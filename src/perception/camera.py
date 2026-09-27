import abc

import cv2


class CameraSource(abc.ABC):

    @abc.abstractmethod
    def read(self):
        pass

    @abc.abstractmethod
    def is_opened(self):
        pass

    @abc.abstractmethod
    def release(self):
        pass


class MacWebcamSource(CameraSource):

    def __init__(self, device_id=0, width=1280, height=720):
        self.cap = cv2.VideoCapture(device_id)

        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def read(self):
        return self.cap.read()

    def is_opened(self):
        return self.cap.isOpened()

    def release(self):
        self.cap.release()