import cv2
import yaml
import numpy as np
from pathlib import Path
from dataclasses import dataclass

@dataclass
class TraversabilityResult:
    costmap: np.ndarray
    visualization: np.ndarray
    mean_cost: float
    percent_traversable: float
    percent_blocked: float
    percent_unknown: float

class TraversabilityCostmap:
    def __init__(self, config_path="configs/traversability.yaml"):
        self.load_config(config_path)

    def load_config(self, config_path):
        path = Path(config_path)
        if not path.exists():
            print(f"Warning: {config_path} not found. Using default costs.")
            config = {}
        else:
            with open(path, "r") as f:
                config = yaml.safe_load(f)

        trav = config.get("traversability", {})
        
        # 0: SMOOTH, 1: ROUGH, 2: BUMPY, 3: FORBIDDEN, 4: OBSTACLE, 5: BACKGROUND
        self.cost_mapping = np.zeros(256, dtype=np.float32)
        self.cost_mapping[0] = trav.get("smooth_cost", 0.0)
        self.cost_mapping[1] = trav.get("rough_cost", 0.3)
        self.cost_mapping[2] = trav.get("bumpy_cost", 0.6)
        self.cost_mapping[3] = trav.get("forbidden_cost", 1.0)
        self.cost_mapping[4] = trav.get("obstacle_cost", 1.0)
        self.cost_mapping[5] = trav.get("background_cost", 0.8)
        
        self.obstacle_inflation = trav.get("obstacle_inflation", 0)

    def process(self, prediction_mask: np.ndarray) -> TraversabilityResult:
        """
        Convert a segmentation mask (H, W) of uint8 class IDs into a TraversabilityResult.
        """
        # Vectorized cost mapping
        costmap = self.cost_mapping[prediction_mask]

        if self.obstacle_inflation > 0:
            # Simple morphological dilation on blocked areas (cost >= 1.0)
            blocked_mask = (costmap >= 1.0).astype(np.uint8)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.obstacle_inflation*2+1, self.obstacle_inflation*2+1))
            dilated = cv2.dilate(blocked_mask, kernel)
            costmap[dilated > 0] = 1.0

        # Create heatmap visualization
        # We want green for 0, yellow for 0.5, red for 1.0. 
        # Matplotlib turbo or cv2 COLORMAP_JET can work. We'll use applyColorMap on 0-255.
        cost_uint8 = np.clip(costmap * 255.0, 0, 255).astype(np.uint8)
        
        # Use COLORMAP_JET: 0 (blue) to 255 (red).
        # We want smooth=0 to be green/cool, 1.0 to be red. Let's use COLORMAP_JET or VIRIDIS.
        # Actually JET is blue for 0, green for ~127, red for 255. 
        # Let's invert it or build a simple custom map if needed.
        # COLORMAP_TURBO is very nice and clear (blue->green->yellow->red).
        vis = cv2.applyColorMap(cost_uint8, cv2.COLORMAP_TURBO)
        
        # Calculate metrics
        total_pixels = max(costmap.size, 1)
        mean_cost = float(np.mean(costmap))
        
        # traversable < 0.5
        traversable = float(np.sum(costmap < 0.5)) / total_pixels * 100.0
        # blocked >= 1.0
        blocked = float(np.sum(costmap >= 1.0)) / total_pixels * 100.0
        # unknown/high = remaining (background)
        unknown = 100.0 - traversable - blocked

        return TraversabilityResult(
            costmap=costmap,
            visualization=vis,
            mean_cost=mean_cost,
            percent_traversable=traversable,
            percent_blocked=blocked,
            percent_unknown=unknown
        )
