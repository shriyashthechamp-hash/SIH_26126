#!/usr/bin/env python3
"""
Validate configs/class_mapping.yaml against known RELLIS-3D data.

Checks:
  1. YAML is syntactically valid.
  2. Every observed raw RELLIS ID has exactly one navigation mapping.
  3. All navigation_id values are in {0,1,2,3,4,5}.
  4. Defensive IDs 29, 30, 32 are present.
  5. No observed class is accidentally unmapped.
"""

import sys
from pathlib import Path

import yaml


def main() -> int:
    config_path = Path("configs/class_mapping.yaml")

    # --- 1. Load YAML ---
    print(f"Loading: {config_path}")
    try:
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)
        print("[PASS] YAML is syntactically valid.\n")
    except yaml.YAMLError as e:
        print(f"[FAIL] YAML parse error:\n{e}")
        return 1

    source_classes = cfg.get("source_classes", {})
    nav_classes = cfg.get("navigation_classes", {})

    # --- 2. Check navigation class definitions ---
    expected_nav_ids = {0, 1, 2, 3, 4, 5}
    defined_nav_ids = set(nav_classes.keys())
    print(f"Defined navigation classes: {sorted(defined_nav_ids)}")
    if defined_nav_ids != expected_nav_ids:
        print(f"[FAIL] Expected nav IDs {sorted(expected_nav_ids)}, got {sorted(defined_nav_ids)}")
        return 1
    print("[PASS] Navigation classes 0–5 all defined.\n")

    # --- 3. Check every observed raw ID is mapped ---
    observed_ids = {0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 17, 18, 19, 23, 27, 31, 33, 34}
    mapped_ids = set(source_classes.keys())
    print(f"Mapped raw IDs: {sorted(mapped_ids)}")
    print(f"Observed raw IDs: {sorted(observed_ids)}")

    missing = observed_ids - mapped_ids
    if missing:
        print(f"[FAIL] Observed IDs missing from mapping: {sorted(missing)}")
        return 1
    print("[PASS] Every observed raw ID has a mapping.\n")

    # --- 4. Check defensive IDs 29, 30, 32 ---
    defensive_ids = {29, 30, 32}
    missing_defensive = defensive_ids - mapped_ids
    if missing_defensive:
        print(f"[FAIL] Defensive IDs missing: {sorted(missing_defensive)}")
        return 1
    print(f"[PASS] Defensive IDs {sorted(defensive_ids)} are all present.\n")

    # --- 5. Check all navigation_id values are 0–5 ---
    errors = []
    for raw_id, entry in source_classes.items():
        nav_id = entry.get("navigation_id")
        if nav_id not in expected_nav_ids:
            errors.append(f"  Raw ID {raw_id}: navigation_id={nav_id} (invalid)")
    if errors:
        print("[FAIL] Invalid navigation_id values:")
        for e in errors:
            print(e)
        return 1
    print("[PASS] All navigation_id values are in {0,1,2,3,4,5}.\n")

    # --- 6. Print full mapping table ---
    print("=" * 72)
    print(f"{'Raw ID':>6}  {'RELLIS Class':<20}  {'Nav ID':>6}  {'Nav Class':<12}  {'Observed'}")
    print("-" * 72)
    for raw_id in sorted(source_classes.keys()):
        entry = source_classes[raw_id]
        nav_id = entry["navigation_id"]
        nav_name = nav_classes[nav_id]
        obs = "YES" if entry.get("observed", False) else "no"
        print(f"{raw_id:>6}  {entry['name']:<20}  {nav_id:>6}  {nav_name:<12}  {obs}")
    print("=" * 72)

    # --- 7. Summary by navigation class ---
    print("\nNavigation class summary:")
    for nid in sorted(nav_classes.keys()):
        members = [
            f"{rid}={source_classes[rid]['name']}"
            for rid in sorted(source_classes.keys())
            if source_classes[rid]["navigation_id"] == nid
        ]
        print(f"  {nid} {nav_classes[nid]:<12}: {', '.join(members)}")

    print(f"\nTotal mapped raw IDs: {len(mapped_ids)}")
    print(f"  Observed: {len(mapped_ids & observed_ids)}")
    print(f"  Defensive (not observed): {len(mapped_ids - observed_ids)}")

    print("\n[ALL CHECKS PASSED]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
