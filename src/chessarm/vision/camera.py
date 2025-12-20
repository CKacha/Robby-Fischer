from __future__ import annotations
import cv2
import numpy as np
import logging

log = logging.getLogger(__name__)

class UsbCamera:
    def __init__(self, device_id: int, width: int, height: int, fps: int, show_window: bool = False) -> None:
        self.device_id = device_id
        self.width = width
        self.height = height
        self.fps = fps
        self.show_window = show_window
        self.cap: cv2.VideoCapture | None = None

    def __enter__(self) -> "UsbCamera":
        self.cap = cv2.VideoCapture(self.device_id)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera device {self.device_id}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.width))
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.height))
        self.cap.set(cv2.CAP_PROP_FPS, float(self.fps))
        log.info(f"Camera opened: /dev/video? (id={self.device_id}) {self.width}x{self.height}@{self.fps}")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.cap:
            self.cap.release()
        if self.show_window:
            cv2.destroyAllWindows()

    def read(self) -> np.ndarray:
        assert self.cap is not None
        ok, frame = self.cap.read()
        if not ok or frame is None:
            raise RuntimeError("Failed to read camera frame")
        if self.show_window:
            cv2.imshow("CHESSARM Camera", frame)
            cv2.waitKey(1)
        return frame
