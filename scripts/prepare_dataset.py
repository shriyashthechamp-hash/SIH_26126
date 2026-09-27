#!/usr/bin/env python3
"""
SIH 26126 — Dataset Preparation Pipeline

Converts raw RELLIS-3D data into training-ready format:
  1. Remaps raw label IDs → 6-class navigation masks (via class_mapping.yaml)
  2. Resizes RGB + mask pairs to a configurable training resolution
  3. Applies a deterministic 60/20/20 TEMPORAL split independently within
     each RELLIS-3D sequence:
       - First 60% of paired frames (by sorted index) → train
       - Middle 20%                                   → validation
       - Final 20%                                    → test
  4. Computes per-class pixel counts and class weights from the train split
  5. Writes split manifests (JSON) + class weights to data/splits/
  6. Produces a human-readable summary report

IMPORTANT: This is a temporal split within each sequence.  Adjacent frames
are ~0.5s apart.  The train/val boundary within a sequence has ~0.5s
temporal proximity — this is documented and accepted as a trade-off to
ensure all six navigation classes appear in every split.

Usage:
    python scripts/prepare_dataset.py
    python scripts/prepare_dataset.py --resolution 640 512
    python scripts/prepare_dataset.py --dry-run
"""

import argparse
import json
import logging
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
import yaml

# ============================================================================
# Constants
# ============================================================================

RELLIS_SEQUENCES = ["00000", "00001", "00002", "00003", "00004"]

RGB_SUBDIR = "pylon_camera_node"
ID_SUBDIR = "pylon_camera_node_label_id"

# Temporal split ratios (must sum to 1.0)
TRAIN_RATIO = 0.60
VAL_RATIO = 0.20
TEST_RATIO = 0.20

