import cv2
import numpy as np
import sys
import os
from pathlib import Path
import glob

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.traversability.bev import BEVProjector

def run_demo():
    print("=" * 50)
    print("BEV PROJECTION DEMO")
    print("=" * 50)

    # Find a sample image
    # Assuming dataset is in data/RELLIS-3D or similar
    # We will search for a random jpg image inside data/
    image_files = glob.glob("data/**/*.jpg", recursive=True) + glob.glob("data/**/*.png", recursive=True)
    
    if not image_files:
        print("No sample images found in data/. Creating a dummy checkerboard image.")
        sample_img = np.zeros((720, 1280, 3), dtype=np.uint8)
        # Draw a perspective grid
        for i in range(10, 720, 50):
            cv2.line(sample_img, (0, i), (1280, i), (255, 255, 255), 2)
        for i in range(10, 1280, 50):
            cv2.line(sample_img, (i, 0), (i, 720), (255, 255, 255), 2)
    else:
        sample_path = image_files[0]
        print(f"Using sample image: {sample_path}")
        sample_img = cv2.imread(sample_path)
        if sample_img is None:
            print("Failed to read image. Using dummy.")
            sample_img = np.zeros((720, 1280, 3), dtype=np.uint8)

    projector = BEVProjector("configs/bev.yaml")
    
    bev_out = projector.project(sample_img, border_value=(50, 50, 50))
    
    out_dir = Path("outputs/bev")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    orig_out = out_dir / "original.jpg"
    bev_out_path = out_dir / "bev.jpg"
    
    cv2.imwrite(str(orig_out), sample_img)
    cv2.imwrite(str(bev_out_path), bev_out)
    
    print(f"Original saved to: {orig_out}")
    print(f"BEV saved to: {bev_out_path}")
    print("DONE.")

if __name__ == "__main__":
    run_demo()
