"""
Custom Yoga Pose Creation and Live Reference Capture Wizard.
Allows users to define custom poses, capture multi-frame landmark references in real time,
generate stable joint angle templates, and save them for instant practice.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from analysis.angle_calculator import AngleCalculator
from analysis.feedback import FeedbackEngine
from config import settings
from database.database import Database
from vision.camera import CameraWorker
from vision.drawing import PoseDrawer

logger = logging.getLogger(__name__)


class AddPoseWindow(QWidget):
    """Wizard for registering custom yoga poses with multi-frame webcam reference capture."""

    pose_created = Signal(dict)
    pose_saved = pose_created
    cancel_requested = Signal()

    def __init__(self, db: Database, user: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user = user

        # Multi-frame capture buffers
        self.camera_worker: Optional[CameraWorker] = None
        self.captured_frame_angles: List[Dict[str, float]] = []
        self.captured_snapshot: Optional[np.ndarray] = None
        self.is_capturing_frames = False
        self.target_frame_count = settings.CUSTOM_POSE_CAPTURE_FRAME_COUNT

        # Calculated template data
        self.calculated_rules: List[Dict[str, Any]] = []

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(20)

        # Header Title
        title_box = QVBoxLayout()
        title_lbl = QLabel("➕ Create Custom Yoga Pose")
        title_lbl.setProperty("class", "heading1")
        title_lbl.setStyleSheet("font-size: 26px; font-weight: bold; color: #F8FAFC;")
        title_box.addWidget(title_lbl)

        sub_lbl = QLabel("Define a custom yoga posture, capture your reference pose via webcam, and generate an AI template.")
        sub_lbl.setStyleSheet(f"color: {settings.THEME['text_secondary']}; font-size: 13px;")
        title_box.addWidget(sub_lbl)
        main_layout.addLayout(title_box)

        # Stacked Wizard Steps (0: Metadata Form, 1: Live Capture, 2: Review & Fine-tune)
        self.stack = QStackedWidget()

        # Step 0: Metadata Form
        self.step0_widget = self._build_metadata_form()
        self.stack.addWidget(self.step0_widget)

        # Step 1: Live Capture
        self.step1_widget = self._build_capture_screen()
        self.stack.addWidget(self.step1_widget)

        # Step 2: Review & Adjust
        self.step2_widget = self._build_review_screen()
        self.stack.addWidget(self.step2_widget)

        main_layout.addWidget(self.stack)

    def _build_metadata_form(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "card")
        form = QFormLayout(card)
        form.setSpacing(14)

        self.in_name = QLineEdit()
        self.in_name.setPlaceholderText("e.g. Flamingo Balance Pose")
        form.addRow("Pose Name *:", self.in_name)

        self.combo_cat = QComboBox()
        self.combo_cat.addItems(["Custom", "Standing", "Sitting", "Balance", "Strength", "Flexibility", "Relaxation"])
        form.addRow("Category *:", self.combo_cat)

        self.combo_diff = QComboBox()
        self.combo_diff.addItems(settings.DIFFICULTY_LEVELS)
        form.addRow("Difficulty *:", self.combo_diff)

        self.combo_goal = QComboBox()
        self.combo_goal.addItems(settings.GOALS)
        form.addRow("Primary Goal *:", self.combo_goal)

        self.spin_hold = QSpinBox()
        self.spin_hold.setRange(5, 120)
        self.spin_hold.setValue(20)
        form.addRow("Target Hold Duration (seconds):", self.spin_hold)

        self.in_desc = QPlainTextEdit()
        self.in_desc.setPlaceholderText("Describe the pose posture, alignment cues, and aesthetic.")
        self.in_desc.setMaximumHeight(80)
        form.addRow("Description:", self.in_desc)

        self.in_benefits = QPlainTextEdit()
        self.in_benefits.setPlaceholderText("Enter benefits (one per line)\ne.g.\nStrengthens quadriceps\nImproves balance")
        self.in_benefits.setMaximumHeight(80)
        form.addRow("Key Benefits:", self.in_benefits)

        self.in_instructions = QPlainTextEdit()
        self.in_instructions.setPlaceholderText("Enter instructions (one per line)\ne.g.\nStand tall on left foot\nLift right knee and hold ankle")
        self.in_instructions.setMaximumHeight(80)
        form.addRow("Instructions:", self.in_instructions)

        self.in_precautions = QLineEdit()
        self.in_precautions.setPlaceholderText("e.g. Avoid if suffering from acute ankle or knee injury")
        form.addRow("Precautions:", self.in_precautions)

        c_layout.addWidget(card)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Buttons
        btn_bar = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "btn_secondary")
        btn_cancel.clicked.connect(self.cancel_requested.emit)
        btn_bar.addWidget(btn_cancel)

        btn_bar.addStretch()

        btn_next = QPushButton("Proceed to Live Pose Capture 🎥 →")
        btn_next.setProperty("class", "btn_primary")
        btn_next.clicked.connect(self._go_to_capture)
        btn_bar.addWidget(btn_next)

        layout.addLayout(btn_bar)
        return widget

    def _build_capture_screen(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Instructions Banner
        banner = QFrame()
        banner.setProperty("class", "highlight_card")
        b_layout = QVBoxLayout(banner)
        b_title = QLabel("📸 Live Reference Capture Mode")
        b_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #A78BFA;")
        b_layout.addWidget(b_title)

        b_sub = QLabel("Stand 2-3 meters away. Assume and hold your desired pose steadily. Click 'Capture Reference' to record 30 stable frames.")
        b_sub.setStyleSheet("color: #FFFFFF; font-size: 13px;")
        b_layout.addWidget(b_sub)
        layout.addWidget(banner)

        # Video Frame Card
        self.capture_video_card = QFrame()
        self.capture_video_card.setProperty("class", "card")
        self.capture_video_card.setStyleSheet("background-color: #000000; border-radius: 12px;")
        cv_layout = QVBoxLayout(self.capture_video_card)
        cv_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_capture_video = QLabel("Starting Webcam...")
        self.lbl_capture_video.setAlignment(Qt.AlignCenter)
        self.lbl_capture_video.setMinimumSize(640, 420)
        cv_layout.addWidget(self.lbl_capture_video)
        layout.addWidget(self.capture_video_card)

        # Progress bar for frame sampling
        self.capture_progress = QProgressBar()
        self.capture_progress.setRange(0, self.target_frame_count)
        self.capture_progress.setValue(0)
        self.capture_progress.setTextVisible(True)
        self.capture_progress.setFormat("Sampled: %v / %m frames")
        layout.addWidget(self.capture_progress)

        # Status text
        self.lbl_capture_status = QLabel("Position yourself in frame and hold steady.")
        self.lbl_capture_status.setStyleSheet("color: #38BDF8; font-weight: bold;")
        self.lbl_capture_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_capture_status)

        # Button Bar
        btn_bar = QHBoxLayout()
        btn_back = QPushButton("← Back to Form")
        btn_back.setProperty("class", "btn_secondary")
        btn_back.clicked.connect(self._back_to_form)
        btn_bar.addWidget(btn_back)

        btn_bar.addStretch()

        self.btn_start_sampling = QPushButton("Capture Reference Pose 📸")
        self.btn_start_sampling.setProperty("class", "btn_primary")
        self.btn_start_sampling.clicked.connect(self._start_frame_sampling)
        btn_bar.addWidget(self.btn_start_sampling)

        layout.addLayout(btn_bar)
        return widget

    def _build_review_screen(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Header
        r_header = QLabel("🎉 Reference Pose Captured Successfully!")
        r_header.setStyleSheet("font-size: 20px; font-weight: bold; color: #10B981;")
        layout.addWidget(r_header)

        r_sub = QLabel("Review the calculated mean joint angles and fine-tune tolerances before saving to the library.")
        r_sub.setStyleSheet("color: #94A3B8; font-size: 13px;")
        layout.addWidget(r_sub)

        # Scroll area for joint rules review
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self.review_container = QWidget()
        self.review_layout = QVBoxLayout(self.review_container)
        self.review_layout.setSpacing(12)
        scroll.setWidget(self.review_container)
        layout.addWidget(scroll)

        # Buttons
        btn_bar = QHBoxLayout()
        btn_recapture = QPushButton("🔄 Re-capture Reference")
        btn_recapture.setProperty("class", "btn_secondary")
        btn_recapture.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_bar.addWidget(btn_recapture)

        btn_bar.addStretch()

        btn_save_final = QPushButton("Save & Register Custom Pose 💾")
        btn_save_final.setProperty("class", "btn_success")
        btn_save_final.clicked.connect(self._save_custom_pose_to_db)
        btn_bar.addWidget(btn_save_final)

        layout.addLayout(btn_bar)
        return widget

    def _go_to_capture(self) -> None:
        name = self.in_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Pose Name", "Please specify a name for your custom pose.")
            return

        self.stack.setCurrentIndex(1)
        self._start_capture_camera()

    def _back_to_form(self) -> None:
        self._stop_capture_camera()
        self.stack.setCurrentIndex(0)

    def _start_capture_camera(self) -> None:
        if self.camera_worker is None:
            self.camera_worker = CameraWorker()
            self.camera_worker.frame_ready.connect(self._on_capture_frame)
            self.camera_worker.start()

    def _stop_capture_camera(self) -> None:
        if self.camera_worker:
            self.camera_worker.stop()
            self.camera_worker = None

    def _start_frame_sampling(self) -> None:
        self.captured_frame_angles.clear()
        self.capture_progress.setValue(0)
        self.is_capturing_frames = True
        self.lbl_capture_status.setText("Sampling frames... Please HOLD STEADY!")
        self.lbl_capture_status.setStyleSheet("color: #F59E0B; font-weight: bold;")
        self.btn_start_sampling.setEnabled(False)

    def _on_capture_frame(
        self,
        frame: np.ndarray,
        landmarks: Dict[str, Dict[str, float]],
        is_visible: bool,
        status_msg: str,
        confidence: float,
    ) -> None:
        if self.stack.currentIndex() != 1:
            return

        # Extract angles
        angles = AngleCalculator.extract_all_angles(landmarks)

        if self.is_capturing_frames and is_visible and angles:
            self.captured_frame_angles.append(angles)
            self.capture_progress.setValue(len(self.captured_frame_angles))
            self.captured_snapshot = frame.copy()

            if len(self.captured_frame_angles) >= self.target_frame_count:
                self.is_capturing_frames = False
                self.btn_start_sampling.setEnabled(True)
                self._process_captured_template()

        # Render skeleton on preview
        annotated = PoseDrawer.draw_skeleton(frame, landmarks, show_angles=True)
        pix = PoseDrawer.frame_to_pixmap(annotated)
        self.lbl_capture_video.setPixmap(pix.scaled(self.lbl_capture_video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _process_captured_template(self) -> None:
        """Averages extracted multi-frame measurements and builds rules."""
        if not self.captured_frame_angles:
            return

        # Gather all joint keys
        all_keys = set()
        for fa in self.captured_frame_angles:
            all_keys.update(fa.keys())

        calculated_rules = []
        for k in sorted(list(all_keys)):
            vals = [fa[k] for fa in self.captured_frame_angles if k in fa]
            if not vals:
                continue

            mean_ang = float(np.mean(vals))
            std_ang = float(np.std(vals))

            # Base tolerance on stability (with min 10° and max 25°)
            computed_tol = max(10.0, min(25.0, round(std_ang * 2.5, 1) if std_ang > 3 else 15.0))

            calculated_rules.append({
                "joint_name": k,
                "target_angle": round(mean_ang, 1),
                "tolerance": computed_tol,
                "weight": 15.0,
                "feedback_message": f"Adjust your {k.replace('_', ' ')}",
            })

        self.calculated_rules = calculated_rules
        self._build_review_ui()
        self._stop_capture_camera()
        self.stack.setCurrentIndex(2)

    def _build_review_ui(self) -> None:
        while self.review_layout.count():
            item = self.review_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for idx, rule in enumerate(self.calculated_rules):
            card = QFrame()
            card.setProperty("class", "card")
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(14, 10, 14, 10)

            j_fmt = rule["joint_name"].replace("_", " ").title()
            name_lbl = QLabel(f"<b>{j_fmt}</b>")
            name_lbl.setMinimumWidth(150)
            c_layout.addWidget(name_lbl)

            target_lbl = QLabel(f"Target: {rule['target_angle']}°")
            target_lbl.setStyleSheet("color: #38BDF8; font-weight: bold;")
            target_lbl.setMinimumWidth(110)
            c_layout.addWidget(target_lbl)

            # Tolerance Slider
            tol_box = QHBoxLayout()
            tol_lbl = QLabel(f"Tolerance: ±{int(rule['tolerance'])}°")
            tol_lbl.setObjectName(f"lbl_tol_{idx}")
            tol_lbl.setMinimumWidth(110)

            slider = QSlider(Qt.Horizontal)
            slider.setRange(5, 35)
            slider.setValue(int(rule["tolerance"]))
            slider.valueChanged.connect(lambda val, i=idx, l=tol_lbl: self._on_tolerance_changed(i, val, l))
            tol_box.addWidget(tol_lbl)
            tol_box.addWidget(slider)

            c_layout.addLayout(tol_box)
            self.review_layout.addWidget(card)

    def _on_tolerance_changed(self, rule_idx: int, new_val: int, label: QLabel) -> None:
        label.setText(f"Tolerance: ±{new_val}°")
        self.calculated_rules[rule_idx]["tolerance"] = float(new_val)

    def _save_custom_pose_to_db(self) -> None:
        name = self.in_name.text().strip()
        cat = self.combo_cat.currentText()
        diff = self.combo_diff.currentText()
        goal = self.combo_goal.currentText()
        hold = self.spin_hold.value()
        desc = self.in_desc.toPlainText().strip() or f"User-created custom posture: {name}"

        benefits = [b.strip() for b in self.in_benefits.toPlainText().split("\n") if b.strip()]
        if not benefits:
            benefits = ["Builds core strength", "Improves posture and flexibility"]

        instructions = [i.strip() for i in self.in_instructions.toPlainText().split("\n") if i.strip()]
        if not instructions:
            instructions = ["Assume the captured posture", "Maintain alignment and breathe evenly"]

        precautions = self.in_precautions.text().strip() or "Practice within a comfortable range of motion."

        # Save snapshot image if available
        image_rel_path = None
        if self.captured_snapshot is not None:
            filename = f"custom_pose_{int(time.time())}.jpg"
            img_full_path = settings.REF_POSES_DIR / filename
            cv2.imwrite(str(img_full_path), self.captured_snapshot)
            image_rel_path = f"data/reference_poses/{filename}"

        ref_template_data = {
            "angles": {r["joint_name"]: r["target_angle"] for r in self.calculated_rules},
            "frame_samples_count": len(self.captured_frame_angles),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        user_id = self.user["id"] if self.user else None

        pose_id = self.db.add_custom_pose(
            name=name,
            category=cat,
            difficulty=diff,
            goal=goal,
            description=desc,
            benefits=benefits,
            instructions=instructions,
            precautions=precautions,
            image_path=image_rel_path,
            hold_duration=hold,
            rules=self.calculated_rules,
            reference_data=ref_template_data,
            created_by=user_id,
        )

        QMessageBox.information(
            self,
            "Success",
            f"Custom Pose '{name}' has been created and registered successfully!\nYou can now practice it anytime.",
        )

        created_pose = self.db.get_pose_by_id(pose_id)
        if created_pose:
            self.pose_created.emit(created_pose)

    def closeEvent(self, event) -> None:
        self._stop_capture_camera()
        super().closeEvent(event)
