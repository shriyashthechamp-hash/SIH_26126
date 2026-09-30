#!/usr/bin/env python3
"""
Test A* planner on a synthetic costmap.

Creates a 40×60 grid with:
  - uniform base cost of 1.0
  - a vertical obstacle wall with a narrow gap
  - start on the left side, goal on the right side

Runs AStarPlanner.plan() and prints summary info, then shows
an ASCII + matplotlib visualisation of the result.
"""

import sys
import os

# Allow running from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from src.planning.astar import AStarPlanner


# ------------------------------------------------------------------
# 1. Build a synthetic costmap
# ------------------------------------------------------------------
ROWS, COLS = 40, 60

# Base cost of 0.0 (smooth terrain)
costmap = np.zeros((ROWS, COLS), dtype=np.float64)
blocked_mask = np.zeros((ROWS, COLS), dtype=bool)

# Vertical wall at column 30, rows 0-34 (blocked).
WALL_COL = 30
blocked_mask[0:35, WALL_COL] = True       # impassable

# Gap at rows 35-39 so a path can pass through.
# (Those cells keep blocked=False, cost=0.0)

# Add a patch of "rough terrain" with higher cost.
costmap[10:20, 40:50] = 5.0

# ------------------------------------------------------------------
# 2. Plan
# ------------------------------------------------------------------
start = (20, 5)
goal  = (20, 55)

planner = AStarPlanner(costmap, blocked_mask=blocked_mask)
path = planner.plan(start, goal)

# ------------------------------------------------------------------
# 3. Print summary
# ------------------------------------------------------------------
SEPARATOR = "=" * 60
print(SEPARATOR)
print("SIH 26126 — A* PLANNER TEST")
print(SEPARATOR)
print(f"  Grid size  : {ROWS} × {COLS}")
print(f"  Start      : {start}")
print(f"  Goal       : {goal}")
print(f"  Path found : {'YES' if path else 'NO'}")
print(f"  Path length: {len(path)} waypoints")
print(SEPARATOR)

if not path:
    print("No valid route — check costmap configuration.")
    sys.exit(1)

# ------------------------------------------------------------------
# 4. ASCII visualisation (fits most terminals)
# ------------------------------------------------------------------
print("\nASCII preview (S=start, G=goal, ·=path, █=wall, ░=rough):\n")

path_set = set(path)

for r in range(ROWS):
    row_chars = []
    for c in range(COLS):
        if (r, c) == start:
            row_chars.append("S")
        elif (r, c) == goal:
            row_chars.append("G")
        elif (r, c) in path_set:
            row_chars.append("·")
        elif blocked_mask[r, c]:
            row_chars.append("█")
        elif costmap[r, c] > 0.0:
            row_chars.append("░")
        else:
            row_chars.append(" ")
    print("".join(row_chars))

print()

# ------------------------------------------------------------------
# 5. Matplotlib visualisation (if available)
# ------------------------------------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")            # non-interactive backend
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    fig, ax = plt.subplots(figsize=(12, 8))

    # Display costmap – blocked cells shown in black.
    display = costmap.copy()
    display[blocked_mask] = np.nan

    ax.imshow(
        display,
        origin="upper",
        cmap="YlOrRd",
        interpolation="nearest",
        vmin=0.0,
        vmax=6.0,
    )

    # Overlay path.
    if path:
        pr = [p[0] for p in path]
        pc = [p[1] for p in path]
        ax.plot(pc, pr, color="dodgerblue", linewidth=2.0, label="A* path")
        ax.plot(pc[0],  pr[0],  "go", markersize=10, label="Start")
        ax.plot(pc[-1], pr[-1], "r*", markersize=14, label="Goal")

    ax.set_title("A* Planner — Synthetic Costmap", fontsize=14)
    ax.set_xlabel("Column")
    ax.set_ylabel("Row")
    ax.legend(loc="upper right")

    out_path = os.path.join(
        os.path.dirname(__file__), "..", "astar_test_result.png"
    )
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    print(f"Plot saved → {os.path.abspath(out_path)}")
    plt.close(fig)

except ImportError:
    print("matplotlib not available — skipping plot.")

# ------------------------------------------------------------------
# 6. Quick edge-case: blocked goal
# ------------------------------------------------------------------
blocked_mask_2 = blocked_mask.copy()
blocked_mask_2[goal[0], goal[1]] = True

planner2 = AStarPlanner(costmap, blocked_mask=blocked_mask_2)
blocked_path = planner2.plan(start, goal)
assert blocked_path == [], "Expected empty path when goal is blocked"
print("Edge case (blocked goal) → correctly returned empty path ✓")

print("\nDone.")
