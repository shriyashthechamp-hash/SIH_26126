"""
Adapter to integrate TraversabilityCostmap output with AStarPlanner.
"""

import numpy as np
from typing import Tuple

from src.traversability.costmap import TraversabilityResult


def get_planning_arrays(
    trav_result: TraversabilityResult,
    blocked_threshold: float = 1.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Converts a TraversabilityResult into the explicit structures
    needed by the AStarPlanner.
    
    Parameters
    ----------
    trav_result : TraversabilityResult
        The result from TraversabilityCostmap.process()
    blocked_threshold : float
        The cost value at or above which a cell is considered impassable.
        Default is 1.0 (OBSTACLE / FORBIDDEN).

    Returns
    -------
    costmap : np.ndarray (float64)
        2D array of traversal costs.
    blocked_mask : np.ndarray (bool)
        2D boolean array where True indicates impassable terrain.
    """
    costmap = trav_result.costmap.astype(np.float64, copy=True)
    blocked_mask = costmap >= blocked_threshold
    
    return costmap, blocked_mask
