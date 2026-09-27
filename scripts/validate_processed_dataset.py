#!/usr/bin/env python3
"""
SIH 26126 — Post-Processing Validation

Validates the processed dataset after prepare_dataset.py has run:
  1. Checks train/val/test pair counts match manifests
  2. Verifies image/mask dimensions are exactly 512×512
  3. Verifies mask unique IDs are in {0,1,2,3,4,5}
  4. Detects missing or corrupt files
  5. Computes per-split class pixel distribution
  6. Reports any errors

Usage:
    python scripts/validate_processed_dataset.py
"""

import json
import logging
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SPLITS_DIR = Path("data/splits")
PROCESSED_ROOT = Path("data/processed/rellis3d")
EXPECTED_SIZE = (512, 512)  # (W, H)
VALID_NAV_IDS = {0, 1, 2, 3, 4, 5}

NAV_NAMES = {
    0: "SMOOTH",
    1: "ROUGH",
    2: "BUMPY",
    3: "FORBIDDEN",
    4: "OBSTACLE",
    5: "BACKGROUND",
}


def validate_split(split_name: str, manifest: list[dict]) -> dict:
    """Validate all pairs in a split. Returns a results dict."""

    result = {
        "split": split_name,
        "manifest_count": len(manifest),
        "rgb_found": 0,
        "mask_found": 0,
        "pairs_valid": 0,
        "rgb_missing": [],
        "mask_missing": [],
        "rgb_corrupt": [],
        "mask_corrupt": [],
        "rgb_wrong_size": [],
        "mask_wrong_size": [],
        "mask_invalid_ids": [],
        "pixel_counts": Counter(),
        "checked_dims": set(),
    }

    for idx, entry in enumerate(manifest):
        stem = entry["stem"]
        rgb_path = Path(entry["rgb"])
        mask_path = Path(entry["mask"])

        # --- Check existence ---
        rgb_exists = rgb_path.exists()
        mask_exists = mask_path.exists()

        if not rgb_exists:
            result["rgb_missing"].append(str(rgb_path))
        else:
            result["rgb_found"] += 1

        if not mask_exists:
            result["mask_missing"].append(str(mask_path))
        else:
            result["mask_found"] += 1

        if not rgb_exists or not mask_exists:
            continue

        # --- Check RGB readability and dimensions ---
        try:
            rgb_img = Image.open(rgb_path)
            rgb_size = rgb_img.size  # (W, H)
            if rgb_size != EXPECTED_SIZE:
                result["rgb_wrong_size"].append(
                    f"{rgb_path}: {rgb_size[0]}×{rgb_size[1]}"
                )
            result["checked_dims"].add(f"RGB:{rgb_size[0]}×{rgb_size[1]}")
        except Exception as e:
            result["rgb_corrupt"].append(f"{rgb_path}: {e}")
            continue

        # --- Check mask readability, dimensions, and IDs ---
        try:
            mask_img = Image.open(mask_path)
            mask_size = mask_img.size
            if mask_size != EXPECTED_SIZE:
                result["mask_wrong_size"].append(
                    f"{mask_path}: {mask_size[0]}×{mask_size[1]}"
                )
            result["checked_dims"].add(f"Mask:{mask_size[0]}×{mask_size[1]}")

            mask_arr = np.array(mask_img)
            unique_ids = set(np.unique(mask_arr).tolist())

            # Check for invalid IDs
            invalid = unique_ids - VALID_NAV_IDS
            if invalid:
                result["mask_invalid_ids"].append(
                    f"{mask_path}: invalid IDs {sorted(invalid)}"
                )

            # Count pixels
            for nav_id in range(6):
                count = int(np.sum(mask_arr == nav_id))
                if count > 0:
                    result["pixel_counts"][nav_id] += count

        except Exception as e:
            result["mask_corrupt"].append(f"{mask_path}: {e}")
            continue

        result["pairs_valid"] += 1

        # Progress
        if (idx + 1) % 500 == 0:
            logger.info(f"  [{split_name}] validated {idx + 1}/{len(manifest)}")

    return result


