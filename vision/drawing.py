"""
Skeleton and Posture Visualization Overlay Module.
Renders high-contrast, color-coded anatomical skeleton connections, glowing joint nodes,
angle badges, and top-bar status indicators onto OpenCV video frames.
"""

from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from PySide6.QtGui import QImage, QPixmap

from config import settings
from vision.landmarks import SKELETON_CONNECTIONS


class PoseDrawer:
    """Renders visual skeleton, status badges, and angle tags onto video frames."""

    # BGR Color Constants
    COLOR_CORRECT_BGR = (129, 185, 16)      # Emerald Green #10B981
    COLOR_WARNING_BGR = (11, 158, 245)      # Amber / Yellow #F59E0B
    COLOR_INCORRECT_BGR = (68, 68, 239)     # Rose / Red #EF4444
    COLOR_GRAY_BGR = (184, 163, 148)        # Gray #94A3B8
    COLOR_DEFAULT_BGR = (241, 102, 99)      # Indigo #6366F1
    COLOR_WHITE_BGR = (250, 250, 250)
    COLOR_DARK_BG_BGR = (26, 23, 15)        # Dark Slate #0F172A

    # Joint to connection mapping for color coding
    JOINT_CONNECTION_MAP = {
        "left_knee": [("LEFT_HIP", "LEFT_KNEE"), ("LEFT_KNEE", "LEFT_ANKLE")],
        "right_knee": [("RIGHT_HIP", "RIGHT_KNEE"), ("RIGHT_KNEE", "RIGHT_ANKLE")],
        "left_elbow": [("LEFT_SHOULDER", "LEFT_ELBOW"), ("LEFT_ELBOW", "LEFT_WRIST")],
        "right_elbow": [("RIGHT_SHOULDER", "RIGHT_ELBOW"), ("RIGHT_ELBOW", "RIGHT_WRIST")],
        "left_shoulder": [("LEFT_SHOULDER", "LEFT_ELBOW"), ("LEFT_SHOULDER", "LEFT_HIP")],
        "right_shoulder": [("RIGHT_SHOULDER", "RIGHT_ELBOW"), ("RIGHT_SHOULDER", "RIGHT_HIP")],
        "left_hip": [("LEFT_SHOULDER", "LEFT_HIP"), ("LEFT_HIP", "LEFT_KNEE")],
        "right_hip": [("RIGHT_SHOULDER", "RIGHT_HIP"), ("RIGHT_HIP", "RIGHT_KNEE")],
        "torso_vertical": [("LEFT_SHOULDER", "LEFT_HIP"), ("RIGHT_SHOULDER", "RIGHT_HIP"), ("LEFT_SHOULDER", "RIGHT_SHOULDER"), ("LEFT_HIP", "RIGHT_HIP")],
    }

    # Landmark to joint name mapping
    LANDMARK_TO_JOINT_MAP = {
        "LEFT_KNEE": "left_knee",
        "RIGHT_KNEE": "right_knee",
        "LEFT_ELBOW": "left_elbow",
        "RIGHT_ELBOW": "right_elbow",
        "LEFT_SHOULDER": "left_shoulder",
        "RIGHT_SHOULDER": "right_shoulder",
        "LEFT_HIP": "left_hip",
        "RIGHT_HIP": "right_hip",
        "LEFT_ANKLE": "left_knee",
        "RIGHT_ANKLE": "right_knee",
        "LEFT_WRIST": "left_elbow",
        "RIGHT_WRIST": "right_elbow",
    }

    @classmethod
    def draw_skeleton(
        cls,
        frame: np.ndarray,
        landmarks: Dict[str, Dict[str, float]],
        posture_result: Optional[Dict[str, Any]] = None,
        show_angles: bool = True,
    ) -> np.ndarray:
        """
        Draws the complete posture skeleton overlaid on the video frame with
        real-time Green (Correct), Yellow (Adjust Slightly), Red (Needs Correction),
        and Gray (Not Detected) highlighting.
        """
        if not landmarks:
            return frame

        annotated = frame.copy()
        h, w, _ = annotated.shape

        # Build color mapping for bones and nodes
        connection_colors: Dict[Tuple[str, str], Tuple[int, int, int]] = {}
        landmark_colors: Dict[str, Tuple[int, int, int]] = {}
        joint_status_map: Dict[str, Dict[str, Any]] = {}

        if posture_result and posture_result.get("joint_results"):
            for j_res in posture_result["joint_results"]:
                j_name = j_res.get("joint_name", "")
                status_code = j_res.get("status_code", "CORRECT")
                joint_status_map[j_name] = j_res

                if status_code == "CORRECT":
                    color = cls.COLOR_CORRECT_BGR
                elif status_code == "WARNING":
                    color = cls.COLOR_WARNING_BGR
                elif status_code == "NOT_DETECTED":
                    color = cls.COLOR_GRAY_BGR
                else:
                    color = cls.COLOR_INCORRECT_BGR

                mapped_conns = cls.JOINT_CONNECTION_MAP.get(j_name, [])
                for conn in mapped_conns:
                    connection_colors[conn] = color
                    connection_colors[(conn[1], conn[0])] = color

        # Map node colors
        for lm_name in landmarks.keys():
            j_mapped = cls.LANDMARK_TO_JOINT_MAP.get(lm_name)
            if j_mapped and j_mapped in joint_status_map:
                st = joint_status_map[j_mapped].get("status_code", "CORRECT")
                if st == "CORRECT":
                    landmark_colors[lm_name] = cls.COLOR_CORRECT_BGR
                elif st == "WARNING":
                    landmark_colors[lm_name] = cls.COLOR_WARNING_BGR
                elif st == "NOT_DETECTED":
                    landmark_colors[lm_name] = cls.COLOR_GRAY_BGR
                else:
                    landmark_colors[lm_name] = cls.COLOR_INCORRECT_BGR
            else:
                landmark_colors[lm_name] = cls.COLOR_DEFAULT_BGR

        # 1. Draw Skeleton Bones / Connections
        for p1_name, p2_name in SKELETON_CONNECTIONS:
            lm1 = landmarks.get(p1_name)
            lm2 = landmarks.get(p2_name)

            if not lm1 or not lm2:
                continue

            if lm1["visibility"] < 0.35 or lm2["visibility"] < 0.35:
                continue

            pt1 = (lm1["px"], lm1["py"])
            pt2 = (lm2["px"], lm2["py"])

            # Determine bone color
            color = connection_colors.get((p1_name, p2_name), cls.COLOR_DEFAULT_BGR)

            # Draw smooth glowing outer line + core anti-aliased line
            cv2.line(annotated, pt1, pt2, (15, 23, 42), 6, cv2.LINE_AA)
            cv2.line(annotated, pt1, pt2, color, 3, cv2.LINE_AA)

        # 2. Draw Landmark Joints (Nodes)
        for name, lm in landmarks.items():
            if lm["visibility"] < 0.35:
                continue

            center = (lm["px"], lm["py"])
            node_color = landmark_colors.get(name, cls.COLOR_DEFAULT_BGR)

            # Outer ring with status color
            cv2.circle(annotated, center, 7, node_color, -1, cv2.LINE_AA)
            # Inner dark core
            cv2.circle(annotated, center, 4, cls.COLOR_DARK_BG_BGR, -1, cv2.LINE_AA)
            # Center bright dot
            cv2.circle(annotated, center, 2, cls.COLOR_WHITE_BGR, -1, cv2.LINE_AA)

        # 3. Draw Angle Labels if requested
        if show_angles and posture_result and posture_result.get("joint_results"):
            for j_res in posture_result["joint_results"]:
                j_name = j_res.get("joint_name", "")
                actual_deg = j_res.get("actual_angle")
                status_code = j_res.get("status_code", "CORRECT")

                if actual_deg is None or status_code == "NOT_DETECTED":
                    continue

                # Map joint name to vertex landmark
                vertex_lm_name = None
                if "knee" in j_name:
                    vertex_lm_name = "LEFT_KNEE" if "left" in j_name else "RIGHT_KNEE"
                elif "elbow" in j_name:
                    vertex_lm_name = "LEFT_ELBOW" if "left" in j_name else "RIGHT_ELBOW"
                elif "shoulder" in j_name:
                    vertex_lm_name = "LEFT_SHOULDER" if "left" in j_name else "RIGHT_SHOULDER"
                elif "hip" in j_name:
                    vertex_lm_name = "LEFT_HIP" if "left" in j_name else "RIGHT_HIP"

                if vertex_lm_name and vertex_lm_name in landmarks:
                    v_lm = landmarks[vertex_lm_name]
                    if v_lm["visibility"] >= 0.4:
                        vx, vy = v_lm["px"], v_lm["py"]
                        label = f"{int(round(actual_deg))}°"

                        badge_border = (
                            cls.COLOR_CORRECT_BGR if status_code == "CORRECT"
                            else cls.COLOR_WARNING_BGR if status_code == "WARNING"
                            else cls.COLOR_INCORRECT_BGR
                        )

                        # Draw small badge
                        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
                        bx, by = vx + 10, vy - 6
                        cv2.rectangle(annotated, (bx - 3, by - th - 3), (bx + tw + 4, by + 3), (15, 23, 42), -1)
                        cv2.rectangle(annotated, (bx - 3, by - th - 3), (bx + tw + 4, by + 3), badge_border, 1, cv2.LINE_AA)
                        cv2.putText(
                            annotated,
                            label,
                            (bx, by),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.42,
                            (255, 255, 255),
                            1,
                            cv2.LINE_AA,
                        )

        return annotated

    @classmethod
    def draw_ghost_reference_skeleton(
        cls,
        frame: np.ndarray,
        pose_name: str,
        alpha: float = 0.40,
        scale: float = 0.85,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
    ) -> np.ndarray:
        """
        Overlays a semi-transparent ethereal cyan canonical reference skeleton
        over the camera view so the user can visually align their body.
        """
        from vision.reference_helper import ReferenceHelper

        template = ReferenceHelper.get_canonical_template(pose_name)
        if not template:
            return frame

        overlay = frame.copy()
        h, w, _ = frame.shape

        cx_base = w * 0.5 + offset_x * w
        cy_base = h * 0.5 + offset_y * h
        box_w = w * scale
        box_h = h * scale

        coords = {}
        for k, (nx, ny) in template.items():
            px = int(cx_base + (nx - 0.5) * box_w)
            py = int(cy_base + (ny - 0.5) * box_h)
            coords[k] = (px, py)

        # Ghost color: Distinctive cyan / sky blue (BGR)
        GHOST_COLOR = (248, 189, 56)
        GHOST_NODE = (255, 255, 255)

        for p1, p2 in SKELETON_CONNECTIONS:
            if p1 in coords and p2 in coords:
                cv2.line(overlay, coords[p1], coords[p2], GHOST_COLOR, 2, cv2.LINE_AA)

        for k, pt in coords.items():
            cv2.circle(overlay, pt, 5, GHOST_COLOR, -1, cv2.LINE_AA)
            cv2.circle(overlay, pt, 2, GHOST_NODE, -1, cv2.LINE_AA)

        return cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0)

    @staticmethod
    def frame_to_pixmap(frame: np.ndarray) -> QPixmap:
        """Converts an OpenCV BGR frame array to a PySide6 QPixmap."""
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(q_img)
