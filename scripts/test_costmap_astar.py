#!/usr/bin/env python3
"""
Integration test: TraversabilityCostmap → costmap_adapter → AStarPlanner.

Builds a synthetic segmentation mask using the real TraversabilityCostmap
class and config, converts it via the adapter, and runs A* planning.

Class IDs (from traversability.yaml):
    0: SMOOTH   (cost 0.0)
    1: ROUGH    (cost 0.3)
    2: BUMPY    (cost 0.6)
    3: FORBIDDEN(cost 1.0 → blocked)
    4: OBSTACLE (cost 1.0 → blocked)
    5: BACKGROUND (cost 0.8)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from src.traversability.costmap import TraversabilityCostmap
from src.planning.costmap_adapter import get_planning_arrays
from src.planning.astar import AStarPlanner

SEPARATOR = "=" * 60

# ------------------------------------------------------------------
# 1. Build a synthetic segmentation mask (100 × 120)
# ------------------------------------------------------------------
ROWS, COLS = 100, 120

seg_mask = np.zeros((ROWS, COLS), dtype=np.uint8)

# Default: class 0 (SMOOTH, cost 0.0) — fully traversable.

# A horizontal band of ROUGH terrain (class 1)
seg_mask[20:30, :] = 1

# A patch of BUMPY terrain (class 2)
seg_mask[60:75, 80:110] = 2

# A vertical OBSTACLE wall (class 4) with a gap
seg_mask[:, 55:58] = 4          # wall spans full height
seg_mask[40:55, 55:58] = 0      # gap: revert to SMOOTH

# A FORBIDDEN zone (class 3)
seg_mask[80:95, 10:30] = 3

# Some BACKGROUND cells (class 5)
seg_mask[0:5, 0:10] = 5

# ------------------------------------------------------------------
# 2. Run through real TraversabilityCostmap
# ------------------------------------------------------------------
trav = TraversabilityCostmap(config_path="configs/traversability.yaml")
trav_result = trav.process(seg_mask)

# ------------------------------------------------------------------
# 3. Convert via adapter
# ------------------------------------------------------------------
costmap, blocked_mask = get_planning_arrays(trav_result)

# ------------------------------------------------------------------
# 4. Plan with A*
# ------------------------------------------------------------------
start = (50, 10)
goal  = (50, 100)

planner = AStarPlanner(costmap, blocked_mask=blocked_mask)
path = planner.plan(start, goal)

# ------------------------------------------------------------------
# 5. Print summary
# ------------------------------------------------------------------
print(SEPARATOR)
print("SIH 26126 — COSTMAP ↔ A* INTEGRATION TEST")
print(SEPARATOR)
print(f"  Seg mask shape   : {seg_mask.shape}")
print(f"  Costmap shape    : {costmap.shape}")
print(f"  Costmap dtype    : {costmap.dtype}")
print(f"  Cost range       : [{costmap.min():.2f}, {costmap.max():.2f}]")
print(f"  Blocked cells    : {int(blocked_mask.sum())} / {blocked_mask.size}"
      f"  ({blocked_mask.sum() / blocked_mask.size * 100:.1f}%)")
print(f"  Start            : {start}")
print(f"  Goal             : {goal}")
print(f"  Path found       : {'YES' if path else 'NO'}")
print(f"  Path length      : {len(path)} waypoints")
print(SEPARATOR)

if not path:
    print("No valid route — check costmap or start/goal placement.")
    sys.exit(1)

# ------------------------------------------------------------------
# 6. ASCII mini-map (down-sampled for readability)
# ------------------------------------------------------------------
print("\nASCII preview (S=start, G=goal, ·=path, █=blocked, "
      "░=rough/bumpy, ▒=background):\n")

path_set = set(path)

# Print every other row/col to fit terminals
for r in range(0, ROWS, 2):
    row_chars = []
    for c in range(0, COLS, 2):
        if (r, c) == start:
            row_chars.append("S")
        elif (r, c) == goal:
            row_chars.append("G")
        elif (r, c) in path_set:
            row_chars.append("·")
        elif blocked_mask[r, c]:
            row_chars.append("█")
        elif costmap[r, c] >= 0.5:
            row_chars.append("▒")
        elif costmap[r, c] > 0.0:
            row_chars.append("░")
        else:
            row_chars.append(" ")
    print("".join(row_chars))

print()

# ------------------------------------------------------------------
# 7. Matplotlib visualisation
# ------------------------------------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    # --- Panel 1: Segmentation mask ---
    ax = axes[0]
    seg_display = ax.imshow(seg_mask, cmap="tab10", vmin=0, vmax=9,
                            interpolation="nearest")
    ax.set_title("Segmentation Mask (class IDs)")
    fig.colorbar(seg_display, ax=ax, shrink=0.6)

    # --- Panel 2: Cost heatmap + blocked overlay ---
    ax = axes[1]
    cost_display = costmap.copy()
    cost_display[blocked_mask] = np.nan
    ax.imshow(cost_display, cmap="YlOrRd", vmin=0.0, vmax=1.0,
              interpolation="nearest")
    # Overlay blocked in dark grey
    blocked_overlay = np.zeros((*costmap.shape, 4))
    blocked_overlay[blocked_mask] = [0.2, 0.2, 0.2, 1.0]
    ax.imshow(blocked_overlay, interpolation="nearest")
    ax.set_title("Traversability Cost + Blocked (grey)")

    # --- Panel 3: A* path on costmap ---
    ax = axes[2]
    ax.imshow(costmap, cmap="YlOrRd", vmin=0.0, vmax=1.0,
              interpolation="nearest", alpha=0.6)
    blocked_overlay2 = np.zeros((*costmap.shape, 4))
    blocked_overlay2[blocked_mask] = [0.2, 0.2, 0.2, 0.8]
    ax.imshow(blocked_overlay2, interpolation="nearest")

    if path:
        pr = [p[0] for p in path]
        pc = [p[1] for p in path]
        ax.plot(pc, pr, color="dodgerblue", linewidth=1.5, label="A* path")
        ax.plot(pc[0],  pr[0],  "go", markersize=8, label="Start")
        ax.plot(pc[-1], pr[-1], "r*", markersize=12, label="Goal")
        ax.legend(loc="upper right", fontsize=8)

    ax.set_title("A* Path on Costmap")

    fig.suptitle("SIH 26126 — Traversability → A* Integration",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()

    out_path = os.path.join(
        os.path.dirname(__file__), "..", "costmap_astar_result.png"
    )
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    print(f"Plot saved → {os.path.abspath(out_path)}")
    plt.close(fig)

except ImportError:
    print("matplotlib not available — skipping plot.")

# ------------------------------------------------------------------
# 8. Edge-case: start or goal on a blocked cell
# ------------------------------------------------------------------
blocked_start = (85, 15)  # inside the FORBIDDEN zone
path_blocked = planner.plan(blocked_start, goal)
assert path_blocked == [], \
    "Expected empty path when start is on a FORBIDDEN cell"
print("Edge case (start on FORBIDDEN) → correctly returned empty path ✓")

# ------------------------------------------------------------------
# 9. Verify smooth (cost=0) cells are traversable
# ------------------------------------------------------------------
smooth_start = (50, 5)   # SMOOTH region
smooth_goal  = (50, 50)  # still SMOOTH, before the wall gap
path_smooth = planner.plan(smooth_start, smooth_goal)
assert len(path_smooth) > 0, \
    "Expected a valid path through cost=0 smooth terrain"
# Verify every cell on the path has cost >= 0 and is not blocked
for r, c in path_smooth:
    assert costmap[r, c] >= 0.0, f"Negative cost at ({r},{c})"
    assert not blocked_mask[r, c], f"Path crossed blocked cell at ({r},{c})"
print("Edge case (smooth cost=0 traversal) → path valid ✓")

print("\nDone.")
