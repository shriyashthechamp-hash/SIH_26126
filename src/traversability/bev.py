import cv2
import numpy as np
import yaml
from pathlib import Path

class BEVProjector:
    """
    Approximate Monocular Inverse Perspective Mapping (IPM) to Bird's Eye View (BEV).
    
    This is an initial assumption-based geometric projection.
    It does NOT represent a true calibrated 3D metric reconstruction.
    """
    def __init__(self, config_path="configs/bev.yaml"):
        self.load_config(config_path)
        self.compute_homography()

    def load_config(self, config_path):
        path = Path(config_path)
        if not path.exists():
            print(f"Warning: {config_path} not found. Using default BEV parameters.")
            config = {}
        else:
            with open(path, "r") as f:
                config = yaml.safe_load(f)
                
        bev = config.get("bev", {})
        
        self.in_w = bev.get("input_width", 1280)
        self.in_h = bev.get("input_height", 720)
        
        self.out_w = bev.get("output_width", 400)
        self.out_h = bev.get("output_height", 400)
        
        # Camera extrinsics assumptions
        self.cam_h_m = bev.get("camera_height_m", 0.5)
        self.pitch_deg = bev.get("camera_pitch_deg", 15.0)
        self.hfov_deg = bev.get("horizontal_fov_deg", 60.0)
        
        # Spatial bounds in meters relative to camera base
        self.near_m = bev.get("near_distance_m", 0.5)
        self.far_m = bev.get("far_distance_m", 10.0)
        self.left_m = bev.get("left_distance_m", -5.0)
        self.right_m = bev.get("right_distance_m", 5.0)
        
    def compute_homography(self):
        """
        Compute the perspective transform matrix from the image plane to the BEV ground plane.
        This uses basic trigonometry assuming a flat ground plane and a pinhole camera model.
        """
        # Focal length estimation based on horizontal FOV
        fx = (self.in_w / 2.0) / np.tan(np.deg2rad(self.hfov_deg / 2.0))
        fy = fx # Assume square pixels
        cx, cy = self.in_w / 2.0, self.in_h / 2.0
        
        # Camera intrinsic matrix
        K = np.array([
            [fx, 0, cx],
            [0, fy, cy],
            [0, 0, 1]
        ], dtype=np.float32)
        
        # Pitch rotation matrix (rotation around X-axis by pitch)
        # Note: Standard camera frame has Z forward, Y down, X right.
        pitch = np.deg2rad(self.pitch_deg)
        # To look down, we rotate around X axis.
        R_pitch = np.array([
            [1, 0, 0],
            [0, np.cos(pitch), -np.sin(pitch)],
            [0, np.sin(pitch), np.cos(pitch)]
        ], dtype=np.float32)
        
        # Transformation from camera to ground frame
        # Camera is at height cam_h_m. Ground is at Y = cam_h_m in camera frame.
        # So we can construct a homography matrix from the ground plane to the image plane,
        # then invert it.
        
        # We'll map specific metric coordinates on the ground plane to image coordinates.
        # Ground coordinates (Z is forward, X is right).
        # We select 4 points on the ground plane [X, Z]:
        # 1. Bottom Left: [left_m, near_m]
        # 2. Bottom Right: [right_m, near_m]
        # 3. Top Left: [left_m, far_m]
        # 4. Top Right: [right_m, far_m]
        
        src_points_3d = np.array([
            [self.left_m, self.cam_h_m, self.near_m],
            [self.right_m, self.cam_h_m, self.near_m],
            [self.left_m, self.cam_h_m, self.far_m],
            [self.right_m, self.cam_h_m, self.far_m]
        ], dtype=np.float32)
        
        # Project these 3D ground points to the image plane
        img_points = []
        for pt in src_points_3d:
            # Apply pitch rotation (from unpitched camera to pitched camera)
            # Actually, let's treat the points as already in unrotated ground-aligned camera frame.
            # Then rotate by pitch to get to actual camera frame.
            # Since camera is pitched DOWN, points move UP in the image.
            # Wait, if camera pitches down, it's a positive rotation around X axis (Y moves towards Z).
            pt_cam = R_pitch @ pt
            
            # Project to image
            u = (fx * pt_cam[0] / pt_cam[2]) + cx
            v = (fy * pt_cam[1] / pt_cam[2]) + cy
            img_points.append([u, v])
            
        self.img_points = np.array(img_points, dtype=np.float32)
        
        # Now define the corresponding points in the BEV output image.
        # BEV image: Top-Left is (0,0), Bottom-Right is (out_w, out_h).
        # X: left_m -> 0, right_m -> out_w
        # Z: far_m -> 0 (top of image), near_m -> out_h (bottom of image)
        
        dst_points = np.array([
            [0, self.out_h],                # Bottom Left
            [self.out_w, self.out_h],       # Bottom Right
            [0, 0],                         # Top Left
            [self.out_w, 0]                 # Top Right
        ], dtype=np.float32)
        
        # Compute the homography matrix from image to BEV
        self.M = cv2.getPerspectiveTransform(self.img_points, dst_points)
        
    def project(self, image: np.ndarray, border_value=(0,0,0), is_mask=False) -> np.ndarray:
        """
        Projects an input image/mask to BEV.
        """
        # Resize input if it doesn't match expected dimensions to avoid homography mismatch
        h, w = image.shape[:2]
        if w != self.in_w or h != self.in_h:
            image = cv2.resize(image, (self.in_w, self.in_h), interpolation=cv2.INTER_NEAREST if is_mask else cv2.INTER_LINEAR)
            
        interp = cv2.INTER_NEAREST if is_mask else cv2.INTER_LINEAR
        
        bev = cv2.warpPerspective(
            image, 
            self.M, 
            (self.out_w, self.out_h), 
            flags=interp, 
            borderMode=cv2.BORDER_CONSTANT, 
            borderValue=border_value
        )
        return bev
