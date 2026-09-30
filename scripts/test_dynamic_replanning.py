#!/usr/bin/env python3
"""
Dynamic replanning integration test for SIH 26126.

Demonstrates the full loop:

  1. Build initial environment  →  plan PATH_1
  2. Introduce a dynamic obstacle across PATH_1
  3. Validate PATH_1 against updated environment  →  INVALID
  4. Re-plan  →  PATH_2 (different route)
  5. Edge case: block every possible route  →  NO VALID PATH

Uses the real TraversabilityCostmap + costmap_adapter + AStarPlanner
+ path_validator — no modules are modified.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from src.traversability.costmap import TraversabilityCostmap
from src.planning.costmap_adapter import get_planning_arrays
from src.planning.astar import AStarPlanner
from src.planning.path_validator import validate_path

SEP = "=" * 60

# ------------------------------------------------------------------
# Class IDs (from configs/traversability.yaml):
#   0: SMOOTH      cost 0.0
#   1: ROUGH       cost 0.3
#   2: BUMPY       cost 0.6
#   3: FORBIDDEN   cost 1.0  (blocked)
#   4: OBSTACLE    cost 1.0  (blocked)
#   5: BACKGROUND  cost 0.8
# ------------------------------------------------------------------
CLASS_SMOOTH   = 0
CLASS_OBSTACLE = 4

ROWS, COLS = 80, 100
START = (40, 10)
GOAL  = (40, 90)

trav = TraversabilityCostmap(config_path="configs/traversability.yaml")


def build_initial_mask():
    """All-smooth grid with a vertical wall + wide gap (initial scene)."""
    mask = np.full((ROWS, COLS), CLASS_SMOOTH, dtype=np.uint8)

    # Vertical wall at col 50, rows 0–24 and 60–79.
    # Wide gap at rows 25–59 so PATH_1 crosses comfortably at row 40.
    mask[0:25, 50]  = CLASS_OBSTACLE
    mask[60:80, 50] = CLASS_OBSTACLE
    return mask


def costmap_from_seg(seg_mask):
    """Seg mask → TraversabilityCostmap → (costmap, blocked_mask)."""
    result = trav.process(seg_mask)
    return get_planning_arrays(result)


# ==================================================================
# PHASE 1 — initial planning
# ==================================================================
print(SEP)
print("SIH 26126 — DYNAMIC REPLANNING TEST")
print(SEP)

seg_1 = build_initial_mask()
costmap_1, blocked_1 = costmap_from_seg(seg_1)

planner_1 = AStarPlanner(costmap_1, blocked_mask=blocked_1)
path_1 = planner_1.plan(START, GOAL)

print(f"  Initial path found : {'YES' if path_1 else 'NO'}")
print(f"  Initial path length: {len(path_1)} waypoints")
assert path_1, "Initial plan should succeed on the open grid."

# ==================================================================
# PHASE 2 — introduce a dynamic obstacle across PATH_1
# ==================================================================
# Find where PATH_1 crosses col 50 (through the gap) and block that
# section plus some margin so the old path is definitely severed.
seg_2 = seg_1.copy()
# Block the middle of the gap (rows 35–50) — severs PATH_1 at row 40
# but leaves narrow corridors at rows 25–34 and 51–59.
seg_2[35:51, 50] = CLASS_OBSTACLE

costmap_2, blocked_2 = costmap_from_seg(seg_2)

print(f"\n  Dynamic obstacle introduced: YES")
print(f"  Blocked cells before: {int(blocked_1.sum())}")
print(f"  Blocked cells after : {int(blocked_2.sum())}")

# ==================================================================
# PHASE 3 — validate old path against updated environment
# ==================================================================
val = validate_path(path_1, blocked_2)

print(f"\n  Old path valid after obstacle: {'YES' if val.valid else 'NO'}")
if not val.valid:
    print(f"  First invalid waypoint: index {val.first_invalid_index} "
          f"→ {val.first_invalid_cell}")
    print(f"  Reason: {val.reason}")

assert not val.valid, "PATH_1 must be invalid after the gap is blocked."

# ==================================================================
# PHASE 4 — replan
# ==================================================================
print(f"\n  Replanning triggered: YES")

planner_2 = AStarPlanner(costmap_2, blocked_mask=blocked_2)
path_2 = planner_2.plan(START, GOAL)

print(f"  New path found : {'YES' if path_2 else 'NO'}")
print(f"  New path length: {len(path_2)} waypoints")
assert path_2, "There is still a route around the wall."

path_changed = (path_1 != path_2)
print(f"  Path changed   : {'YES' if path_changed else 'NO'}")
assert path_changed, "PATH_2 must differ from PATH_1."

# Validate PATH_2 against the new environment.
val_2 = validate_path(path_2, blocked_2)
assert val_2.valid, "PATH_2 must be valid in the updated environment."
print(f"  PATH_2 valid in new env: YES")

# ==================================================================
# PHASE 5 — edge case: completely block all routes
# ==================================================================
seg_3 = seg_2.copy()
seg_3[:, 50] = CLASS_OBSTACLE             # full-height wall, no gap

costmap_3, blocked_3 = costmap_from_seg(seg_3)
planner_3 = AStarPlanner(costmap_3, blocked_mask=blocked_3)
path_3 = planner_3.plan(START, GOAL)

print(f"\n  Full blockage — replanning result: "
      f"{'PATH FOUND' if path_3 else 'NO VALID PATH'}")
assert path_3 == [], "No route should exist when the wall has no gap."

print(SEP)

# ==================================================================
# Visualisation
# ==================================================================
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # Helper: draw a costmap panel with path overlay.
    def draw_panel(ax, costmap, blocked, path, title,
                   extra_path=None, extra_label=None):
        # Base costmap.
        display = costmap.copy()
        display[blocked] = np.nan
        ax.imshow(display, cmap="YlOrRd", vmin=0.0, vmax=1.0,
                  interpolation="nearest", alpha=0.7)
        # Blocked overlay.
        overlay = np.zeros((*costmap.shape, 4))
        overlay[blocked] = [0.15, 0.15, 0.15, 0.9]
        ax.imshow(overlay, interpolation="nearest")

        if extra_path:
            er = [p[0] for p in extra_path]
            ec = [p[1] for p in extra_path]
            ax.plot(ec, er, color="salmon", linewidth=1.2,
                    linestyle="--", alpha=0.6, label=extra_label or "Old path")

        if path:
            pr = [p[0] for p in path]
            pc = [p[1] for p in path]
            ax.plot(pc, pr, color="dodgerblue", linewidth=2.0,
                    label="A* path")
            ax.plot(pc[0],  pr[0],  "go", markersize=9, label="Start")
            ax.plot(pc[-1], pr[-1], "r*", markersize=13, label="Goal")

        ax.set_title(title, fontsize=11)
        ax.legend(loc="upper right", fontsize=7)

    # LEFT: initial environment + PATH_1
    draw_panel(axes[0], costmap_1, blocked_1, path_1,
               "Initial Costmap + PATH_1")

    # RIGHT: updated environment + PATH_2 (with old path ghosted)
    draw_panel(axes[1], costmap_2, blocked_2, path_2,
               "Updated Costmap + PATH_2\n(old path dashed)",
               extra_path=path_1, extra_label="Old PATH_1 (invalid)")

    fig.suptitle("SIH 26126 — Dynamic Replanning",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()

    out = os.path.join(
        os.path.dirname(__file__), "..", "dynamic_replanning_result.png"
    )
    fig.savefig(out, dpi=140, bbox_inches="tight")
    print(f"\nPlot saved → {os.path.abspath(out)}")
    plt.close(fig)

except ImportError:
    print("\nmatplotlib not available — skipping plot.")

print("\nDone.")
