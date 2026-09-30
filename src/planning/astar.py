"""
A* grid planner for SIH 26126.

Operates on a 2-D NumPy costmap where each cell holds a non-negative
traversal cost.  Blocked / impassable cells are explicitly defined
by a `blocked_mask` (boolean array) or by having cost `np.inf` or `np.nan`.
Smooth terrain has cost=0.0 and is perfectly traversable.

The planner uses 8-connected movement and a Euclidean admissible
heuristic.  Edge cost = distance × average cell cost of the two
endpoints, so the search naturally prefers cheaper terrain.

Dependencies: numpy, heapq (stdlib).
"""

import heapq
import math
from typing import List, Optional, Tuple

import numpy as np


# Type aliases ---------------------------------------------------------------
Cell = Tuple[int, int]            # (row, col)
Path = List[Cell]

# 8-connected neighbour offsets and their Euclidean step distances.
_NEIGHBOURS: List[Tuple[int, int, float]] = [
    (-1, -1, math.sqrt(2)),
    (-1,  0, 1.0),
    (-1,  1, math.sqrt(2)),
    ( 0, -1, 1.0),
    ( 0,  1, 1.0),
    ( 1, -1, math.sqrt(2)),
    ( 1,  0, 1.0),
    ( 1,  1, math.sqrt(2)),
]


class AStarPlanner:
    """
    Cost-weighted A* planner on a 2-D grid.

    Parameters
    ----------
    costmap : np.ndarray, shape (H, W)
        Non-negative values represent traversal cost.
        Values inf or nan are treated as impassable.
    blocked_mask : np.ndarray, shape (H, W), optional
        Boolean mask where True means the cell is impassable.
    """

    def __init__(self, costmap: np.ndarray, blocked_mask: Optional[np.ndarray] = None) -> None:
        if costmap.ndim != 2:
            raise ValueError(
                f"costmap must be 2-D, got shape {costmap.shape}"
            )
        self.costmap = costmap.astype(np.float64, copy=True)
        self.rows, self.cols = self.costmap.shape
        
        if blocked_mask is not None:
            if blocked_mask.shape != self.costmap.shape:
                raise ValueError("blocked_mask shape must match costmap shape")
            self.blocked_mask = blocked_mask.astype(bool, copy=True)
        else:
            self.blocked_mask = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _passable(self, r: int, c: int) -> bool:
        """Return True if (r, c) is inside the grid and traversable."""
        if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
            return False
        if self.blocked_mask is not None and self.blocked_mask[r, c]:
            return False
        v = self.costmap[r, c]
        return np.isfinite(v) and v >= 0.0

    @staticmethod
    def _heuristic(a: Cell, b: Cell) -> float:
        """Euclidean distance – admissible for 8-connected grids."""
        return math.hypot(a[0] - b[0], a[1] - b[1])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(
        self,
        start: Cell,
        goal: Cell,
    ) -> Path:
        """
        Find the lowest-cost path from *start* to *goal*.

        Parameters
        ----------
        start : (row, col)
        goal  : (row, col)

        Returns
        -------
        path : list[(row, col)]
            Ordered waypoints **including** start and goal.
            Empty list if no valid route exists or if start/goal
            are out of bounds / blocked.
        """
        if not self._passable(*start) or not self._passable(*goal):
            return []

        if start == goal:
            return [start]

        # Priority queue entries: (f_score, counter, cell)
        # `counter` breaks ties so that heapq never compares tuples.
        counter = 0
        open_set: list = []
        heapq.heappush(open_set, (0.0, counter, start))

        g_score: dict[Cell, float] = {start: 0.0}
        came_from: dict[Cell, Cell] = {}
        closed: set[Cell] = set()

        while open_set:
            _f, _cnt, current = heapq.heappop(open_set)

            if current == goal:
                return self._reconstruct(came_from, current)

            if current in closed:
                continue
            closed.add(current)

            cr, cc = current
            current_cost = self.costmap[cr, cc]

            for dr, dc, step_dist in _NEIGHBOURS:
                nr, nc = cr + dr, cc + dc

                if not self._passable(nr, nc):
                    continue

                neighbour = (nr, nc)

                if neighbour in closed:
                    continue

                neighbour_cost = self.costmap[nr, nc]

                # Edge weight = step distance × average terrain cost.
                edge = step_dist * 0.5 * (current_cost + neighbour_cost)
                tentative_g = g_score[current] + edge

                if tentative_g < g_score.get(neighbour, math.inf):
                    g_score[neighbour] = tentative_g
                    f = tentative_g + self._heuristic(neighbour, goal)
                    came_from[neighbour] = current
                    counter += 1
                    heapq.heappush(open_set, (f, counter, neighbour))

        # Exhausted the search – no path exists.
        return []

    # ------------------------------------------------------------------

    @staticmethod
    def _reconstruct(came_from: dict, current: Cell) -> Path:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
