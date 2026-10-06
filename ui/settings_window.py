"""
Settings Screen for KI.AI.
Provides controls for camera input selection, detection confidence,
voice feedback configuration, and privacy statement.
"""

from typing import Any, Dict, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from config import settings
from database.database import Database


class SettingsWindow(QWidget):
    """System Settings and Privacy Control Screen."""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        # Title
        title_box = QVBoxLayout()
        title = QLabel("System Settings")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        subtitle = QLabel("Configure camera input, AI detection confidence, and privacy preferences.")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Camera & AI Settings Card
        cam_card = QFrame()
        cam_card.setProperty("class", "card")
        c_layout = QVBoxLayout(cam_card)
        c_layout.setContentsMargins(20, 18, 20, 18)
        c_layout.setSpacing(14)

        c_title = QLabel("Camera & Vision")
        c_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        c_layout.addWidget(c_title)

        # Camera Selection
        cam_row = QHBoxLayout()
        lbl_cam = QLabel("Camera Device:")
        lbl_cam.setStyleSheet("color: #E2E8F0; font-weight: 500;")
        cam_row.addWidget(lbl_cam)
        cam_row.addStretch()
        self.combo_cam = QComboBox()
        self.combo_cam.addItems(["Camera 0 (Integrated Webcam)", "Camera 1 (USB Camera)", "Camera 2"])
        self.combo_cam.setFixedWidth(240)
        cam_row.addWidget(self.combo_cam)
        c_layout.addLayout(cam_row)

        # Detection Confidence Slider
        conf_row = QHBoxLayout()
        lbl_conf = QLabel("Min Landmark Detection Confidence (0.60):")
        lbl_conf.setStyleSheet("color: #E2E8F0; font-weight: 500;")
        conf_row.addWidget(lbl_conf)
        conf_row.addStretch()
        slider = QSlider(Qt.Horizontal)
        slider.setRange(40, 90)
        slider.setValue(60)
        slider.setFixedWidth(200)
        conf_row.addWidget(slider)
        c_layout.addLayout(conf_row)

        # Mirror Feed Checkbox
        self.chk_mirror = QCheckBox("Mirror camera video horizontally")
        self.chk_mirror.setChecked(True)
        c_layout.addWidget(self.chk_mirror)

        layout.addWidget(cam_card)

        # Voice Coach Settings Card
        voice_card = QFrame()
        voice_card.setProperty("class", "card")
        v_layout = QVBoxLayout(voice_card)
        v_layout.setContentsMargins(20, 18, 20, 18)
        v_layout.setSpacing(10)

        v_title = QLabel("Audio & Voice Coach")
        v_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        v_layout.addWidget(v_title)

        self.chk_voice = QCheckBox("Enable real-time spoken coaching cues (Text-to-Speech)")
        self.chk_voice.setChecked(True)
        v_layout.addWidget(self.chk_voice)

        layout.addWidget(voice_card)

        # Privacy Guarantee Card
        privacy_card = QFrame()
        privacy_card.setStyleSheet("""
            QFrame {
                background-color: rgba(16, 185, 129, 0.08);
                border: 1px solid #10B981;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        p_layout = QVBoxLayout(privacy_card)
        p_title = QLabel("🔒 100% Local Privacy Guarantee")
        p_title.setStyleSheet("color: #10B981; font-weight: 700; font-size: 14px;")
        p_layout.addWidget(p_title)

        p_desc = QLabel(
            "All computer vision and MediaPipe pose estimation calculations execute entirely on your "
            "local CPU/GPU. Video frames are processed in-memory and are never uploaded, recorded, or "
            "transmitted to external cloud servers."
        )
        p_desc.setStyleSheet("color: #E2E8F0; font-size: 12.5px; line-height: 1.4;")
        p_desc.setWordWrap(True)
        p_layout.addWidget(p_desc)

        layout.addWidget(privacy_card)
        layout.addStretch()
