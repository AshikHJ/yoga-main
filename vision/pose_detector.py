"""
Pose Detector Module for AI Yoga Assistant.
Wraps MediaPipe Pose Landmarker with robust fallback modes, RGB frame processing,
and full-body visibility & confidence evaluation.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from config import settings
from vision.landmarks import LandmarkHelper

logger = logging.getLogger(__name__)


class PoseDetector:
    """Detects 33 human pose landmarks from video frames using MediaPipe."""

    def __init__(
        self,
        min_detection_confidence: float = settings.MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence: float = settings.MIN_TRACKING_CONFIDENCE,
        model_complexity: int = 1,
    ):
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.model_complexity = model_complexity
        self.detector = None
        self._mode = "none"
        self._init_detector()

    def _init_detector(self) -> None:
        """Initializes MediaPipe detector."""
        # Try MediaPipe solutions.pose
        try:
            import mediapipe as mp
            if hasattr(mp, "solutions") and hasattr(mp.solutions, "pose"):
                self.detector = mp.solutions.pose.Pose(
                    static_image_mode=False,
                    model_complexity=self.model_complexity,
                    smooth_landmarks=True,
                    enable_segmentation=False,
                    min_detection_confidence=self.min_detection_confidence,
                    min_tracking_confidence=self.min_tracking_confidence,
                )
                self._mode = "solutions"
                logger.info("Initialized MediaPipe solutions.pose successfully.")
                return
        except Exception as e:
            logger.debug(f"MediaPipe solutions.pose init failed: {e}")

        # Try MediaPipe tasks API
        try:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            # Check if model exists or download pose_landmarker_heavy / full
            model_path = settings.MODELS_DIR / "pose_landmarker.task"
            if not model_path.exists():
                logger.info("Downloading pose_landmarker model task file...")
                import urllib.request
                url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task"
                try:
                    urllib.request.urlretrieve(url, str(model_path))
                    logger.info("Pose landmarker model downloaded successfully.")
                except Exception as down_err:
                    logger.warning(f"Could not auto-download task model: {down_err}")

            if model_path.exists():
                base_options = python.BaseOptions(model_asset_path=str(model_path))
                options = vision.PoseLandmarkerOptions(
                    base_options=base_options,
                    running_mode=vision.RunningMode.IMAGE,
                    min_pose_detection_confidence=self.min_detection_confidence,
                    min_pose_presence_confidence=settings.MIN_PRESENCE_CONFIDENCE,
                    min_tracking_confidence=self.min_tracking_confidence,
                    num_poses=1,
                )
                self.detector = vision.PoseLandmarker.create_from_options(options)
                self._mode = "tasks"
                logger.info("Initialized MediaPipe Tasks PoseLandmarker successfully.")
                return
        except Exception as e:
            logger.warning(f"MediaPipe Tasks API init failed: {e}")

        if not self.detector:
            logger.error("Failed to initialize any MediaPipe Pose detector backend.")

    def process_frame(
        self,
        frame: np.ndarray,
    ) -> Tuple[Dict[str, Dict[str, float]], bool, str, float]:
        """
        Processes a BGR video frame and extracts 33 pose landmarks.
        
        Args:
            frame: OpenCV BGR frame (numpy array).
            
        Returns:
            Tuple of:
                - landmarks_dict (Dict mapping landmark names to coordinates/visibility)
                - is_body_visible (bool)
                - status_message (str)
                - confidence_score (float 0.0 - 1.0)
        """
        if frame is None or self.detector is None:
            return {}, False, "Detector not initialized or empty frame.", 0.0

        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        try:
            if self._mode == "solutions":
                results = self.detector.process(rgb_frame)
                if not results or not results.pose_landmarks:
                    return {}, False, "No person detected. Stand in view of the camera.", 0.0

                raw_lms = results.pose_landmarks.landmark
                parsed = LandmarkHelper.parse_mediapipe_landmarks(raw_lms, image_width=w, image_height=h)

            elif self._mode == "tasks":
                import mediapipe as mp
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                detection_result = self.detector.detect(mp_image)

                if not detection_result.pose_landmarks:
                    return {}, False, "No person detected. Stand in view of the camera.", 0.0

                raw_lms = detection_result.pose_landmarks[0]
                parsed = LandmarkHelper.parse_mediapipe_landmarks(raw_lms, image_width=w, image_height=h)

            else:
                return {}, False, "No valid detector backend.", 0.0

            # Run full body visibility check
            is_visible, msg, confidence = LandmarkHelper.check_body_visibility(parsed)
            return parsed, is_visible, msg, confidence

        except Exception as e:
            logger.error(f"Error during pose processing: {e}")
            return {}, False, f"Detection error: {e}", 0.0

    def close(self) -> None:
        """Releases detector resources."""
        try:
            if self.detector and hasattr(self.detector, "close"):
                self.detector.close()
        except Exception:
            pass