def main() -> int:
    errors_found = False

    # --- Load manifests ---
    all_results = {}
    for split_name in ["train", "val", "test"]:
        manifest_path = SPLITS_DIR / f"{split_name}.json"
        if not manifest_path.exists():
            logger.error(f"Manifest not found: {manifest_path}")
            return 1

        with open(manifest_path) as f:
            manifest = json.load(f)

        logger.info(f"Validating {split_name}: {len(manifest)} entries...")
        result = validate_split(split_name, manifest)
        all_results[split_name] = result

    # --- Print report ---
    print("\n" + "=" * 76)
    print("SIH 26126 — Post-Processing Validation Report")
    print("=" * 76)

    total_pairs = 0
    total_valid = 0

    for split_name in ["train", "val", "test"]:
        r = all_results[split_name]
        total_pairs += r["manifest_count"]
        total_valid += r["pairs_valid"]

        print(f"\n--- [{split_name.upper()}] ---")
        print(f"  Manifest entries:    {r['manifest_count']}")
        print(f"  RGB files found:     {r['rgb_found']}")
        print(f"  Mask files found:    {r['mask_found']}")
        print(f"  Valid pairs:         {r['pairs_valid']}")
        print(f"  Dimensions observed: {sorted(r['checked_dims'])}")

        # Errors
        issues = []
        if r["rgb_missing"]:
            issues.append(f"  ⚠ RGB missing:       {len(r['rgb_missing'])}")
            errors_found = True
        if r["mask_missing"]:
            issues.append(f"  ⚠ Mask missing:      {len(r['mask_missing'])}")
            errors_found = True
        if r["rgb_corrupt"]:
            issues.append(f"  ⚠ RGB corrupt:       {len(r['rgb_corrupt'])}")
            errors_found = True
        if r["mask_corrupt"]:
            issues.append(f"  ⚠ Mask corrupt:      {len(r['mask_corrupt'])}")
            errors_found = True
        if r["rgb_wrong_size"]:
            issues.append(f"  ⚠ RGB wrong size:    {len(r['rgb_wrong_size'])}")
            errors_found = True
        if r["mask_wrong_size"]:
            issues.append(f"  ⚠ Mask wrong size:   {len(r['mask_wrong_size'])}")
            errors_found = True
        if r["mask_invalid_ids"]:
            issues.append(f"  ⚠ Invalid mask IDs:  {len(r['mask_invalid_ids'])}")
            errors_found = True

        if issues:
            for issue in issues:
                print(issue)
            # Print first few details
            for key in ["rgb_missing", "mask_missing", "rgb_corrupt",
                        "mask_corrupt", "rgb_wrong_size", "mask_wrong_size",
                        "mask_invalid_ids"]:
                items = r[key]
                if items:
                    for item in items[:3]:
                        print(f"      → {item}")
                    if len(items) > 3:
                        print(f"      ... and {len(items) - 3} more")
        else:
            print("  ✅ No errors found.")

        # Pixel distribution
        counts = r["pixel_counts"]
        total_px = sum(counts.values())
        if total_px > 0:
            print(f"\n  Class distribution ({total_px:,} total pixels):")
            for nid in range(6):
                px = counts.get(nid, 0)
                pct = px / total_px * 100
                flag = ""
                if px == 0:
                    flag = " ⚠ ZERO"
                elif pct < 0.01:
                    flag = " ⚠ TRACE"
                print(
                    f"    {nid} {NAV_NAMES[nid]:<12}: "
                    f"{px:>15,} px  ({pct:6.3f}%){flag}"
                )

    # --- Totals ---
    print(f"\n--- TOTALS ---")
    print(f"  Total manifest entries: {total_pairs}")
    print(f"  Total valid pairs:      {total_valid}")
    match = total_pairs == total_valid
    if match:
        print("  ✅ All manifest entries validated successfully.")
    else:
        print(f"  ❌ {total_pairs - total_valid} entries failed validation.")
        errors_found = True

    # --- Unique mask IDs across entire dataset ---
    all_ids = set()
    for r in all_results.values():
        all_ids.update(r["pixel_counts"].keys())
    print(f"\n  Unique mask IDs across dataset: {sorted(all_ids)}")
    if all_ids <= VALID_NAV_IDS:
        print("  ✅ All mask IDs are valid (0–5).")
    else:
        print(f"  ❌ Invalid IDs found: {sorted(all_ids - VALID_NAV_IDS)}")
        errors_found = True

    print("\n" + "=" * 76)
    if errors_found:
        print("VALIDATION FAILED — see errors above")
    else:
        print("ALL CHECKS PASSED")
    print("=" * 76)

    return 1 if errors_found else 0


if __name__ == "__main__":
    sys.exit(main())
