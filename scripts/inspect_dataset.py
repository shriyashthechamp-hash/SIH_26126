#!/usr/bin/env python3
"""
SIH 26126 — Dataset Inspection Script

Inspects RELLIS-3D data: file counts, pairing, dimensions, label
distribution, and generates sample visualizations.

Usage:
    python scripts/inspect_dataset.py --dataset rellis3d
    python scripts/inspect_dataset.py --dataset rellis3d --samples 10
    python scripts/inspect_dataset.py --dataset rellis3d --output outputs/dataset_inspection
"""

import argparse
import json
import logging
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from PIL import Image
import yaml

# ============================================================================
# Constants
# ============================================================================

RELLIS_SEQUENCES = ["00000", "00001", "00002", "00003", "00004"]

RGB_SUBDIR = "pylon_camera_node"
ID_SUBDIR = "pylon_camera_node_label_id"
COLOR_SUBDIR = "pylon_camera_node_label_color"

# Navigation class colors for visualization (RGB)
NAV_COLORS = {
    0: (46, 204, 113),    # SMOOTH  — green
    1: (241, 196, 15),    # ROUGH   — yellow
    2: (230, 126, 34),    # BUMPY   — orange
    3: (52, 152, 219),    # FORBIDDEN — blue
    4: (231, 76, 60),     # OBSTACLE — red
    5: (149, 165, 166),   # BACKGROUND — grey
}

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
    lut = np.full(max_id + 1, 5, dtype=np.uint8)  # default = BACKGROUND
    for raw_id, nav_id in mapping.items():
        if 0 <= raw_id <= max_id:
            lut[raw_id] = nav_id
    return lut


def check_image_readable(path: Path) -> tuple[bool, str]:
    """Try opening an image. Returns (ok, error_msg)."""
    try:
        img = Image.open(path)
        img.verify()
        return True, ""
    except Exception as e:
        return False, str(e)


def get_image_size(path: Path) -> tuple[int, int]:
    """Return (width, height) of an image."""
    with Image.open(path) as img:
        return img.size


def colorize_nav_mask(nav_mask: np.ndarray) -> np.ndarray:
    """Convert a single-channel nav mask to an RGB image."""
    h, w = nav_mask.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    for nav_id, color in NAV_COLORS.items():
        rgb[nav_mask == nav_id] = color
    return rgb


# ============================================================================
# Sequence Inspection
# ============================================================================

