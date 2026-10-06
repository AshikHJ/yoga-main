"""
Reference Pose & Anatomical Skeleton Rendering Helper for KI.AI.
Generates ideal 2D reference skeletons, posture illustrations, and SVG figure badges
for Reference Assist (Photo, Skeleton, Overlay modes) and Yoga Library Cards.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer

from config import settings
from vision.landmarks import SKELETON_CONNECTIONS


class ReferenceHelper:
    """Generates ideal reference posture skeletons, SVG icons, and overlays."""

    # Reference canonical landmark templates for standard poses (normalized 0.0-1.0)
    CANONICAL_POSES: Dict[str, Dict[str, Tuple[float, float]]] = {
        "tadasana": {
            "NOSE": (0.50, 0.12),
            "LEFT_SHOULDER": (0.44, 0.22), "RIGHT_SHOULDER": (0.56, 0.22),
            "LEFT_ELBOW": (0.41, 0.38), "RIGHT_ELBOW": (0.59, 0.38),
            "LEFT_WRIST": (0.40, 0.52), "RIGHT_WRIST": (0.60, 0.52),
            "LEFT_HIP": (0.46, 0.52), "RIGHT_HIP": (0.54, 0.52),
            "LEFT_KNEE": (0.46, 0.74), "RIGHT_KNEE": (0.54, 0.74),
            "LEFT_ANKLE": (0.46, 0.92), "RIGHT_ANKLE": (0.54, 0.92),
        },
        "warrior": {
            "NOSE": (0.48, 0.18),
            "LEFT_SHOULDER": (0.42, 0.28), "RIGHT_SHOULDER": (0.54, 0.28),
            "LEFT_ELBOW": (0.24, 0.28), "RIGHT_ELBOW": (0.72, 0.28),
            "LEFT_WRIST": (0.12, 0.28), "RIGHT_WRIST": (0.86, 0.28),
            "LEFT_HIP": (0.44, 0.52), "RIGHT_HIP": (0.52, 0.52),
            "LEFT_KNEE": (0.30, 0.68), "RIGHT_KNEE": (0.68, 0.68),
            "LEFT_ANKLE": (0.30, 0.90), "RIGHT_ANKLE": (0.80, 0.88),
        },
        "tree": {
            "NOSE": (0.50, 0.14),
            "LEFT_SHOULDER": (0.44, 0.24), "RIGHT_SHOULDER": (0.56, 0.24),
            "LEFT_ELBOW": (0.42, 0.15), "RIGHT_ELBOW": (0.58, 0.15),
            "LEFT_WRIST": (0.50, 0.08), "RIGHT_WRIST": (0.50, 0.08),
            "LEFT_HIP": (0.46, 0.52), "RIGHT_HIP": (0.54, 0.52),
            "LEFT_KNEE": (0.48, 0.73), "RIGHT_KNEE": (0.70, 0.62),
            "LEFT_ANKLE": (0.48, 0.92), "RIGHT_ANKLE": (0.50, 0.72),
        },
        "vrikshasana": {
            "NOSE": (0.50, 0.14),
            "LEFT_SHOULDER": (0.44, 0.24), "RIGHT_SHOULDER": (0.56, 0.24),
            "LEFT_ELBOW": (0.42, 0.15), "RIGHT_ELBOW": (0.58, 0.15),
            "LEFT_WRIST": (0.50, 0.08), "RIGHT_WRIST": (0.50, 0.08),
            "LEFT_HIP": (0.46, 0.52), "RIGHT_HIP": (0.54, 0.52),
            "LEFT_KNEE": (0.48, 0.73), "RIGHT_KNEE": (0.70, 0.62),
            "LEFT_ANKLE": (0.48, 0.92), "RIGHT_ANKLE": (0.50, 0.72),
        },
        "triangle": {
            "NOSE": (0.38, 0.32),
            "LEFT_SHOULDER": (0.34, 0.40), "RIGHT_SHOULDER": (0.44, 0.36),
            "LEFT_ELBOW": (0.28, 0.56), "RIGHT_ELBOW": (0.50, 0.20),
            "LEFT_WRIST": (0.24, 0.72), "RIGHT_WRIST": (0.56, 0.08),
            "LEFT_HIP": (0.42, 0.58), "RIGHT_HIP": (0.52, 0.54),
            "LEFT_KNEE": (0.30, 0.75), "RIGHT_KNEE": (0.64, 0.74),
            "LEFT_ANKLE": (0.25, 0.92), "RIGHT_ANKLE": (0.75, 0.90),
        },
        "chair": {
            "NOSE": (0.46, 0.18),
            "LEFT_SHOULDER": (0.44, 0.28), "RIGHT_SHOULDER": (0.52, 0.28),
            "LEFT_ELBOW": (0.38, 0.16), "RIGHT_ELBOW": (0.46, 0.16),
            "LEFT_WRIST": (0.32, 0.08), "RIGHT_WRIST": (0.40, 0.08),
            "LEFT_HIP": (0.56, 0.56), "RIGHT_HIP": (0.60, 0.56),
            "LEFT_KNEE": (0.46, 0.72), "RIGHT_KNEE": (0.50, 0.72),
            "LEFT_ANKLE": (0.46, 0.92), "RIGHT_ANKLE": (0.50, 0.92),
        },
        "cobra": {
            "NOSE": (0.25, 0.26),
            "LEFT_SHOULDER": (0.32, 0.38), "RIGHT_SHOULDER": (0.36, 0.38),
            "LEFT_ELBOW": (0.32, 0.56), "RIGHT_ELBOW": (0.38, 0.56),
            "LEFT_WRIST": (0.32, 0.70), "RIGHT_WRIST": (0.38, 0.70),
            "LEFT_HIP": (0.52, 0.68), "RIGHT_HIP": (0.56, 0.68),
            "LEFT_KNEE": (0.70, 0.72), "RIGHT_KNEE": (0.74, 0.72),
            "LEFT_ANKLE": (0.86, 0.75), "RIGHT_ANKLE": (0.90, 0.75),
        },
        "bhujangasana": {
            "NOSE": (0.25, 0.26),
            "LEFT_SHOULDER": (0.32, 0.38), "RIGHT_SHOULDER": (0.36, 0.38),
            "LEFT_ELBOW": (0.32, 0.56), "RIGHT_ELBOW": (0.38, 0.56),
            "LEFT_WRIST": (0.32, 0.70), "RIGHT_WRIST": (0.38, 0.70),
            "LEFT_HIP": (0.52, 0.68), "RIGHT_HIP": (0.56, 0.68),
            "LEFT_KNEE": (0.70, 0.72), "RIGHT_KNEE": (0.74, 0.72),
            "LEFT_ANKLE": (0.86, 0.75), "RIGHT_ANKLE": (0.90, 0.75),
        },
        "child": {
            "NOSE": (0.30, 0.58),
            "LEFT_SHOULDER": (0.38, 0.54), "RIGHT_SHOULDER": (0.42, 0.54),
            "LEFT_ELBOW": (0.26, 0.64), "RIGHT_ELBOW": (0.28, 0.64),
            "LEFT_WRIST": (0.16, 0.70), "RIGHT_WRIST": (0.18, 0.70),
            "LEFT_HIP": (0.64, 0.58), "RIGHT_HIP": (0.68, 0.58),
            "LEFT_KNEE": (0.52, 0.72), "RIGHT_KNEE": (0.54, 0.72),
            "LEFT_ANKLE": (0.72, 0.74), "RIGHT_ANKLE": (0.74, 0.74),
        },
        "downward dog": {
            "NOSE": (0.40, 0.58),
            "LEFT_SHOULDER": (0.36, 0.50), "RIGHT_SHOULDER": (0.40, 0.50),
            "LEFT_ELBOW": (0.28, 0.64), "RIGHT_ELBOW": (0.30, 0.64),
            "LEFT_WRIST": (0.20, 0.78), "RIGHT_WRIST": (0.22, 0.78),
            "LEFT_HIP": (0.52, 0.28), "RIGHT_HIP": (0.56, 0.28),
            "LEFT_KNEE": (0.64, 0.52), "RIGHT_KNEE": (0.66, 0.52),
            "LEFT_ANKLE": (0.76, 0.78), "RIGHT_ANKLE": (0.78, 0.78),
        },
        "dancer": {
            "NOSE": (0.48, 0.24),
            "LEFT_SHOULDER": (0.44, 0.32), "RIGHT_SHOULDER": (0.52, 0.32),
            "LEFT_ELBOW": (0.30, 0.30), "RIGHT_ELBOW": (0.60, 0.22),
            "LEFT_WRIST": (0.18, 0.28), "RIGHT_WRIST": (0.66, 0.18),
            "LEFT_HIP": (0.46, 0.52), "RIGHT_HIP": (0.50, 0.52),
            "LEFT_KNEE": (0.46, 0.72), "RIGHT_KNEE": (0.66, 0.40),
            "LEFT_ANKLE": (0.46, 0.92), "RIGHT_ANKLE": (0.68, 0.20),
        },
        "natarajasana": {
            "NOSE": (0.48, 0.24),
            "LEFT_SHOULDER": (0.44, 0.32), "RIGHT_SHOULDER": (0.52, 0.32),
            "LEFT_ELBOW": (0.30, 0.30), "RIGHT_ELBOW": (0.60, 0.22),
            "LEFT_WRIST": (0.18, 0.28), "RIGHT_WRIST": (0.66, 0.18),
            "LEFT_HIP": (0.46, 0.52), "RIGHT_HIP": (0.50, 0.52),
            "LEFT_KNEE": (0.46, 0.72), "RIGHT_KNEE": (0.66, 0.40),
            "LEFT_ANKLE": (0.46, 0.92), "RIGHT_ANKLE": (0.68, 0.20),
        },
        "bridge": {
            "NOSE": (0.24, 0.68),
            "LEFT_SHOULDER": (0.30, 0.68), "RIGHT_SHOULDER": (0.34, 0.68),
            "LEFT_ELBOW": (0.42, 0.70), "RIGHT_ELBOW": (0.44, 0.70),
            "LEFT_WRIST": (0.54, 0.72), "RIGHT_WRIST": (0.56, 0.72),
            "LEFT_HIP": (0.56, 0.42), "RIGHT_HIP": (0.60, 0.42),
            "LEFT_KNEE": (0.76, 0.52), "RIGHT_KNEE": (0.78, 0.52),
            "LEFT_ANKLE": (0.78, 0.74), "RIGHT_ANKLE": (0.80, 0.74),
        },
        "bow": {
            "NOSE": (0.28, 0.34),
            "LEFT_SHOULDER": (0.34, 0.42), "RIGHT_SHOULDER": (0.38, 0.42),
            "LEFT_ELBOW": (0.50, 0.36), "RIGHT_ELBOW": (0.52, 0.36),
            "LEFT_WRIST": (0.68, 0.34), "RIGHT_WRIST": (0.70, 0.34),
            "LEFT_HIP": (0.50, 0.70), "RIGHT_HIP": (0.54, 0.70),
            "LEFT_KNEE": (0.66, 0.56), "RIGHT_KNEE": (0.68, 0.56),
            "LEFT_ANKLE": (0.72, 0.36), "RIGHT_ANKLE": (0.74, 0.36),
        },
        "easy pose": {
            "NOSE": (0.50, 0.22),
            "LEFT_SHOULDER": (0.42, 0.34), "RIGHT_SHOULDER": (0.58, 0.34),
            "LEFT_ELBOW": (0.34, 0.54), "RIGHT_ELBOW": (0.66, 0.54),
            "LEFT_WRIST": (0.30, 0.72), "RIGHT_WRIST": (0.70, 0.72),
            "LEFT_HIP": (0.44, 0.62), "RIGHT_HIP": (0.56, 0.62),
            "LEFT_KNEE": (0.28, 0.76), "RIGHT_KNEE": (0.72, 0.76),
            "LEFT_ANKLE": (0.48, 0.78), "RIGHT_ANKLE": (0.52, 0.78),
        },
        "sukhasana": {
            "NOSE": (0.50, 0.22),
            "LEFT_SHOULDER": (0.42, 0.34), "RIGHT_SHOULDER": (0.58, 0.34),
            "LEFT_ELBOW": (0.34, 0.54), "RIGHT_ELBOW": (0.66, 0.54),
            "LEFT_WRIST": (0.30, 0.72), "RIGHT_WRIST": (0.70, 0.72),
            "LEFT_HIP": (0.44, 0.62), "RIGHT_HIP": (0.56, 0.62),
            "LEFT_KNEE": (0.28, 0.76), "RIGHT_KNEE": (0.72, 0.76),
            "LEFT_ANKLE": (0.48, 0.78), "RIGHT_ANKLE": (0.52, 0.78),
        }
    }

    @classmethod
    def get_canonical_template(cls, pose_name: str) -> Dict[str, Tuple[float, float]]:
        """Returns canonical template or default upright template."""
        clean_name = pose_name.lower()
        for k, v in cls.CANONICAL_POSES.items():
            if k in clean_name:
                return v
        return cls.CANONICAL_POSES["tadasana"]

    @classmethod
    def get_pose_figure_pixmap(cls, pose: Dict[str, Any], size: Tuple[int, int] = (44, 44)) -> QPixmap:
        """
        Loads the dedicated SVG pose figure or renders canonical silhouette fallback.
        Never returns a generic meditation emoji for mismatched poses.
        """
        fig_path = pose.get("figure_path") or pose.get("pose_figure")
        w, h = size

        if fig_path:
            p = Path(fig_path)
            if not p.is_absolute():
                p = settings.BASE_DIR / fig_path

            if p.exists() and p.suffix.lower() == ".svg":
                renderer = QSvgRenderer(str(p))
                pixmap = QPixmap(w, h)
                pixmap.fill(Qt.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.end()
                return pixmap

        # Fallback: Render clean dynamic canonical line-art skeleton
        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw dark translucent container background
        painter.setBrush(QColor(15, 23, 42, 220))
        painter.setPen(QPen(QColor(16, 185, 129, 180), 1))
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 6, 6)

        # Draw mini pose lines
        template = cls.get_canonical_template(pose.get("name", ""))
        painter.setPen(QPen(QColor(255, 255, 255, 220), 2))

        coords = {k: (int(v[0] * w), int(v[1] * h)) for k, v in template.items()}
        for p1_name, p2_name in SKELETON_CONNECTIONS:
            if p1_name in coords and p2_name in coords:
                x1, y1 = coords[p1_name]
                x2, y2 = coords[p2_name]
                painter.drawLine(x1, y1, x2, y2)

        painter.end()
        return pixmap

    @classmethod
    def render_reference_skeleton_image(
        cls,
        pose_name: str,
        rules: Optional[List[Dict[str, Any]]] = None,
        width: int = 400,
        height: int = 450,
    ) -> np.ndarray:
        """
        Draws canonical 2D biomechanical skeleton on dark background
        with green joint angles and reference labels.
        """
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:] = (15, 23, 42)  # Obsidian dark background #0F172A

        template = cls.get_canonical_template(pose_name)
        coords = {}
        for k, (nx, ny) in template.items():
            cx = int(nx * width)
            cy = int(ny * (height - 40) + 20)
            coords[k] = (cx, cy)

        # Draw skeleton bone lines
        for p1_name, p2_name in SKELETON_CONNECTIONS:
            if p1_name in coords and p2_name in coords:
                pt1 = coords[p1_name]
                pt2 = coords[p2_name]
                cv2.line(img, pt1, pt2, (180, 240, 200), 4, cv2.LINE_AA)
                cv2.line(img, pt1, pt2, (16, 185, 129), 2, cv2.LINE_AA)

        # Draw joint nodes
        for k, (cx, cy) in coords.items():
            cv2.circle(img, (cx, cy), 6, (16, 185, 129), -1, cv2.LINE_AA)
            cv2.circle(img, (cx, cy), 2, (255, 255, 255), -1, cv2.LINE_AA)

        # Draw target angle badges if rules are provided
        if rules:
            for rule in rules:
                j_name = rule.get("joint_name", "")
                target_deg = int(rule.get("target_angle", 0))

                # Map joint name to landmark coordinate
                target_pt = None
                if "knee" in j_name:
                    target_pt = coords.get("LEFT_KNEE" if "left" in j_name else "RIGHT_KNEE")
                elif "elbow" in j_name:
                    target_pt = coords.get("LEFT_ELBOW" if "left" in j_name else "RIGHT_ELBOW")
                elif "shoulder" in j_name:
                    target_pt = coords.get("LEFT_SHOULDER" if "left" in j_name else "RIGHT_SHOULDER")
                elif "hip" in j_name:
                    target_pt = coords.get("LEFT_HIP" if "left" in j_name else "RIGHT_HIP")

                if target_pt:
                    tx, ty = target_pt
                    badge_text = f"{target_deg} deg"
                    cv2.putText(img, badge_text, (tx + 10, ty + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (16, 185, 129), 1, cv2.LINE_AA)

        return img

    @classmethod
    def render_reference_photo_card(
        cls,
        pose_name: str,
        category: str,
        difficulty: str,
        width: int = 400,
        height: int = 450,
    ) -> np.ndarray:
        """
        Creates an illustrative high-contrast posture card with gradient
        and anatomical skeleton representation.
        """
        img = cls.render_reference_skeleton_image(pose_name, width=width, height=height)

        # Draw overlay header badge
        cv2.rectangle(img, (0, 0), (width, 45), (6, 78, 59), -1)
        cv2.putText(img, f"KI.AI REFERENCE: {pose_name.upper()}", (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

        # Footer badge
        cv2.rectangle(img, (0, height - 35), (width, height), (11, 17, 32), -1)
        cv2.putText(img, f"Category: {category}  |  Level: {difficulty}", (14, height - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148, 163, 184), 1, cv2.LINE_AA)

        return img