NAV_NAMES = {
    0: "SMOOTH",
    1: "ROUGH",
    2: "BUMPY",
    3: "FORBIDDEN",
    4: "OBSTACLE",
    5: "BACKGROUND",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Helpers
# ============================================================================

def load_class_mapping(config_path: Path) -> dict[int, int]:
    """Load class_mapping.yaml and return {raw_id: nav_id}."""
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    mapping = {}
    for raw_id, entry in cfg["source_classes"].items():
        mapping[int(raw_id)] = int(entry["navigation_id"])
    return mapping


def build_lut(mapping: dict[int, int], max_id: int = 255) -> np.ndarray:
    """Build a numpy lookup table from raw_id → nav_id.

    Unknown IDs default to 5 (BACKGROUND).
    """
    lut = np.full(max_id + 1, 5, dtype=np.uint8)
    for raw_id, nav_id in mapping.items():
        if 0 <= raw_id <= max_id:
            lut[raw_id] = nav_id
    return lut


def find_paired_samples(seq_dir: Path) -> list[tuple[Path, Path, str]]:
    """Find all valid (rgb_path, mask_path, stem) triples in a sequence.

    Returns pairs sorted by stem (which encodes frame index), ensuring
    deterministic temporal ordering.
    """
    rgb_dir = seq_dir / RGB_SUBDIR
    id_dir = seq_dir / ID_SUBDIR

    if not rgb_dir.exists() or not id_dir.exists():
        return []

    # Build stem → path maps
    rgb_files = {}
    for ext in ("*.jpg", "*.png"):
        for f in rgb_dir.glob(ext):
            rgb_files[f.stem] = f

    id_files = {}
    for f in id_dir.glob("*.png"):
        id_files[f.stem] = f

    # Find intersections, sorted by stem for temporal ordering
    paired_stems = sorted(set(rgb_files.keys()) & set(id_files.keys()))
    return [(rgb_files[s], id_files[s], s) for s in paired_stems]


def process_single_pair(
    rgb_path: Path,
    mask_path: Path,
    lut: np.ndarray,
    target_w: int,
    target_h: int,
    output_rgb_dir: Path,
    output_mask_dir: Path,
    stem: str,
) -> dict[int, int]:
    """Process a single RGB+mask pair. Returns nav_id → pixel_count."""

    # Load and resize RGB
    rgb_img = Image.open(rgb_path).convert("RGB")
    rgb_resized = rgb_img.resize((target_w, target_h), Image.LANCZOS)
    rgb_resized.save(output_rgb_dir / f"{stem}.jpg", quality=95)

    # Load, remap, and resize mask
    raw_mask = np.array(Image.open(mask_path))
    if raw_mask.ndim == 3:
        raw_mask = raw_mask[:, :, 0]

    # Remap through LUT
    nav_mask = lut[raw_mask]

    # Resize with NEAREST to preserve label IDs
    nav_pil = Image.fromarray(nav_mask, mode="L")
    nav_resized = nav_pil.resize((target_w, target_h), Image.NEAREST)
    nav_resized.save(output_mask_dir / f"{stem}.png")

    # Count pixels (from resized mask, which is what the model sees)
    nav_arr = np.array(nav_resized)
    pixel_counts = {}
    for nav_id in range(6):
        count = int(np.sum(nav_arr == nav_id))
        if count > 0:
            pixel_counts[nav_id] = count

    return pixel_counts


# ============================================================================
# Split Logic — 60/20/20 Temporal Within Each Sequence
# ============================================================================

def temporal_split_sequence(
    pairs: list[tuple[Path, Path, str]],
    train_ratio: float = TRAIN_RATIO,
    val_ratio: float = VAL_RATIO,
) -> tuple[
    list[tuple[Path, Path, str]],
    list[tuple[Path, Path, str]],
    list[tuple[Path, Path, str]],
]:
    """Split a sorted list of pairs into train/val/test by temporal position.

    Pairs MUST be sorted by frame index (temporal order) before calling.
    First train_ratio → train, next val_ratio → val, remainder → test.
    """
    n = len(pairs)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    return pairs[:train_end], pairs[train_end:val_end], pairs[val_end:]


def build_splits(
    data_root: Path,
) -> tuple[
    dict[str, list[tuple[Path, Path, str, str]]],
    dict[str, dict[str, int]],
]:
    """Build train/val/test splits using 60/20/20 temporal split per sequence.

    Returns:
        splits: {split_name: [(rgb_path, mask_path, stem, seq_name), ...]}
        per_seq_counts: {seq_name: {"train": N, "val": N, "test": N}}
    """

    splits: dict[str, list[tuple[Path, Path, str, str]]] = {
        "train": [],
        "val": [],
        "test": [],
    }
    per_seq_counts: dict[str, dict[str, int]] = {}

    for seq_name in RELLIS_SEQUENCES:
        seq_dir = data_root / seq_name
        pairs = find_paired_samples(seq_dir)

        if not pairs:
            logger.warning(f"  {seq_name}: no paired samples found, skipping.")
            continue

        # Temporal split (pairs are already sorted by stem/frame index)
        train_pairs, val_pairs, test_pairs = temporal_split_sequence(pairs)

        # Validate: every pair must have both files existing
        for split_name_local, split_pairs in [
            ("train", train_pairs),
            ("val", val_pairs),
            ("test", test_pairs),
        ]:
            for rgb_path, mask_path, stem in split_pairs:
                assert rgb_path.exists(), f"RGB missing: {rgb_path}"
                assert mask_path.exists(), f"Mask missing: {mask_path}"

        # Append to global splits
        for rgb, mask, stem in train_pairs:
            splits["train"].append((rgb, mask, stem, seq_name))
        for rgb, mask, stem in val_pairs:
            splits["val"].append((rgb, mask, stem, seq_name))
        for rgb, mask, stem in test_pairs:
            splits["test"].append((rgb, mask, stem, seq_name))

        per_seq_counts[seq_name] = {
            "total_pairs": len(pairs),
            "train": len(train_pairs),
            "val": len(val_pairs),
            "test": len(test_pairs),
        }

        logger.info(
            f"  {seq_name}: {len(pairs)} pairs → "
            f"train={len(train_pairs)}, val={len(val_pairs)}, test={len(test_pairs)}"
        )

    return splits, per_seq_counts


# ============================================================================
# Class Weights
# ============================================================================

def compute_class_weights(
    pixel_counts: dict[int, int],
    max_weight: float = 50.0,
) -> dict[str, Any]:
    """Compute inverse-frequency class weights with capping.

    Returns a dict with raw counts, frequencies, raw weights, and capped weights.
    """
    total_px = sum(pixel_counts.values())
    n_classes = 6

    result: dict[str, Any] = {
        "total_pixels": total_px,
        "per_class": {},
    }

    # Compute inverse frequency: weight_c = total / (n_classes * count_c)
    raw_weights = {}
    for nid in range(n_classes):
        count = pixel_counts.get(nid, 0)
        if count > 0:
            raw_w = total_px / (n_classes * count)
        else:
            raw_w = max_weight  # If no pixels at all, assign max weight
        raw_weights[nid] = raw_w

    # Normalize so the minimum weight = 1.0
    min_w = min(raw_weights.values())
    if min_w > 0:
        norm_weights = {k: v / min_w for k, v in raw_weights.items()}
    else:
        norm_weights = raw_weights

    # Cap at max_weight
    capped_weights = {k: min(v, max_weight) for k, v in norm_weights.items()}

    for nid in range(n_classes):
        count = pixel_counts.get(nid, 0)
        freq = count / total_px if total_px > 0 else 0.0
        result["per_class"][nid] = {
            "name": NAV_NAMES[nid],
            "pixel_count": count,
            "frequency": round(freq, 6),
            "raw_weight": round(raw_weights[nid], 4),
            "normalized_weight": round(norm_weights[nid], 4),
            "capped_weight": round(capped_weights[nid], 4),
        }

    # Final weight vector for training (as a flat list, index = nav_id)
    result["weight_vector"] = [
        round(capped_weights[nid], 4) for nid in range(n_classes)
    ]
    result["max_weight_cap"] = max_weight

    return result


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="SIH 26126 — Dataset Preparation Pipeline"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/class_mapping.yaml",
        help="Path to class mapping config",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        nargs=2,
        default=[512, 512],
        metavar=("WIDTH", "HEIGHT"),
        help="Target resolution W H (default: 512 512)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/rellis3d",
        help="Output directory for processed data",
    )
    parser.add_argument(
        "--splits-dir",
        type=str,
        default="data/splits",
        help="Output directory for split manifests",
    )
    parser.add_argument(
        "--data-root",
        type=str,
        default="data/rellis3d",
        help="Root directory of raw RELLIS-3D data",
    )
    parser.add_argument(
        "--max-weight",
        type=float,
        default=50.0,
        help="Maximum class weight cap (default: 50.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only compute splits and weights, don't write images",
    )
    args = parser.parse_args()

    target_w, target_h = args.resolution
    data_root = Path(args.data_root)
    output_root = Path(args.output)
    splits_dir = Path(args.splits_dir)

    if not data_root.exists():
        logger.error(f"Data root not found: {data_root}")
        return 1

    # --- Load mapping ---
    config_path = Path(args.config)
    logger.info(f"Loading class mapping from {config_path}")
    mapping = load_class_mapping(config_path)
    lut = build_lut(mapping)
    logger.info(f"Mapping loaded: {len(mapping)} raw IDs → 6 nav classes")
    logger.info(f"Target resolution: {target_w}×{target_h}")
    logger.info(
        f"Split strategy: {TRAIN_RATIO:.0%}/{VAL_RATIO:.0%}/{TEST_RATIO:.0%} "
        f"temporal within each sequence"
    )

    # --- Build splits ---
    logger.info("Building train/val/test splits...")
    splits, per_seq_counts = build_splits(data_root)

    for split_name, items in splits.items():
        logger.info(f"  {split_name}: {len(items)} pairs")

    total_pairs = sum(len(v) for v in splits.values())
    logger.info(f"  Total: {total_pairs} pairs")

    # --- Process images ---
    split_pixel_counts: dict[str, Counter] = {
        "train": Counter(),
        "val": Counter(),
        "test": Counter(),
    }
    split_manifests: dict[str, list[dict]] = {
        "train": [],
        "val": [],
        "test": [],
    }

    start_time = time.time()

    for split_name, items in splits.items():
        split_rgb_dir = output_root / split_name / "images"
        split_mask_dir = output_root / split_name / "masks"

        if not args.dry_run:
            split_rgb_dir.mkdir(parents=True, exist_ok=True)
            split_mask_dir.mkdir(parents=True, exist_ok=True)

        for idx, (rgb_path, mask_path, stem, seq) in enumerate(items):
            # Use seq_stem to avoid name collisions across sequences
            unique_stem = f"{seq}_{stem}"

            if not args.dry_run:
                px_counts = process_single_pair(
                    rgb_path, mask_path, lut,
                    target_w, target_h,
                    split_rgb_dir, split_mask_dir,
                    unique_stem,
                )
                for nav_id, count in px_counts.items():
                    split_pixel_counts[split_name][nav_id] += count
            else:
                # Dry run: count pixels from raw mask (no resize/write)
                raw_mask = np.array(Image.open(mask_path))
                if raw_mask.ndim == 3:
                    raw_mask = raw_mask[:, :, 0]
                nav_mask = lut[raw_mask]
                for nav_id in range(6):
                    count = int(np.sum(nav_mask == nav_id))
                    if count > 0:
                        split_pixel_counts[split_name][nav_id] += count

            split_manifests[split_name].append({
                "stem": unique_stem,
                "sequence": seq,
                "original_stem": stem,
                "rgb": str(split_rgb_dir / f"{unique_stem}.jpg"),
                "mask": str(split_mask_dir / f"{unique_stem}.png"),
            })

            # Progress logging
            if (idx + 1) % 200 == 0 or (idx + 1) == len(items):
                elapsed = time.time() - start_time
                logger.info(
                    f"  [{split_name}] {idx + 1}/{len(items)} "
                    f"({elapsed:.0f}s elapsed)"
                )

    elapsed_total = time.time() - start_time
    mode_str = "DRY RUN" if args.dry_run else "PROCESSED"
    logger.info(f"{mode_str} {total_pairs} pairs in {elapsed_total:.1f}s")

    # --- Compute class weights from TRAIN split only ---
    logger.info("Computing class weights from train split...")
    train_weights = compute_class_weights(
        dict(split_pixel_counts["train"]),
        max_weight=args.max_weight,
    )

    # --- Validate FORBIDDEN and SMOOTH have meaningful training signal ---
    smooth_px = split_pixel_counts["train"].get(0, 0)
    forbidden_px = split_pixel_counts["train"].get(3, 0)
    train_total = sum(split_pixel_counts["train"].values())

    logger.info("Validating critical class training signal...")
    if smooth_px == 0:
        logger.error("SMOOTH has ZERO pixels in train — model cannot learn this class!")
        return 1
    if forbidden_px == 0:
        logger.error("FORBIDDEN has ZERO pixels in train — model cannot learn this class!")
        return 1

    smooth_pct = smooth_px / train_total * 100
    forbidden_pct = forbidden_px / train_total * 100
    logger.info(f"  SMOOTH:    {smooth_px:>12,} px ({smooth_pct:.4f}%)")
    logger.info(f"  FORBIDDEN: {forbidden_px:>12,} px ({forbidden_pct:.4f}%)")

    if smooth_pct < 0.01:
        logger.warning(f"SMOOTH is very sparse in train ({smooth_pct:.4f}%)")
    if forbidden_pct < 0.001:
        logger.warning(f"FORBIDDEN is very sparse in train ({forbidden_pct:.4f}%)")

    # --- Write outputs ---
    splits_dir.mkdir(parents=True, exist_ok=True)

    # Split manifests
    for split_name, manifest in split_manifests.items():
        manifest_path = splits_dir / f"{split_name}.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Manifest: {manifest_path} ({len(manifest)} entries)")

    # Class weights
    weights_path = splits_dir / "class_weights.json"
    with open(weights_path, "w") as f:
        json.dump(train_weights, f, indent=2)
    logger.info(f"Class weights: {weights_path}")

    # Per-sequence split counts
    seq_counts_path = splits_dir / "per_sequence_counts.json"
    with open(seq_counts_path, "w") as f:
        json.dump(per_seq_counts, f, indent=2)

    # --- Summary report ---
    report_lines = []
    report_lines.append("=" * 76)
    report_lines.append("SIH 26126 — Dataset Preparation Report")
    report_lines.append("=" * 76)
    report_lines.append("")
    report_lines.append(f"Resolution:      {target_w}×{target_h}")
    report_lines.append(f"Mode:            {'DRY RUN' if args.dry_run else 'FULL PROCESSING'}")
    report_lines.append(f"Time:            {elapsed_total:.1f}s")
    report_lines.append(
        f"Split strategy:  {TRAIN_RATIO:.0%}/{VAL_RATIO:.0%}/{TEST_RATIO:.0%} "
        f"temporal within each sequence"
    )
    report_lines.append(
        "  NOTE: This is a temporal split. Train/val boundaries within a "
        "sequence\n        have ~0.5s temporal proximity. This is accepted as "
        "a trade-off to\n        ensure all six navigation classes appear in "
        "every split."
    )
    report_lines.append("")

    # --- Per-sequence pair counts ---
    report_lines.append("--- Per-Sequence Pair Counts ---")
    report_lines.append(
        f"  {'Sequence':>8}  {'Total':>6}  {'Train':>6}  {'Val':>6}  {'Test':>6}"
    )
    report_lines.append("  " + "-" * 42)
    totals = {"total_pairs": 0, "train": 0, "val": 0, "test": 0}
    for seq_name in RELLIS_SEQUENCES:
        if seq_name in per_seq_counts:
            c = per_seq_counts[seq_name]
            report_lines.append(
                f"  {seq_name:>8}  {c['total_pairs']:>6}  "
                f"{c['train']:>6}  {c['val']:>6}  {c['test']:>6}"
            )
            for k in totals:
                totals[k] += c[k]
    report_lines.append("  " + "-" * 42)
    report_lines.append(
        f"  {'TOTAL':>8}  {totals['total_pairs']:>6}  "
        f"{totals['train']:>6}  {totals['val']:>6}  {totals['test']:>6}"
    )
    report_lines.append("")

    # --- Per-split class distribution ---
    report_lines.append("--- Per-Split Class Distribution ---")
    for split_name in ["train", "val", "test"]:
        counts = split_pixel_counts[split_name]
        total_px = sum(counts.values())
        report_lines.append(f"\n  [{split_name.upper()}] ({len(split_manifests[split_name])} pairs, {total_px:,} total pixels)")
        for nid in range(6):
            px = counts.get(nid, 0)
            pct = px / total_px * 100 if total_px > 0 else 0
            flag = ""
            if px == 0:
                flag = " ⚠ ZERO"
            elif pct < 0.01:
                flag = " ⚠ TRACE"
            report_lines.append(
                f"    {nid} {NAV_NAMES[nid]:<12}: {px:>15,} px  ({pct:6.3f}%){flag}"
            )
    report_lines.append("")

    # --- Class weights ---
    report_lines.append("--- Class Weights (from train split) ---")
    report_lines.append(f"  Max weight cap: {args.max_weight}")
    report_lines.append(f"  Weight vector:  {train_weights['weight_vector']}")
    report_lines.append("")
    report_lines.append(
        f"  {'Nav ID':>6}  {'Class':<12}  {'Train Pixels':>15}  "
        f"{'Freq':>8}  {'Norm Wt':>8}  {'Capped':>8}"
    )
    report_lines.append("  " + "-" * 68)
    for nid in range(6):
        info = train_weights["per_class"][nid]
        report_lines.append(
            f"  {nid:>6}  {info['name']:<12}  {info['pixel_count']:>15,}  "
            f"{info['frequency']:>8.4f}  "
            f"{info['normalized_weight']:>8.2f}  {info['capped_weight']:>8.2f}"
        )
    report_lines.append("")

    # --- Critical class validation ---
    report_lines.append("--- Critical Class Validation ---")
    report_lines.append(f"  SMOOTH    in train: {smooth_px:>12,} px ({smooth_pct:.4f}%)")
    report_lines.append(f"  FORBIDDEN in train: {forbidden_px:>12,} px ({forbidden_pct:.4f}%)")
    if smooth_px > 0 and forbidden_px > 0:
        report_lines.append("  ✅ Both critical classes have training signal.")
    else:
        report_lines.append("  ❌ CRITICAL: One or both classes missing from train!")
    report_lines.append("")

    # --- Output paths ---
    report_lines.append("--- Output Paths ---")
    report_lines.append(f"  Processed images:    {output_root}/")
    report_lines.append(f"  Split manifests:     {splits_dir}/")
    report_lines.append(f"  Class weights:       {weights_path}")
    report_lines.append(f"  Per-seq counts:      {seq_counts_path}")
    report_lines.append("")
    report_lines.append("=" * 76)
    report_lines.append("END OF REPORT")
    report_lines.append("=" * 76)

    report_text = "\n".join(report_lines)
    report_path = splits_dir / "preparation_report.txt"
    report_path.write_text(report_text)
    logger.info(f"Report: {report_path}")

    # Print report to stdout
    print("\n" + report_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