def inspect_sequence(
    seq_dir: Path,
    seq_name: str,
    mapping: dict[int, int],
    lut: np.ndarray,
    check_corrupt: bool = True,
    max_corrupt_check: int = 50,
) -> dict[str, Any]:
    """Inspect a single RELLIS sequence directory."""

    rgb_dir = seq_dir / RGB_SUBDIR
    id_dir = seq_dir / ID_SUBDIR
    color_dir = seq_dir / COLOR_SUBDIR

    result: dict[str, Any] = {"sequence": seq_name, "errors": []}

    # --- File counts ---
    rgb_files = sorted(rgb_dir.glob("*.jpg")) + sorted(rgb_dir.glob("*.png"))
    id_files = sorted(id_dir.glob("*.png")) if id_dir.exists() else []
    color_files = sorted(color_dir.glob("*.png")) if color_dir.exists() else []

    rgb_stems = {f.stem for f in rgb_files}
    id_stems = {f.stem for f in id_files}
    color_stems = {f.stem for f in color_files}

    result["rgb_count"] = len(rgb_files)
    result["id_count"] = len(id_files)
    result["color_count"] = len(color_files)

    # --- Pairing ---
    paired = rgb_stems & id_stems
    rgb_only = rgb_stems - id_stems
    id_only = id_stems - rgb_stems

    result["paired_count"] = len(paired)
    result["rgb_without_id"] = len(rgb_only)
    result["id_without_rgb"] = len(id_only)

    if id_only:
        result["errors"].append(f"{len(id_only)} ID masks have no corresponding RGB")

    # --- Dimensions (sample) ---
    if rgb_files:
        sample_rgb = rgb_files[0]
        result["rgb_dimensions"] = get_image_size(sample_rgb)

    if id_files:
        sample_id = id_files[0]
        result["id_dimensions"] = get_image_size(sample_id)

    # --- Corruption check (sample) ---
    if check_corrupt:
        corrupt_rgb = []
        corrupt_id = []

        for f in rgb_files[:max_corrupt_check]:
            ok, err = check_image_readable(f)
            if not ok:
                corrupt_rgb.append((str(f), err))

        for f in id_files[:max_corrupt_check]:
            ok, err = check_image_readable(f)
            if not ok:
                corrupt_id.append((str(f), err))

        result["corrupt_rgb_checked"] = min(len(rgb_files), max_corrupt_check)
        result["corrupt_rgb_found"] = corrupt_rgb
        result["corrupt_id_checked"] = min(len(id_files), max_corrupt_check)
        result["corrupt_id_found"] = corrupt_id

    # --- Label distribution ---
    label_counter: Counter = Counter()
    for id_path in id_files:
        mask = np.array(Image.open(id_path))
        # Handle multi-channel masks (take first channel)
        if mask.ndim == 3:
            mask = mask[:, :, 0]
        for val in np.unique(mask):
            label_counter[int(val)] += int(np.sum(mask == val))

    result["raw_label_ids"] = sorted(label_counter.keys())
    result["raw_pixel_counts"] = dict(sorted(label_counter.items()))

    # --- Navigation class distribution ---
    nav_counter: Counter = Counter()
    for raw_id, px_count in label_counter.items():
        nav_id = mapping.get(raw_id, 5)
        nav_counter[nav_id] += px_count

    result["nav_pixel_counts"] = {
        nav_id: {"name": NAV_NAMES[nav_id], "pixels": nav_counter.get(nav_id, 0)}
        for nav_id in sorted(NAV_NAMES.keys())
    }

    # --- Valid paired file list ---
    result["paired_stems"] = sorted(paired)

    return result


# ============================================================================
# Visualization
# ============================================================================

