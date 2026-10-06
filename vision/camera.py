"""
Threaded Camera Capture Worker for AI Yoga Assistant.
Runs OpenCV webcam capture and MediaPipe landmark detection on a dedicated QThread
to ensure zero GUI stutter or frame freezing.
"""

import logging
import time
from typing import Optional
import cv2
import numpy as np
from PySide6.QtCore import QMutex, QThread, Signal

from config import settings
from vision.pose_detector import PoseDetector

logger = logging.getLogger(__name__)


class CameraWorker(QThread):
    """
    QThread worker that captures frames from a webcam, performs pose landmark extraction,
    and emits Qt signals to the main UI thread.
    """

    # Signals:
    # frame_ready(raw_frame, landmarks_dict, is_body_visible, status_message, confidence)
    frame_ready = Signal(object, object, bool, str, float)
    error_occurred = Signal(str)
    camera_started = Signal()
    camera_stopped = Signal()

    def __init__(
        self,
        camera_index: int = settings.DEFAULT_CAMERA_INDEX,
        mirror: bool = settings.MIRROR_WEBCAM,
        parent=None,
    ):
        super().__init__(parent)
        self.camera_index = camera_index
        self.mirror = mirror
        self._is_running = False
        self._mutex = QMutex()
        self.detector: Optional[PoseDetector] = None

    def run(self) -> None:
        """Main thread loop."""
        self._mutex.lock()
        self._is_running = True
        self._mutex.unlock()

        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if cv2.os.name == 'nt' else cv2.CAP_ANY)

        if not cap.isOpened():
            # Try default backend without CAP_DSHOW
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            self.error_occurred.emit(
                f"Unable to access webcam at index {self.camera_index}. "
                "Please ensure the camera is connected and not in use by another application."
            )
            self._is_running = False
            return

        # Configure camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, settings.CAMERA_FPS)

        # Initialize detector on this worker thread
        self.detector = PoseDetector(
            min_detection_confidence=settings.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=settings.MIN_TRACKING_CONFIDENCE,
        )

        self.camera_started.emit()
        target_interval = 1.0 / settings.CAMERA_FPS

        while True:
            self._mutex.lock()
            running = self._is_running
            self._mutex.unlock()

            if not running:
                break

            loop_start = time.time()
            ret, frame = cap.read()

            if not ret or frame is None:
                self.error_occurred.emit("Failed to grab video frame from webcam.")
                time.sleep(0.1)
                continue

            if self.mirror:
                frame = cv2.flip(frame, 1)

            # Process frame through MediaPipe Pose detector
            landmarks, is_visible, status_msg, confidence = self.detector.process_frame(frame)

            # Emit results to UI
            self.frame_ready.emit(frame, landmarks, is_visible, status_msg, confidence)

            # Frame rate pacing
            elapsed = time.time() - loop_start
            sleep_time = max(0.001, target_interval - elapsed)
            time.sleep(sleep_time)

        # Cleanup
        cap.release()
        if self.detector:
            self.detector.close()
        self.camera_stopped.emit()
        logger.info("CameraWorker thread stopped and resources released.")

    def stop(self) -> None:
        """Safely signals the worker thread to stop and waits for exit."""
        self._mutex.lock()
        self._is_running = False
        self._mutex.unlock()
        self.wait(1000)
