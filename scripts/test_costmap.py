import unittest
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.traversability.costmap import TraversabilityCostmap

class TestCostmap(unittest.TestCase):
    def setUp(self):
        self.costmap = TraversabilityCostmap(config_path="configs/traversability.yaml")
        
    def test_class_mapping(self):
        mask = np.array([[0, 1, 2], [3, 4, 5]], dtype=np.uint8)
        result = self.costmap.process(mask)
        
        # dtypes
        self.assertEqual(result.costmap.dtype, np.float32)
        
        # shapes
        self.assertEqual(result.costmap.shape, (2, 3))
        
        # specific values
        self.assertAlmostEqual(result.costmap[0, 0], 0.0) # SMOOTH
        self.assertAlmostEqual(result.costmap[0, 1], 0.3) # ROUGH
        self.assertAlmostEqual(result.costmap[0, 2], 0.6) # BUMPY
        self.assertAlmostEqual(result.costmap[1, 0], 1.0) # FORBIDDEN
        self.assertAlmostEqual(result.costmap[1, 1], 1.0) # OBSTACLE
        self.assertAlmostEqual(result.costmap[1, 2], 0.8) # BACKGROUND
        
    def test_smooth_is_zero(self):
        mask = np.zeros((10, 10), dtype=np.uint8)
        result = self.costmap.process(mask)
        self.assertTrue(np.all(result.costmap == 0.0))
        
    def test_obstacle_is_blocked(self):
        mask = np.full((10, 10), 4, dtype=np.uint8)
        result = self.costmap.process(mask)
        self.assertTrue(np.all(result.costmap == 1.0))

    def test_random_mask(self):
        mask = np.random.randint(0, 6, size=(64, 64), dtype=np.uint8)
        result = self.costmap.process(mask)
        
        self.assertTrue(np.max(result.costmap) <= 1.0)
        self.assertTrue(np.min(result.costmap) >= 0.0)
        
if __name__ == '__main__':
    unittest.main()
