import cv2
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.perception.camera import create_camera_from_config
from src.localization.visual_odometry import VisualOdometry


def main():
    print("=" * 60)
    print("SIH 26126 — VISUAL ODOMETRY TEST")
    print("=" * 60)

    camera = create_camera_from_config("configs/camera.yaml")

    if not camera.is_opened():
        print("ERROR: Camera could not be opened.")
        return

    vo = VisualOdometry()

    print("Camera: OK")
    print("Visual Odometry: OK")
    print("Move the camera slowly.")
    print("Press Q to quit.")
    print("=" * 60)

    while True:
        ret, frame = camera.read()

        if not ret or frame is None:
            print("Camera frame failed.")
            break

        pose = vo.update(frame)

        display = frame.copy()

        cv2.putText(
            display,
            f"X: {pose.x:.3f}",
            (30, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        cv2.putText(
            display,
            f"Y: {pose.y:.3f}",
            (30, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        cv2.putText(
            display,
            f"Yaw: {pose.yaw:.3f}",
            (30, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        cv2.putText(
            display,
            f"Matches: {pose.num_matches}",
            (30, 145),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2,
        )

        cv2.putText(
            display,
            f"Inliers: {pose.num_inliers}",
            (30, 180),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2,
        )

        cv2.putText(
            display,
            f"Tracking: {pose.tracking_quality:.2f}",
            (30, 215),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 200, 255),
            2,
        )

        cv2.imshow(
            "SIH 26126 - Visual Odometry",
            display,
        )

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
    