"""
Path validity checker for SIH 26126.

Given an existing A* path (list of (row, col) waypoints) and a
current environment state (blocked_mask + optional cost threshold),
determines whether the path is still safe to follow.

This module does NOT modify the path — it only inspects it.
Replanning is the caller's responsibility.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np


Cell = Tuple[int, int]


@dataclass
class ValidationResult:
    """Result of validating a path against the current environment."""

    valid: bool
    """True if every waypoint on the path is still traversable."""

    first_invalid_index: Optional[int]
    """Index into the path list of the first waypoint that fails
    validation, or None if the path is valid."""

    first_invalid_cell: Optional[Cell]
    """(row, col) of the first invalid waypoint, or None."""

    reason: str
    """Human-readable explanation."""


def validate_path(
    path: List[Cell],
    blocked_mask: np.ndarray,
    costmap: Optional[np.ndarray] = None,
    cost_threshold: Optional[float] = None,
) -> ValidationResult:
    """
    Check whether *path* is still traversable.

    A waypoint is invalid if:
      1. It falls on a blocked cell (``blocked_mask[r, c]`` is True), OR
      2. An optional *cost_threshold* is given **and** the cell's cost
         in *costmap* meets or exceeds that threshold.

    Parameters
    ----------
    path : list[(row, col)]
        Ordered waypoints produced by AStarPlanner.
    blocked_mask : np.ndarray (bool), shape (H, W)
        Current blocked-cell map.
    costmap : np.ndarray (float), shape (H, W), optional
        Current traversal cost grid.  Only needed when
        *cost_threshold* is set.
    cost_threshold : float, optional
        If provided, any waypoint whose cost >= this value is
        considered invalid even if it is not in blocked_mask.

    Returns
    -------
    ValidationResult
    """
    if not path:
        return ValidationResult(
            valid=True,
            first_invalid_index=None,
            first_invalid_cell=None,
            reason="Empty path is trivially valid.",
        )

    rows, cols = blocked_mask.shape

    for idx, (r, c) in enumerate(path):
        # Out-of-bounds check.
        if r < 0 or r >= rows or c < 0 or c >= cols:
            return ValidationResult(
                valid=False,
                first_invalid_index=idx,
                first_invalid_cell=(r, c),
                reason=f"Waypoint {idx} ({r}, {c}) is out of bounds.",
            )

        # Blocked check.
        if blocked_mask[r, c]:
            return ValidationResult(
                valid=False,
                first_invalid_index=idx,
                first_invalid_cell=(r, c),
                reason=f"Waypoint {idx} ({r}, {c}) is blocked.",
            )

        # Optional cost-threshold check.
        if (
            cost_threshold is not None
            and costmap is not None
            and costmap[r, c] >= cost_threshold
        ):
            return ValidationResult(
                valid=False,
                first_invalid_index=idx,
                first_invalid_cell=(r, c),
                reason=(
                    f"Waypoint {idx} ({r}, {c}) cost "
                    f"{costmap[r, c]:.3f} >= threshold {cost_threshold}."
                ),
            )

    return ValidationResult(
        valid=True,
        first_invalid_index=None,
        first_invalid_cell=None,
        reason="All waypoints are traversable.",
    )
