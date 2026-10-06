"""
Dedicated 12-Step Surya Yoga (Sun Salutation) Guided Screen for KI.AI.
Features an interactive stepper bar (01/12), breathing cues, step-by-step instructions,
real-time webcam posture verification, joint checklist, and hold timers.
"""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from analysis.angle_calculator import AngleCalculator
from analysis.feedback import FeedbackEngine
from analysis.posture_checker import PostureChecker
from config import settings
from database.database import Database
from ui.reference_pose_panel import ReferencePosePanel
from vision.camera import CameraWorker
from vision.drawing import PoseDrawer
from vision.reference_helper import ReferenceHelper

logger = logging.getLogger(__name__)


class SuryaYogaWindow(QWidget):
    """Guided 12-step Surya Namaskar practice window with Reference Pose Panel."""

    finish_sequence = Signal()

    def __init__(self, db: Database, user: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user = user

        self.posture_checker = PostureChecker()
        self.feedback_engine = FeedbackEngine()

        self.surya_poses: List[Dict[str, Any]] = self.db.get_surya_namaskar_poses()
        self.current_step_index = 0
        self.is_practicing = False
        self.hold_count = 0
        self.ghost_mode = False

        self.camera_worker: Optional[CameraWorker] = None
        self.hold_timer = QTimer(self)
        self.hold_timer.setInterval(1000)
        self.hold_timer.timeout.connect(self._on_hold_timer_tick)

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # Header Row
        top_header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("☀ Surya Yoga (12-Step Sun Salutation)")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        subtitle = QLabel("Guided sequential flow with real-time posture checking and reference alignment.")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top_header.addLayout(title_box)
        top_header.addStretch()

        self.lbl_step_counter = QLabel("Step 01 / 12")
        self.lbl_step_counter.setStyleSheet("font-size: 18px; font-weight: 800; color: #10B981;")
        top_header.addWidget(self.lbl_step_counter)
        main_layout.addLayout(top_header)

        # Stepper Progress Bar (● ─ ● ─ ●)
        self.stepper_card = QFrame()
        self.stepper_card.setProperty("class", "card")
        self.stepper_layout = QHBoxLayout(self.stepper_card)
        self.stepper_layout.setContentsMargins(12, 8, 12, 8)
        self.stepper_layout.setSpacing(6)
        main_layout.addWidget(self.stepper_card)
        self._build_stepper_nodes()

        # Split Practice Layout (Camera Left, Reference & HUD Right)
        split_layout = QHBoxLayout()
        split_layout.setSpacing(14)

        # LEFT: Video Frame (Main Area)
        left_box = QVBoxLayout()
        left_box.setSpacing(10)

        self.video_card = QFrame()
        self.video_card.setProperty("class", "card")
        self.video_card.setStyleSheet("background-color: #000; border-radius: 12px;")
        v_layout = QVBoxLayout(self.video_card)
        v_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_video = QLabel("Initializing Surya Yoga Camera Feed...")
        self.lbl_video.setAlignment(Qt.AlignCenter)
        self.lbl_video.setMinimumSize(600, 420)
        self.lbl_video.setStyleSheet("color: #64748B; font-size: 14px;")
        v_layout.addWidget(self.lbl_video)
        left_box.addWidget(self.video_card, stretch=5)

        # Step Navigation Controls
        ctrl_bar = QFrame()
        ctrl_bar.setProperty("class", "card")
        c_layout = QHBoxLayout(ctrl_bar)
        c_layout.setContentsMargins(12, 8, 12, 8)
        c_layout.setSpacing(8)

        self.btn_prev = QPushButton("◀ Previous Step")
        self.btn_prev.setProperty("class", "btn_secondary")
        self.btn_prev.clicked.connect(self._on_prev_step)
        c_layout.addWidget(self.btn_prev)

        self.btn_toggle_practice = QPushButton("▶ Start Step")
        self.btn_toggle_practice.setProperty("class", "btn_primary")
        self.btn_toggle_practice.clicked.connect(self._on_toggle_practice)
        c_layout.addWidget(self.btn_toggle_practice)

        self.btn_next = QPushButton("Next Step ▶")
        self.btn_next.setProperty("class", "btn_secondary")
        self.btn_next.clicked.connect(self._on_next_step)
        c_layout.addWidget(self.btn_next)

        left_box.addWidget(ctrl_bar)
        split_layout.addLayout(left_box, stretch=6)

        # RIGHT: Reference Pose Panel + Breathing & Posture Info
        right_box = QVBoxLayout()
        right_box.setSpacing(10)

        # Embedded Reference Pose Panel
        initial_pose = self.surya_poses[0] if self.surya_poses else {}
        self.reference_panel = ReferencePosePanel(initial_pose, parent=self)
        self.reference_panel.ghost_mode_toggled.connect(lambda v: setattr(self, "ghost_mode", v))
        right_box.addWidget(self.reference_panel)

        step_card = QFrame()
        step_card.setProperty("class", "card")
        s_layout = QVBoxLayout(step_card)
        s_layout.setContentsMargins(14, 12, 14, 12)

        self.lbl_sanskrit = QLabel("PRANAMASANA")
        self.lbl_sanskrit.setStyleSheet("color: #10B981; font-weight: 700; font-size: 11px;")
        s_layout.addWidget(self.lbl_sanskrit)

        self.lbl_pose_name = QLabel("Prayer Pose")
        self.lbl_pose_name.setStyleSheet("font-size: 18px; font-weight: 800; color: #FFF;")
        s_layout.addWidget(self.lbl_pose_name)

        self.lbl_breathing = QLabel("💨 Exhale — Bring palms together at heart center.")
        self.lbl_breathing.setStyleSheet("background-color: rgba(16, 185, 129, 0.12); border-left: 3px solid #10B981; padding: 6px 10px; border-radius: 4px; font-size: 12px; font-weight: 500; margin-top: 4px;")
        self.lbl_breathing.setWordWrap(True)
        s_layout.addWidget(self.lbl_breathing)

        self.lbl_instructions = QLabel("Stand tall and establish smooth breathing.")
        self.lbl_instructions.setStyleSheet("color: #94A3B8; font-size: 12px; margin-top: 4px;")
        self.lbl_instructions.setWordWrap(True)
        s_layout.addWidget(self.lbl_instructions)

        right_box.addWidget(step_card)

        # Score & Timer Card
        score_card = QFrame()
        score_card.setProperty("class", "card")
        sc_layout = QVBoxLayout(score_card)
        sc_layout.setContentsMargins(14, 12, 14, 12)

        sc_head = QHBoxLayout()
        sc_title = QLabel("POSTURE SCORE")
        sc_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        sc_head.addWidget(sc_title)
        sc_head.addStretch()

        self.lbl_score_tier = QLabel("🟢 GOOD")
        self.lbl_score_tier.setStyleSheet("background: rgba(16, 185, 129, 0.18); color: #10B981; border: 1px solid #10B981; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;")
        sc_head.addWidget(self.lbl_score_tier)
        sc_layout.addLayout(sc_head)

        sc_mid = QHBoxLayout()
        self.lbl_score_val = QLabel("0%")
        self.lbl_score_val.setStyleSheet("font-size: 34px; font-weight: 800; color: #10B981;")
        sc_mid.addWidget(self.lbl_score_val)
        sc_mid.addStretch()

        time_box = QVBoxLayout()
        self.lbl_timer_count = QLabel("00 / 10s")
        self.lbl_timer_count.setStyleSheet("font-size: 20px; font-weight: 800; color: #FFF;")
        self.lbl_timer_count.setAlignment(Qt.AlignRight)
        time_box.addWidget(self.lbl_timer_count)

        self.lbl_timer_status = QLabel("Score ≥80% to hold")
        self.lbl_timer_status.setStyleSheet("color: #64748B; font-size: 11px;")
        self.lbl_timer_status.setAlignment(Qt.AlignRight)
        time_box.addWidget(self.lbl_timer_status)
        sc_mid.addLayout(time_box)

        sc_layout.addLayout(sc_mid)
        right_box.addWidget(score_card)

        # Feedback Cue Card
        fb_card = QFrame()
        fb_card.setProperty("class", "card")
        fb_card.setStyleSheet("background-color: #1E293B; border-left: 4px solid #10B981; border-radius: 8px; padding: 10px;")
        fb_layout = QVBoxLayout(fb_card)
        fb_head = QLabel("ACTIONABLE FEEDBACK")
        fb_head.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 700;")
        fb_layout.addWidget(fb_head)

        self.lbl_feedback = QLabel("Stand in front of the camera and begin Step 1.")
        self.lbl_feedback.setStyleSheet("color: #F8FAFC; font-size: 12px; font-weight: 500;")
        self.lbl_feedback.setWordWrap(True)
        fb_layout.addWidget(self.lbl_feedback)
        right_box.addWidget(fb_card)

        # Joint Alignment Checklist
        cl_card = QFrame()
        cl_card.setProperty("class", "card")
        cl_box = QVBoxLayout(cl_card)
        cl_box.setContentsMargins(12, 10, 12, 10)
        cl_title = QLabel("POSTURE STATUS")
        cl_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        cl_box.addWidget(cl_title)

        scroll_cl = QScrollArea()
        scroll_cl.setWidgetResizable(True)
        scroll_cl.setFrameShape(QFrame.NoFrame)
        scroll_cl.setStyleSheet("background: transparent;")
        self.cl_widget = QWidget()
        self.cl_layout = QVBoxLayout(self.cl_widget)
        self.cl_layout.setContentsMargins(0, 2, 0, 2)
        self.cl_layout.setSpacing(4)
        scroll_cl.setWidget(self.cl_widget)
        cl_box.addWidget(scroll_cl)

        right_box.addWidget(cl_card, stretch=4)
        split_layout.addLayout(right_box, stretch=4)

        main_layout.addLayout(split_layout)
        self._update_step_view()

    def _build_stepper_nodes(self) -> None:
        while self.stepper_layout.count():
            item = self.stepper_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for idx in range(12):
            node = QPushButton(f"{idx+1}")
            node.setFixedSize(28, 28)
            node.clicked.connect(lambda _, i=idx: self._jump_to_step(i))

            if idx == self.current_step_index:
                node.setStyleSheet("background-color: #064E3B; border: 2px solid #10B981; color: #10B981; border-radius: 14px; font-weight: bold; font-size: 11px;")
            elif idx < self.current_step_index:
                node.setStyleSheet("background-color: #10B981; color: #FFF; border: none; border-radius: 14px; font-weight: bold; font-size: 11px;")
            else:
                node.setStyleSheet("background-color: #0F172A; border: 1px solid #334155; color: #64748B; border-radius: 14px; font-size: 11px;")

            self.stepper_layout.addWidget(node)
            if idx < 11:
                line = QFrame()
                line.setFixedHeight(2)
                line.setStyleSheet(f"background-color: {'#10B981' if idx < self.current_step_index else '#334155'};")
                self.stepper_layout.addWidget(line)

    def _jump_to_step(self, idx: int) -> None:
        self.current_step_index = idx
        self._build_stepper_nodes()
        self._update_step_view()

    def _on_prev_step(self) -> None:
        if self.current_step_index > 0:
            self._jump_to_step(self.current_step_index - 1)

    def _on_next_step(self) -> None:
        if self.current_step_index < len(self.surya_poses) - 1:
            self._jump_to_step(self.current_step_index + 1)
        else:
            self.feedback_engine.speak_cue("Surya Namaskar 12-step sequence completed!")
            self.finish_sequence.emit()

    def _update_step_view(self) -> None:
        if not self.surya_poses or self.current_step_index >= len(self.surya_poses):
            return

        pose = self.surya_poses[self.current_step_index]
        self.lbl_step_counter.setText(f"Step {self.current_step_index+1:02d} / 12")
        self.lbl_pose_name.setText(pose.get("name", "").replace(f"Step {self.current_step_index+1}: ", ""))
        self.lbl_sanskrit.setText(pose.get("sanskrit_name", "Surya Asana").upper())
        self.lbl_instructions.setText(pose.get("description", ""))

        target_hold = pose.get("hold_duration", 10)
        self.lbl_timer_count.setText(f"00 / {target_hold}s")
        self.hold_count = 0
        self.reference_panel.set_pose(pose)
        self._build_joint_checklist()

    def _build_joint_checklist(self) -> None:
        while self.cl_layout.count():
            item = self.cl_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.surya_poses:
            return

        pose = self.surya_poses[self.current_step_index]
        for rule in pose.get("rules", []):
            j_name = rule.get("joint_name", "")
            fmt_name = FeedbackEngine.format_joint_name(j_name)
            target = int(round(float(rule.get("target_angle", 0.0))))

            row = QFrame()
            row.setObjectName(f"surya_row_{j_name}")
            row.setStyleSheet("background-color: #0F172A; border-radius: 6px; padding: 4px 8px;")
            r_lay = QHBoxLayout(row)
            r_lay.setContentsMargins(6, 3, 6, 3)

            lbl_dot = QLabel("⚪")
            lbl_dot.setObjectName(f"surya_dot_{j_name}")
            r_lay.addWidget(lbl_dot)

            lbl_name = QLabel(fmt_name)
            lbl_name.setStyleSheet("color: #F8FAFC; font-weight: 500; font-size: 12px;")
            r_lay.addWidget(lbl_name)
            r_lay.addStretch()

            lbl_deg = QLabel(f"-- / {target}°")
            lbl_deg.setObjectName(f"surya_deg_{j_name}")
            lbl_deg.setStyleSheet("color: #64748B; font-size: 11px;")
            r_lay.addWidget(lbl_deg)

            self.cl_layout.addWidget(row)

    def start_camera(self) -> None:
        if self.camera_worker is None or not self.camera_worker.isRunning():
            self.camera_worker = CameraWorker(camera_index=0)
            self.camera_worker.frame_ready.connect(self._on_frame_received)
            self.camera_worker.start()

    def stop_camera(self) -> None:
        if self.camera_worker and self.camera_worker.isRunning():
            self.camera_worker.stop()
            self.camera_worker = None
        self.hold_timer.stop()

    def _on_toggle_practice(self) -> None:
        self.is_practicing = not self.is_practicing
        if self.is_practicing:
            self.btn_toggle_practice.setText("⏹ Pause Step")
            self.btn_toggle_practice.setStyleSheet("background-color: #EF4444; color: white;")
            self.hold_timer.start()
        else:
            self.btn_toggle_practice.setText("▶ Start Step")
            self.btn_toggle_practice.setStyleSheet("")
            self.hold_timer.stop()

    def _on_hold_timer_tick(self) -> None:
        if not self.is_practicing:
            return

        pose = self.surya_poses[self.current_step_index]
        target_hold = pose.get("hold_duration", 10)
        curr_score = float(self.lbl_score_val.text().replace("%", "") or "0")

        if curr_score >= 80.0:
            self.hold_count += 1
            self.lbl_timer_count.setText(f"{self.hold_count:02d} / {target_hold}s")
            self.lbl_timer_status.setText("✓ Posture holding steady!")
            self.lbl_timer_status.setStyleSheet("color: #10B981; font-weight: bold;")

            if self.hold_count >= target_hold:
                self.feedback_engine.speak_cue(f"Step {self.current_step_index+1} complete! Moving to next step.")
                self.hold_count = 0
                self._on_next_step()
        else:
            self.lbl_timer_status.setText("⏸ Hold Paused — Adjust Alignment")
            self.lbl_timer_status.setStyleSheet("color: #F59E0B;")

    def _on_frame_received(
        self,
        frame: np.ndarray,
        landmarks: Dict[str, Dict[str, float]],
        is_visible: bool,
        status_msg: str,
        confidence: float,
    ) -> None:
        if not self.surya_poses:
            return

        pose = self.surya_poses[self.current_step_index]
        if not is_visible:
            pixmap = PoseDrawer.frame_to_pixmap(frame)
            self.lbl_video.setPixmap(pixmap.scaled(self.lbl_video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return

        actual_angles = AngleCalculator.extract_all_angles(landmarks)
        posture_res = self.posture_checker.check_posture(pose, actual_angles, is_body_visible=True)

        overall_score = posture_res.get("overall_score", 0.0)
        level_info = posture_res.get("level_info", settings.SCORE_LEVELS["INCORRECT"])

        self.lbl_score_val.setText(f"{int(round(overall_score))}%")
        self.lbl_score_val.setStyleSheet(f"font-size: 34px; font-weight: 800; color: {level_info['color']};")
        self.lbl_score_tier.setText(f"{level_info.get('dot', '🟢')} {level_info.get('label', 'GOOD')}")

        primary_fb = posture_res.get("primary_feedback", "")
        self.lbl_feedback.setText(primary_fb or "Maintain steady posture and even breathing.")

        if self.is_practicing:
            self.feedback_engine.speak_cue(primary_fb)

        # Update checklist dots
        for res in posture_res.get("joint_results", []):
            j_name = res.get("joint_name", "")
            actual = int(round(float(res.get("actual_angle", 0.0))))
            target = int(round(float(res.get("target_angle", 0.0))))

            dot_lbl = self.cl_widget.findChild(QLabel, f"surya_dot_{j_name}")
            deg_lbl = self.cl_widget.findChild(QLabel, f"surya_deg_{j_name}")

            if dot_lbl:
                dot_lbl.setText(res.get("status_dot", "⚪"))
            if deg_lbl:
                deg_lbl.setText(f"{actual}° / {target}°")

        # Update Reference Panel Live Comparison
        self.reference_panel.update_live_comparison(posture_res)

        annotated_frame = PoseDrawer.draw_skeleton(frame, landmarks, posture_res, show_angles=True)

        if self.ghost_mode:
            annotated_frame = PoseDrawer.draw_ghost_reference_skeleton(
                annotated_frame,
                pose.get("name", ""),
                alpha=0.38
            )

        pixmap = PoseDrawer.frame_to_pixmap(annotated_frame)
        self.lbl_video.setPixmap(pixmap.scaled(self.lbl_video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