def save_sample_visualizations(
    seq_dir: Path,
    seq_name: str,
    paired_stems: list[str],
    lut: np.ndarray,
    output_dir: Path,
    num_samples: int = 5,
    seed: int = 42,
) -> list[str]:
    """Save side-by-side visualizations for random paired samples."""

    if not paired_stems:
        logger.warning(f"Sequence {seq_name}: no paired samples for visualization.")
        return []

    rng = random.Random(seed)
    samples = rng.sample(paired_stems, min(num_samples, len(paired_stems)))
    saved_paths = []

    vis_dir = output_dir / "visualizations" / seq_name
    vis_dir.mkdir(parents=True, exist_ok=True)

    for stem in samples:
        # Find RGB (could be .jpg or .png)
        rgb_dir = seq_dir / RGB_SUBDIR
        rgb_path = rgb_dir / f"{stem}.jpg"
        if not rgb_path.exists():
            rgb_path = rgb_dir / f"{stem}.png"
        if not rgb_path.exists():
            logger.warning(f"Cannot find RGB for {stem}")
            continue

        id_path = seq_dir / ID_SUBDIR / f"{stem}.png"

        rgb_img = np.array(Image.open(rgb_path).convert("RGB"))
        raw_mask = np.array(Image.open(id_path))
        if raw_mask.ndim == 3:
            raw_mask = raw_mask[:, :, 0]

        # Convert to navigation mask
        nav_mask = lut[raw_mask]
        nav_rgb = colorize_nav_mask(nav_mask)

        # Build figure
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        axes[0].imshow(rgb_img)
        axes[0].set_title(f"RGB — {stem}", fontsize=10)
        axes[0].axis("off")

        axes[1].imshow(raw_mask, cmap="tab20", vmin=0, vmax=34)
        axes[1].set_title("Raw RELLIS Mask", fontsize=10)
        axes[1].axis("off")

        axes[2].imshow(nav_rgb)
        axes[2].set_title("Navigation Classes", fontsize=10)
        axes[2].axis("off")

        # Legend for navigation classes
        patches = [
            mpatches.Patch(
                color=np.array(NAV_COLORS[nid]) / 255.0,
                label=f"{nid} {NAV_NAMES[nid]}"
            )
            for nid in sorted(NAV_NAMES.keys())
        ]
        fig.legend(
            handles=patches,
            loc="lower center",
            ncol=6,
            fontsize=8,
            frameon=False,
            bbox_to_anchor=(0.5, -0.02),
        )

        fig.suptitle(f"Sequence {seq_name}", fontsize=12, fontweight="bold")
        plt.tight_layout()

        save_path = vis_dir / f"{stem}.png"
        fig.savefig(save_path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        saved_paths.append(str(save_path))

    return saved_paths


# ============================================================================
# Report
# ============================================================================

def generate_report(
    results: list[dict[str, Any]],
    output_dir: Path,
    vis_paths: dict[str, list[str]],
) -> Path:
    """Generate a human-readable text report."""

    report_path = output_dir / "inspection_report.txt"

    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("SIH 26126 — RELLIS-3D Dataset Inspection Report")
    lines.append("=" * 72)
    lines.append("")

    total_rgb = 0
    total_id = 0
    total_color = 0
    total_paired = 0
    all_raw_ids: set[int] = set()

    for r in results:
        seq = r["sequence"]
        lines.append(f"--- Sequence {seq} ---")
        lines.append(f"  RGB images:       {r['rgb_count']}")
        lines.append(f"  ID masks:         {r['id_count']}")
        lines.append(f"  Color masks:      {r['color_count']}")
        lines.append(f"  Valid pairs:      {r['paired_count']}")
        lines.append(f"  RGB without ID:   {r['rgb_without_id']}")
        lines.append(f"  ID without RGB:   {r['id_without_rgb']}")

        if "rgb_dimensions" in r:
            lines.append(f"  RGB size (W×H):   {r['rgb_dimensions'][0]}×{r['rgb_dimensions'][1]}")
        if "id_dimensions" in r:
            lines.append(f"  Mask size (W×H):  {r['id_dimensions'][0]}×{r['id_dimensions'][1]}")

        lines.append(f"  Raw label IDs:    {r['raw_label_ids']}")

        if r.get("corrupt_rgb_found"):
            lines.append(f"  ⚠ Corrupt RGB:    {len(r['corrupt_rgb_found'])} files")
        if r.get("corrupt_id_found"):
            lines.append(f"  ⚠ Corrupt masks:  {len(r['corrupt_id_found'])} files")

        if r.get("errors"):
            for err in r["errors"]:
                lines.append(f"  ⚠ {err}")

        lines.append("")

        total_rgb += r["rgb_count"]
        total_id += r["id_count"]
        total_color += r["color_count"]
        total_paired += r["paired_count"]
        all_raw_ids.update(r["raw_label_ids"])

    # --- Totals ---
    lines.append("--- TOTALS ---")
    lines.append(f"  Total RGB:        {total_rgb}")
    lines.append(f"  Total ID masks:   {total_id}")
    lines.append(f"  Total color:      {total_color}")
    lines.append(f"  Total pairs:      {total_paired}")
    lines.append(f"  All raw IDs:      {sorted(all_raw_ids)}")
    lines.append("")

    # --- Navigation class distribution (aggregated) ---
    agg_nav: Counter = Counter()
    agg_raw: Counter = Counter()
    for r in results:
        for raw_id, px in r["raw_pixel_counts"].items():
            agg_raw[raw_id] += px
        for nav_id_str, info in r["nav_pixel_counts"].items():
            nav_id = int(nav_id_str) if isinstance(nav_id_str, str) else nav_id_str
            agg_nav[nav_id] += info["pixels"]

    total_px = sum(agg_nav.values())

    lines.append("--- Navigation Class Distribution (all sequences) ---")
    for nav_id in sorted(NAV_NAMES.keys()):
        px = agg_nav.get(nav_id, 0)
        pct = (px / total_px * 100) if total_px > 0 else 0.0
        lines.append(f"  {nav_id} {NAV_NAMES[nav_id]:<12}: {px:>15,} px  ({pct:5.1f}%)")
    lines.append(f"  {'TOTAL':<14}: {total_px:>15,} px")
    lines.append("")

    # --- Visualizations ---
    lines.append("--- Saved Visualizations ---")
    for seq, paths in vis_paths.items():
        lines.append(f"  Sequence {seq}: {len(paths)} samples")
        for p in paths:
            lines.append(f"    → {p}")
    lines.append("")

    lines.append("=" * 72)
    lines.append("END OF REPORT")
    lines.append("=" * 72)

    report_text = "\n".join(lines)
    report_path.write_text(report_text)
    return report_path


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="SIH 26126 — Dataset Inspection")
    parser.add_argument(
        "--dataset",
        type=str,
        default="rellis3d",
        choices=["rellis3d"],
        help="Dataset to inspect (default: rellis3d)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="Number of visualization samples per sequence (default: 5)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/dataset_inspection",
        help="Output directory for report and visualizations",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/class_mapping.yaml",
        help="Path to class mapping config",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sample selection (default: 42)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Load mapping ---
    config_path = Path(args.config)
    logger.info(f"Loading class mapping from {config_path}")
    mapping = load_class_mapping(config_path)
    lut = build_lut(mapping)
    logger.info(f"Mapping loaded: {len(mapping)} raw IDs → 6 nav classes")

    # --- Determine dataset root ---
    if args.dataset == "rellis3d":
        data_root = Path("data/rellis3d")
    else:
        logger.error(f"Unknown dataset: {args.dataset}")
        return 1

    if not data_root.exists():
        logger.error(f"Data root not found: {data_root}")
        return 1

    # --- Inspect each sequence ---
    all_results = []
    all_vis_paths: dict[str, list[str]] = {}

    for seq_name in RELLIS_SEQUENCES:
        seq_dir = data_root / seq_name
        if not seq_dir.exists():
            logger.warning(f"Sequence directory not found: {seq_dir}")
            continue

        logger.info(f"Inspecting sequence {seq_name}...")
        result = inspect_sequence(seq_dir, seq_name, mapping, lut)
        all_results.append(result)

        logger.info(
            f"  {seq_name}: {result['rgb_count']} RGB, "
            f"{result['id_count']} ID, "
            f"{result['paired_count']} pairs"
        )

        # --- Visualizations ---
        logger.info(f"  Generating {args.samples} sample visualizations...")
        vis = save_sample_visualizations(
            seq_dir, seq_name, result["paired_stems"],
            lut, output_dir, num_samples=args.samples, seed=args.seed,
        )
        all_vis_paths[seq_name] = vis
        logger.info(f"  Saved {len(vis)} visualizations.")

    # --- Generate report ---
    logger.info("Generating inspection report...")
    report_path = generate_report(all_results, output_dir, all_vis_paths)
    logger.info(f"Report saved to: {report_path}")

    # --- Save raw results as JSON ---
    json_path = output_dir / "inspection_data.json"
    # Convert results to JSON-safe format (remove paired_stems to keep size small)
    json_results = []
    for r in all_results:
        jr = {k: v for k, v in r.items() if k != "paired_stems"}
        jr["paired_stems_count"] = len(r.get("paired_stems", []))
        json_results.append(jr)

    with open(json_path, "w") as f:
        json.dump(json_results, f, indent=2)
    logger.info(f"JSON data saved to: {json_path}")

    # --- Print summary ---
    print("\n" + "=" * 60)
    print("INSPECTION COMPLETE")
    print("=" * 60)
    print(f"Report:          {report_path}")
    print(f"JSON data:       {json_path}")
    print(f"Visualizations:  {output_dir / 'visualizations'}")
    total_vis = sum(len(v) for v in all_vis_paths.values())
    print(f"Total samples:   {total_vis}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
