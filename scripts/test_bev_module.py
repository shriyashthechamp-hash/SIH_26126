import unittest
import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.traversability.bev import BEVProjector

class TestBEVProjector(unittest.TestCase):
    def setUp(self):
        self.projector = BEVProjector(config_path="configs/bev.yaml")
        
    def test_dimensions(self):
        # Input can be any size, output must match config
        dummy_img = np.zeros((720, 1280, 3), dtype=np.uint8)
        bev_img = self.projector.project(dummy_img)
        
        self.assertEqual(bev_img.shape[0], self.projector.out_h)
        self.assertEqual(bev_img.shape[1], self.projector.out_w)
        self.assertEqual(bev_img.shape[2], 3)
        
    def test_deterministic(self):
        dummy_img = np.ones((720, 1280), dtype=np.uint8) * 128
        bev1 = self.projector.project(dummy_img)
        bev2 = self.projector.project(dummy_img)
        
        self.assertTrue(np.allclose(bev1, bev2))
        self.assertFalse(np.any(np.isnan(bev1)))
        
    def test_resize_handling(self):
        # Input wrong size -> should resize and project without error
        wrong_size = np.zeros((480, 640), dtype=np.uint8)
        bev_img = self.projector.project(wrong_size)
        self.assertEqual(bev_img.shape[0], self.projector.out_h)
        self.assertEqual(bev_img.shape[1], self.projector.out_w)

if __name__ == '__main__':
    unittest.main()
