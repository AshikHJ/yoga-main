"""
Reference Assist UI Component for KI.AI.
Provides three interactive modes for visual posture guidance:
1. PHOTO — High-res reference posture visual card
2. SKELETON — Ideal 2D anatomical reference skeleton with target joint angles
3. OVERLAY — Reference skeleton overlay guide alongside user camera feed
"""

from typing import Any, Dict, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import settings
from vision.reference_helper import ReferenceHelper


class ReferenceAssistWidget(QFrame):
    """Interactive Reference Assist component supporting Photo, Skeleton, and Overlay modes."""

    mode_changed = Signal(str)  # Emits "photo", "skeleton", or "overlay"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pose: Optional[Dict[str, Any]] = None
        self.current_mode = "photo"  # "photo" | "skeleton" | "overlay"

        self.setProperty("class", "card")
        self.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 10px;
            }
        """)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Header Row
        header = QHBoxLayout()
        title = QLabel("REFERENCE ASSIST")
        title.setStyleSheet("color: #10B981; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        header.addWidget(title)
        header.addStretch()

        # Mode Buttons (PHOTO | SKELETON | OVERLAY)
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.btn_photo = QPushButton("PHOTO")
        self.btn_photo.setCheckable(True)
        self.btn_photo.setChecked(True)
        self.btn_photo.setStyleSheet(self._get_tab_btn_style())
        self.btn_group.addButton(self.btn_photo)
        header.addWidget(self.btn_photo)

        self.btn_skeleton = QPushButton("SKELETON")
        self.btn_skeleton.setCheckable(True)
        self.btn_skeleton.setStyleSheet(self._get_tab_btn_style())
        self.btn_group.addButton(self.btn_skeleton)
        header.addWidget(self.btn_skeleton)

        self.btn_overlay = QPushButton("OVERLAY")
        self.btn_overlay.setCheckable(True)
        self.btn_overlay.setStyleSheet(self._get_tab_btn_style())
        self.btn_group.addButton(self.btn_overlay)
        header.addWidget(self.btn_overlay)

        layout.addLayout(header)

        # Content Image / Skeleton Display
        self.lbl_display = QLabel()
        self.lbl_display.setAlignment(Qt.AlignCenter)
        self.lbl_display.setMinimumHeight(230)
        self.lbl_display.setStyleSheet("background-color: #0B1120; border-radius: 8px; border: 1px solid #1E293B;")
        layout.addWidget(self.lbl_display)

        # Description / Mode subtitle
        self.lbl_caption = QLabel("Reference photo guide for starting posture.")
        self.lbl_caption.setStyleSheet("color: #94A3B8; font-size: 11px; font-style: italic;")
        self.lbl_caption.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_caption)

        # Connect Signals
        self.btn_photo.clicked.connect(lambda: self._set_mode("photo"))
        self.btn_skeleton.clicked.connect(lambda: self._set_mode("skeleton"))
        self.btn_overlay.clicked.connect(lambda: self._set_mode("overlay"))

    def _get_tab_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #FFFFFF;
                border-color: #10B981;
            }
            QPushButton:checked {
                background-color: #10B981;
                color: #FFFFFF;
                border-color: #10B981;
            }
        """

    def set_pose(self, pose: Dict[str, Any]) -> None:
        """Sets the active pose and refreshes the current view."""
        self.current_pose = pose
        self._refresh_view()

    def _set_mode(self, mode: str) -> None:
        self.current_mode = mode
        self.mode_changed.emit(mode)
        self._refresh_view()

    def _refresh_view(self) -> None:
        if not self.current_pose:
            self.lbl_display.setText("Select a pose to view reference assist.")
            return

        pose_name = self.current_pose.get("name", "Pose")
        rules = self.current_pose.get("rules", [])

        if self.current_mode == "photo":
            pixmap = ReferenceHelper.render_reference_photo_card(self.current_pose, width=360, height=240)
            self.lbl_display.setPixmap(pixmap.scaled(self.lbl_display.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.lbl_caption.setText(f"Target Form: {pose_name}")

        elif self.current_mode == "skeleton":
            pixmap = ReferenceHelper.render_reference_skeleton_image(pose_name, rules=rules, width=360, height=240)
            self.lbl_display.setPixmap(pixmap.scaled(self.lbl_display.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.lbl_caption.setText("Ideal joint angle skeleton (Green = target degrees)")

        elif self.current_mode == "overlay":
            pixmap = ReferenceHelper.render_reference_skeleton_image(pose_name, rules=rules, width=360, height=240)
            self.lbl_display.setPixmap(pixmap.scaled(self.lbl_display.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.lbl_caption.setText("Overlay Guide: Compare your body against the green skeleton.")
