import cv2
import numpy as np
from dataclasses import dataclass


@dataclass
class PoseEstimate:
    x: float
    y: float
    yaw: float
    tracking_quality: float
    num_matches: int
    num_inliers: int


class VisualOdometry:
    """
    Lightweight monocular visual odometry.

    Input:
        Consecutive RGB/BGR frames.

    Output:
        Relative accumulated pose:
            x
            y
            yaw
            tracking_quality

    Important:
        Monocular VO has scale ambiguity.
        Therefore x/y are relative units, not metric meters.
    """

    def __init__(
        self,
        focal_length=None,
        principal_point=None,
        min_matches=20,
    ):
        self.prev_gray = None

        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0

        self.min_matches = min_matches

        self.orb = cv2.ORB_create(
            nfeatures=1500,
            scaleFactor=1.2,
            nlevels=8,
        )

        self.matcher = cv2.BFMatcher(
            cv2.NORM_HAMMING,
            crossCheck=True,
        )

        self.focal_length = focal_length
        self.principal_point = principal_point

    def _get_camera_matrix(self, frame):
        h, w = frame.shape[:2]

        if self.focal_length is None:
            focal = float(max(w, h))
        else:
            focal = float(self.focal_length)

        if self.principal_point is None:
            cx = w / 2.0
            cy = h / 2.0
        else:
            cx, cy = self.principal_point

        return np.array(
            [
                [focal, 0.0, cx],
                [0.0, focal, cy],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    def reset(self):
        self.prev_gray = None

        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0

    def update(self, frame):
        """
        Process one frame.

        Returns:
            PoseEstimate
        """

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        keypoints, descriptors = self.orb.detectAndCompute(
            gray,
            None,
        )

        # First frame initializes tracking.
        if self.prev_gray is None:
            self.prev_gray = gray

            return PoseEstimate(
                x=self.x,
                y=self.y,
                yaw=self.yaw,
                tracking_quality=0.0,
                num_matches=0,
                num_inliers=0,
            )

        # No descriptors -> tracking failure.
        if descriptors is None:
            self.prev_gray = gray

            return PoseEstimate(
                x=self.x,
                y=self.y,
                yaw=self.yaw,
                tracking_quality=0.0,
                num_matches=0,
                num_inliers=0,
            )

        prev_keypoints, prev_descriptors = self.orb.detectAndCompute(
            self.prev_gray,
            None,
        )

        if prev_descriptors is None:
            self.prev_gray = gray

            return PoseEstimate(
                x=self.x,
                y=self.y,
                yaw=self.yaw,
                tracking_quality=0.0,
                num_matches=0,
                num_inliers=0,
            )

        matches = self.matcher.match(
            prev_descriptors,
            descriptors,
        )

        matches = sorted(
            matches,
            key=lambda m: m.distance,
        )

        if len(matches) < self.min_matches:
            self.prev_gray = gray

            return PoseEstimate(
                x=self.x,
                y=self.y,
                yaw=self.yaw,
                tracking_quality=0.0,
                num_matches=len(matches),
                num_inliers=0,
            )

        # Keep the strongest matches.
        good_matches = [m for m in matches if m.distance < 50.0]
        good_matches = good_matches[: min(len(good_matches), 300)]

        if len(good_matches) < self.min_matches:
            self.prev_gray = gray

            return PoseEstimate(
                x=self.x,
                y=self.y,
                yaw=self.yaw,
                tracking_quality=0.0,
                num_matches=len(good_matches),
                num_inliers=0,
            )

        pts_prev = np.float32(
            [
                prev_keypoints[m.queryIdx].pt
                for m in good_matches
            ]
        )

        pts_curr = np.float32(
            [
                keypoints[m.trainIdx].pt
                for m in good_matches
            ]
        )

        K = self._get_camera_matrix(frame)

        E, mask = cv2.findEssentialMat(
            pts_prev,
            pts_curr,
            K,
            method=cv2.RANSAC,
            prob=0.999,
            threshold=1.0,
        )

        if E is None or E.shape != (3, 3):
            self.prev_gray = gray

            return PoseEstimate(
                x=self.x,
                y=self.y,
                yaw=self.yaw,
                tracking_quality=0.0,
                num_matches=len(good_matches),
                num_inliers=0,
            )

        inlier_count, R, t, pose_mask = cv2.recoverPose(
            E,
            pts_prev,
            pts_curr,
            K,
            mask=mask,
        )

        tracking_quality = min(
            1.0,
            inlier_count / max(len(good_matches), 1),
        )

        if inlier_count >= self.min_matches and tracking_quality >= 0.1:
            # Monocular translation has unknown scale.
            translation = t.flatten()

            # We only use relative horizontal motion.
            dx = float(translation[0])
            dy = float(translation[2])

            # Estimate yaw from rotation matrix.
            delta_yaw = float(
                np.arctan2(
                    R[2, 0],
                    R[0, 0],
                )
            )

            self.x += dx
            self.y += dy
            self.yaw += delta_yaw

        self.prev_gray = gray

        return PoseEstimate(
            x=self.x,
            y=self.y,
            yaw=self.yaw,
            tracking_quality=tracking_quality,
            num_matches=len(good_matches),
            num_inliers=int(inlier_count),
        )

        