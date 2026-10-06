"""
Angle and Geometric Calculation Module for AI Yoga Assistant.
Provides mathematically rigorous vector angle calculations, limb alignments,
and normalized keypoint geometric features.
"""

import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


class AngleCalculator:
    """Calculates 2D and 3D geometric angles between anatomical landmarks."""

    @staticmethod
    def calculate_angle(
        point_a: Union[List[float], Tuple[float, ...], np.ndarray],
        point_b: Union[List[float], Tuple[float, ...], np.ndarray],
        point_c: Union[List[float], Tuple[float, ...], np.ndarray],
    ) -> float:
        """
        Calculates the interior angle at point_b formed by segments BA and BC in degrees.
        
        Args:
            point_a: Starting point coordinates [x, y] or [x, y, z].
            point_b: Vertex point coordinates [x, y] or [x, y, z] where angle is measured.
            point_c: Ending point coordinates [x, y] or [x, y, z].
            
        Returns:
            Angle in degrees in the range [0.0, 180.0]. Returns 0.0 if points coincide.
        """
        try:
            # Convert to numpy 2D arrays (using x, y coordinates primarily for planar stability)
            a = np.array([point_a[0], point_a[1]], dtype=np.float64)
            b = np.array([point_b[0], point_b[1]], dtype=np.float64)
            c = np.array([point_c[0], point_c[1]], dtype=np.float64)

            # Vectors BA and BC
            ba = a - b
            bc = c - b

            # Compute Euclidean norms
            norm_ba = np.linalg.norm(ba)
            norm_bc = np.linalg.norm(bc)

            # Check for zero-length vectors (coinciding points)
            if norm_ba < 1e-7 or norm_bc < 1e-7:
                return 0.0

            # Dot product
            dot_prod = np.dot(ba, bc)

            # Cosine with clamping to avoid precision domain errors
            cosine_angle = dot_prod / (norm_ba * norm_bc)
            cosine_angle = np.clip(cosine_angle, -1.0, 1.0)

            # Compute angle in radians and convert to degrees
            angle_rad = np.arccos(cosine_angle)
            angle_deg = np.degrees(angle_rad)

            return float(round(angle_deg, 2))
        except Exception:
            return 0.0

    @staticmethod
    def calculate_angle_with_vertical(
        point_top: Union[List[float], Tuple[float, ...], np.ndarray],
        point_bottom: Union[List[float], Tuple[float, ...], np.ndarray],
    ) -> float:
        """
        Calculates the angle (in degrees) of a segment (e.g. spine from hip to shoulder)
        relative to the true vertical axis.
        90° means completely upright relative to horizontal floor; 0° means horizontal.
        
        Args:
            point_top: Top landmark (e.g. shoulder/nose/mid_shoulders).
            point_bottom: Bottom landmark (e.g. hip/mid_hips).
            
        Returns:
            Angle in degrees [0.0, 180.0].
        """
        try:
            dx = point_top[0] - point_bottom[0]
            dy = point_bottom[1] - point_top[1]  # Note: Image Y is inverted (0 is top)

            if abs(dx) < 1e-7 and abs(dy) < 1e-7:
                return 90.0

            # Calculate angle with horizontal x-axis in degrees
            angle_rad = math.atan2(dy, dx)
            angle_deg = math.degrees(angle_rad)

            # Convert to inclination from horizontal ground (0 to 180)
            if angle_deg < 0:
                angle_deg += 180.0

            return float(round(angle_deg, 2))
        except Exception:
            return 90.0

    @staticmethod
    def calculate_angle_with_horizontal(
        point_a: Union[List[float], Tuple[float, ...], np.ndarray],
        point_b: Union[List[float], Tuple[float, ...], np.ndarray],
    ) -> float:
        """
        Calculates the tilt angle of a segment (e.g. left shoulder to right shoulder)
        relative to horizontal.
        0° means perfectly level horizontal line.
        """
        try:
            dx = point_b[0] - point_a[0]
            dy = point_b[1] - point_a[1]
            if abs(dx) < 1e-7:
                return 90.0
            angle_rad = math.atan2(abs(dy), abs(dx))
            return float(round(math.degrees(angle_rad), 2))
        except Exception:
            return 0.0

    @staticmethod
    def calculate_distance(
        point_a: Union[List[float], Tuple[float, ...], np.ndarray],
        point_b: Union[List[float], Tuple[float, ...], np.ndarray],
    ) -> float:
        """Calculates Euclidean distance between two points."""
        try:
            a = np.array([point_a[0], point_a[1]], dtype=np.float64)
            b = np.array([point_b[0], point_b[1]], dtype=np.float64)
            return float(np.linalg.norm(a - b))
        except Exception:
            return 0.0

    @classmethod
    def extract_all_angles(cls, landmarks: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """
        Extracts all standard yoga joint angles from a landmark dictionary.
        
        Expected landmarks keys (MediaPipe names):
            LEFT_SHOULDER, RIGHT_SHOULDER,
            LEFT_ELBOW, RIGHT_ELBOW,
            LEFT_WRIST, RIGHT_WRIST,
            LEFT_HIP, RIGHT_HIP,
            LEFT_KNEE, RIGHT_KNEE,
            LEFT_ANKLE, RIGHT_ANKLE, etc.
            
        Returns:
            Dictionary mapping joint names to calculated angles.
        """
        angles: Dict[str, float] = {}

        def get_coords(name: str) -> Optional[Tuple[float, float, float]]:
            lm = landmarks.get(name)
            if lm and "x" in lm and "y" in lm:
                return (lm["x"], lm["y"], lm.get("z", 0.0))
            return None

        # Keypoints
        l_shoulder = get_coords("LEFT_SHOULDER")
        r_shoulder = get_coords("RIGHT_SHOULDER")
        l_elbow = get_coords("LEFT_ELBOW")
        r_elbow = get_coords("RIGHT_ELBOW")
        l_wrist = get_coords("LEFT_WRIST")
        r_wrist = get_coords("RIGHT_WRIST")
        l_hip = get_coords("LEFT_HIP")
        r_hip = get_coords("RIGHT_HIP")
        l_knee = get_coords("LEFT_KNEE")
        r_knee = get_coords("RIGHT_KNEE")
        l_ankle = get_coords("LEFT_ANKLE")
        r_ankle = get_coords("RIGHT_ANKLE")

        # Left Arm / Elbow Angle (Shoulder - Elbow - Wrist)
        if l_shoulder and l_elbow and l_wrist:
            angles["left_elbow"] = cls.calculate_angle(l_shoulder, l_elbow, l_wrist)

        # Right Arm / Elbow Angle (Shoulder - Elbow - Wrist)
        if r_shoulder and r_elbow and r_wrist:
            angles["right_elbow"] = cls.calculate_angle(r_shoulder, r_elbow, r_wrist)

        # Left Shoulder / Armpit Angle (Hip - Shoulder - Elbow)
        if l_hip and l_shoulder and l_elbow:
            angles["left_shoulder"] = cls.calculate_angle(l_hip, l_shoulder, l_elbow)

        # Right Shoulder / Armpit Angle (Hip - Shoulder - Elbow)
        if r_hip and r_shoulder and r_elbow:
            angles["right_shoulder"] = cls.calculate_angle(r_hip, r_shoulder, r_elbow)

        # Left Knee Angle (Hip - Knee - Ankle)
        if l_hip and l_knee and l_ankle:
            angles["left_knee"] = cls.calculate_angle(l_hip, l_knee, l_ankle)

        # Right Knee Angle (Hip - Knee - Ankle)
        if r_hip and r_knee and r_ankle:
            angles["right_knee"] = cls.calculate_angle(r_hip, r_knee, r_ankle)

        # Left Hip Angle (Shoulder - Hip - Knee)
        if l_shoulder and l_hip and l_knee:
            angles["left_hip"] = cls.calculate_angle(l_shoulder, l_hip, l_knee)

        # Right Hip Angle (Shoulder - Hip - Knee)
        if r_shoulder and r_hip and r_knee:
            angles["right_hip"] = cls.calculate_angle(r_shoulder, r_hip, r_knee)

        # Torso Verticality (Mid Shoulder - Mid Hip relative to vertical)
        if l_shoulder and r_shoulder and l_hip and r_hip:
            mid_shoulder = (
                (l_shoulder[0] + r_shoulder[0]) / 2.0,
                (l_shoulder[1] + r_shoulder[1]) / 2.0,
            )
            mid_hip = (
                (l_hip[0] + r_hip[0]) / 2.0,
                (l_hip[1] + r_hip[1]) / 2.0,
            )
            angles["torso_vertical"] = cls.calculate_angle_with_vertical(mid_shoulder, mid_hip)

        # Shoulder Level Tilt (Angle of shoulder line relative to horizontal)
        if l_shoulder and r_shoulder:
            angles["shoulder_tilt"] = cls.calculate_angle_with_horizontal(l_shoulder, r_shoulder)

        # Hip Level Tilt (Angle of hip line relative to horizontal)
        if l_hip and r_hip:
            angles["hip_tilt"] = cls.calculate_angle_with_horizontal(l_hip, r_hip)

        return angles
