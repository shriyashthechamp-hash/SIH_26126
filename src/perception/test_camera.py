import cv2

from camera import MacWebcamSource


def main():
    camera = MacWebcamSource(
        device_id=1,
        width=1280,
        height=720,
    )

    if not camera.is_opened():
        print("ERROR: Could not open camera.")
        return

    print("Camera opened successfully.")
    print("Press Q to quit.")

    while True:
        success, frame = camera.read()

        if not success:
            print("ERROR: Failed to read frame.")
            break

        cv2.imshow("SIH 26126 - Camera Test", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()