"""
Landmark Definitions and Visibility Verification Module.
Maps standard MediaPipe 33 keypoints, connection pairs, and provides
robust full-body visibility & confidence checking.
"""

from typing import Any, Dict, List, Optional, Tuple
from config import settings

# MediaPipe 33 Pose Landmark Names in Index Order
LANDMARK_NAMES = [
    "NOSE",
    "LEFT_EYE_INNER", "LEFT_EYE", "LEFT_EYE_OUTER",
    "RIGHT_EYE_INNER", "RIGHT_EYE", "RIGHT_EYE_OUTER",
    "LEFT_EAR", "RIGHT_EAR",
    "MOUTH_LEFT", "MOUTH_RIGHT",
    "LEFT_SHOULDER", "RIGHT_SHOULDER",
    "LEFT_ELBOW", "RIGHT_ELBOW",
    "LEFT_WRIST", "RIGHT_WRIST",
    "LEFT_PINKY", "RIGHT_PINKY",
    "LEFT_INDEX", "RIGHT_INDEX",
    "LEFT_THUMB", "RIGHT_THUMB",
    "LEFT_HIP", "RIGHT_HIP",
    "LEFT_KNEE", "RIGHT_KNEE",
    "LEFT_ANKLE", "RIGHT_ANKLE",
    "LEFT_HEEL", "RIGHT_HEEL",
    "LEFT_FOOT_INDEX", "RIGHT_FOOT_INDEX"
]

# Landmark Index Mapping
LANDMARK_INDEX_MAP = {name: idx for idx, name in enumerate(LANDMARK_NAMES)}

# Anatomical Connections for Visual Skeleton Rendering
SKELETON_CONNECTIONS = [
    # Head / Face
    ("NOSE", "LEFT_EYE"), ("LEFT_EYE", "LEFT_EAR"),
    ("NOSE", "RIGHT_EYE"), ("RIGHT_EYE", "RIGHT_EAR"),
    
    # Torso & Shoulders
    ("LEFT_SHOULDER", "RIGHT_SHOULDER"),
    ("LEFT_SHOULDER", "LEFT_HIP"),
    ("RIGHT_SHOULDER", "RIGHT_HIP"),
    ("LEFT_HIP", "RIGHT_HIP"),

    # Left Arm
    ("LEFT_SHOULDER", "LEFT_ELBOW"),
    ("LEFT_ELBOW", "LEFT_WRIST"),
    ("LEFT_WRIST", "LEFT_PINKY"),
    ("LEFT_WRIST", "LEFT_INDEX"),
    ("LEFT_WRIST", "LEFT_THUMB"),

    # Right Arm
    ("RIGHT_SHOULDER", "RIGHT_ELBOW"),
    ("RIGHT_ELBOW", "RIGHT_WRIST"),
    ("RIGHT_WRIST", "RIGHT_PINKY"),
    ("RIGHT_WRIST", "RIGHT_INDEX"),
    ("RIGHT_WRIST", "RIGHT_THUMB"),

    # Left Leg
    ("LEFT_HIP", "LEFT_KNEE"),
    ("LEFT_KNEE", "LEFT_ANKLE"),
    ("LEFT_ANKLE", "LEFT_HEEL"),
    ("LEFT_HEEL", "LEFT_FOOT_INDEX"),
    ("LEFT_ANKLE", "LEFT_FOOT_INDEX"),

    # Right Leg
    ("RIGHT_HIP", "RIGHT_KNEE"),
    ("RIGHT_KNEE", "RIGHT_ANKLE"),
    ("RIGHT_ANKLE", "RIGHT_HEEL"),
    ("RIGHT_HEEL", "RIGHT_FOOT_INDEX"),
    ("RIGHT_ANKLE", "RIGHT_FOOT_INDEX"),
]


class LandmarkHelper:
    """Helper utilities for processing and checking body landmarks."""

    @staticmethod
    def parse_mediapipe_landmarks(
        raw_landmarks: Any,
        image_width: int = 1,
        image_height: int = 1
    ) -> Dict[str, Dict[str, float]]:
        """
        Converts MediaPipe landmark objects into a clean dictionary.
        Each entry has: 'x' (norm 0-1), 'y' (norm 0-1), 'z', 'visibility',
        and pixel coordinates 'px', 'py'.
        """
        parsed: Dict[str, Dict[str, float]] = {}

        if not raw_landmarks:
            return parsed

        # Support both object list (LandmarkList) and iterable
        landmark_list = getattr(raw_landmarks, "landmark", raw_landmarks)

        for idx, lm in enumerate(landmark_list):
            if idx >= len(LANDMARK_NAMES):
                break
            name = LANDMARK_NAMES[idx]
            x = float(getattr(lm, "x", 0.0))
            y = float(getattr(lm, "y", 0.0))
            z = float(getattr(lm, "z", 0.0))
            vis = float(getattr(lm, "visibility", 1.0))
            presence = float(getattr(lm, "presence", 1.0))

            effective_vis = min(vis, presence)

            parsed[name] = {
                "x": x,
                "y": y,
                "z": z,
                "visibility": effective_vis,
                "px": int(x * image_width),
                "py": int(y * image_height),
            }

        return parsed

    @classmethod
    def check_body_visibility(
        cls,
        landmarks: Dict[str, Dict[str, float]],
        min_visibility: float = settings.LANDMARK_VISIBILITY_THRESHOLD,
    ) -> Tuple[bool, str, float]:
        """
        Verifies whether the full human body is adequately visible in the frame.
        
        Returns:
            Tuple of (is_visible: bool, warning_message: str, avg_confidence: float)
        """
        if not landmarks:
            return False, "No person detected in frame. Please stand in front of camera.", 0.0

        # Check core visibility landmarks
        key_landmarks = settings.KEY_VISIBILITY_LANDMARKS
        visibilities: List[float] = []
        missing_parts: List[str] = []

        for lm_name in key_landmarks:
            lm = landmarks.get(lm_name)
            if not lm or lm["visibility"] < min_visibility:
                visibilities.append(0.0)
                part_name = lm_name.replace("LEFT_", "").replace("RIGHT_", "").lower()
                if part_name not in missing_parts:
                    missing_parts.append(part_name)
            else:
                visibilities.append(lm["visibility"])

        avg_confidence = float(sum(visibilities) / len(visibilities)) if visibilities else 0.0

        # Assess specific missing body sections
        has_lower_body = all(
            landmarks.get(k, {}).get("visibility", 0.0) >= min_visibility
            for k in ["LEFT_KNEE", "RIGHT_KNEE", "LEFT_ANKLE", "RIGHT_ANKLE"]
        )
        has_upper_body = all(
            landmarks.get(k, {}).get("visibility", 0.0) >= min_visibility
            for k in ["LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_HIP", "RIGHT_HIP"]
        )

        if not has_upper_body and not has_lower_body:
            return False, "Body not clearly detected. Please step into frame with good lighting.", avg_confidence

        if not has_lower_body:
            return False, "Lower body not fully visible. Please step backward (~2-3 meters).", avg_confidence

        if not has_upper_body:
            return False, "Upper body truncated. Please tilt camera upward.", avg_confidence

        if avg_confidence < 0.60:
            return False, "Pose detection confidence is low. Please improve room lighting.", avg_confidence

        return True, "Full body visible and tracking reliably.", avg_confidence
