"""
Real-Time Practice Screen for AI Yoga Assistant.
Provides live camera feed, real-time skeleton overlays, live posture evaluation,
pose identification, posture status checklist with small circular status dots,
hold timer, and actionable corrective feedback.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
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
from analysis.pose_classifier import PoseClassifier
from analysis.posture_checker import PostureChecker
from analysis.score_calculator import ScoreCalculator
from config import settings
from database.database import Database
from ui.reference_pose_panel import ReferencePosePanel
from ui.session_summary import SessionSummaryDialog
from vision.camera import CameraWorker
from vision.drawing import PoseDrawer

logger = logging.getLogger(__name__)


class CameraWindow(QWidget):
    """Real-time Yoga Practice and Posture Correction Screen with Reference Pose Panel."""

    session_completed = Signal(dict)
    back_to_library = Signal()

    def __init__(
        self,
        db: Database,
        user: Optional[Dict[str, Any]] = None,
        selected_pose: Optional[Dict[str, Any]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.db = db
        self.user = user
        self.selected_pose = selected_pose

        # Analysis Engines
        self.posture_checker = PostureChecker()
        self.feedback_engine = FeedbackEngine()

        # Session tracking state
        self.is_practicing = False
        self.is_paused = False
        self.session_start_time: Optional[float] = None
        self.elapsed_practice_time = 0
        self.hold_time_seconds = 0
        self.score_samples: List[float] = []
        self.mistake_frequencies: Dict[str, int] = {}
        self.corrections_count = 0
        self.ghost_mode = False

        # Camera worker thread
        self.camera_worker: Optional[CameraWorker] = None

        # Hold timer ticker
        self.hold_timer = QTimer(self)
        self.hold_timer.setInterval(1000)  # 1 second ticks
        self.hold_timer.timeout.connect(self._on_hold_timer_tick)

        self._all_poses_cache = self.db.get_all_poses()
        self._init_ui()

    def set_active_pose(self, pose: Dict[str, Any]) -> None:
        """Sets the active pose to practice and updates reference panel."""
        self.selected_pose = self.db.get_pose_by_id(pose["id"]) or pose
        self.lbl_selected_pose_name.setText(self.selected_pose.get("name", "Pose"))
        self.lbl_selected_sanskrit.setText(self.selected_pose.get("sanskrit_name", ""))
        self.lbl_header_pose.setText(f"Current Pose: {self.selected_pose.get('name', 'Pose')}")
        self.lbl_header_ref.setText(f"Reference: {self.selected_pose.get('sanskrit_name', '')}")
        target_hold = self.selected_pose.get("hold_duration", settings.DEFAULT_HOLD_DURATION_SECONDS)
        self.lbl_target_hold.setText(f"Target Hold: {target_hold}s")
        self.lbl_header_hold.setText(f"Target Hold: {target_hold}s")
        self.reference_panel.set_pose(self.selected_pose)
        self.reset_session()
        self._build_joint_checklist()

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(14, 12, 14, 12)
        outer_layout.setSpacing(10)

        # ==========================================
        # TOP: Live Practice Header Bar
        # ==========================================
        header_bar = QFrame()
        header_bar.setProperty("class", "card")
        header_bar.setStyleSheet("""
            background: linear-gradient(135deg, #0F172A, #064E3B);
            border: 1px solid #10B981;
            border-radius: 10px;
            padding: 4px;
        """)
        h_layout = QHBoxLayout(header_bar)
        h_layout.setContentsMargins(14, 6, 14, 6)

        self.lbl_header_pose = QLabel(f"Current Pose: {self.selected_pose.get('name', 'Pose') if self.selected_pose else 'Pose'}")
        self.lbl_header_pose.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF;")
        h_layout.addWidget(self.lbl_header_pose)

        self.lbl_header_ref = QLabel(f"Reference: {self.selected_pose.get('sanskrit_name', '') if self.selected_pose else ''}")
        self.lbl_header_ref.setStyleSheet("color: #34D399; font-weight: 600; font-size: 12px; font-style: italic;")
        h_layout.addWidget(self.lbl_header_ref)

        h_layout.addStretch()

        self.lbl_header_hold = QLabel(f"Target Hold: {self.selected_pose.get('hold_duration', 20) if self.selected_pose else 20}s")
        self.lbl_header_hold.setStyleSheet("color: #A78BFA; font-weight: 700; font-size: 12px;")
        h_layout.addWidget(self.lbl_header_hold)

        self.lbl_header_match = QLabel("AI Match: --%")
        self.lbl_header_match.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.2);
            color: #10B981;
            border: 1px solid #10B981;
            border-radius: 6px;
            padding: 3px 10px;
            font-size: 12px;
            font-weight: 800;
        """)
        h_layout.addWidget(self.lbl_header_match)

        outer_layout.addWidget(header_bar)

        # ==========================================
        # SPLIT MAIN AREA: Camera Left, Reference Right
        # ==========================================
        main_split = QHBoxLayout()
        main_split.setSpacing(14)

        # LEFT: Video Stream View (Main Area)
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)

        self.video_card = QFrame()
        self.video_card.setProperty("class", "card")
        self.video_card.setStyleSheet(f"""
            QFrame.card {{
                background-color: #000000;
                border: 2px solid {settings.THEME['border']};
                border-radius: 12px;
            }}
        """)
        video_card_layout = QVBoxLayout(self.video_card)
        video_card_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_video = QLabel()
        self.lbl_video.setAlignment(Qt.AlignCenter)
        self.lbl_video.setMinimumSize(600, 420)
        self.lbl_video.setText("Initializing Camera Feed...")
        self.lbl_video.setStyleSheet("color: #64748B; font-size: 15px;")
        video_card_layout.addWidget(self.lbl_video)
        left_panel.addWidget(self.video_card, stretch=5)

        # Visibility / Tracking Banner
        self.lbl_warning_banner = QLabel("Camera Ready — Position yourself 2-3 meters away")
        self.lbl_warning_banner.setAlignment(Qt.AlignCenter)
        self.lbl_warning_banner.setStyleSheet("""
            background-color: #1E293B;
            color: #10B981;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 500;
        """)
        left_panel.addWidget(self.lbl_warning_banner)

        # Bottom Control Toolbar
        control_bar = QFrame()
        control_bar.setProperty("class", "card")
        ctrl_layout = QHBoxLayout(control_bar)
        ctrl_layout.setContentsMargins(12, 8, 12, 8)
        ctrl_layout.setSpacing(8)

        self.btn_toggle_practice = QPushButton("▶ Start Practice")
        self.btn_toggle_practice.setProperty("class", "btn_success")
        self.btn_toggle_practice.clicked.connect(self._on_toggle_practice)
        ctrl_layout.addWidget(self.btn_toggle_practice)

        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setProperty("class", "btn_secondary")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._on_toggle_pause)
        ctrl_layout.addWidget(self.btn_pause)

        self.btn_reset = QPushButton("🔄 Reset")
        self.btn_reset.setProperty("class", "btn_secondary")
        self.btn_reset.clicked.connect(self.reset_session)
        ctrl_layout.addWidget(self.btn_reset)

        self.btn_finish = QPushButton("✓ Finish")
        self.btn_finish.setProperty("class", "btn_primary")
        self.btn_finish.clicked.connect(self._on_finish_session)
        ctrl_layout.addWidget(self.btn_finish)

        ctrl_layout.addStretch()

        self.combo_cam = QComboBox()
        self.combo_cam.addItems(["Camera 0", "Camera 1", "Camera 2"])
        self.combo_cam.currentIndexChanged.connect(self._on_camera_selected)
        ctrl_layout.addWidget(self.combo_cam)

        self.chk_voice = QCheckBox("🔊 Voice Coach")
        self.chk_voice.setChecked(True)
        self.chk_voice.toggled.connect(lambda v: self.feedback_engine.voice.set_enabled(v))
        ctrl_layout.addWidget(self.chk_voice)

        left_panel.addWidget(control_bar)
        main_split.addLayout(left_panel, stretch=6)

        # RIGHT: Reference Pose Panel + Live Posture HUD Panel (40% width)
        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)

        # 1. Embedded Reference Pose Panel
        self.reference_panel = ReferencePosePanel(self.selected_pose, parent=self)
        self.reference_panel.ghost_mode_toggled.connect(self._on_ghost_mode_toggled)
        right_panel.addWidget(self.reference_panel)

        # 2. Large Overall Posture Indicator Card
        score_hud_card = QFrame()
        score_hud_card.setProperty("class", "card")
        s_hud_layout = QVBoxLayout(score_hud_card)
        s_hud_layout.setContentsMargins(16, 12, 16, 12)
        s_hud_layout.setSpacing(6)

        s_header_row = QHBoxLayout()
        s_title = QLabel("OVERALL POSTURE SCORE")
        s_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        s_header_row.addWidget(s_title)
        s_header_row.addStretch()

        # Large Overall Status Badge (🟢 EXCELLENT / 🟢 GOOD / 🟡 NEEDS IMPROVEMENT / 🔴 NEEDS CORRECTION)
        self.lbl_score_tier = QLabel("🔴 NEEDS CORRECTION")
        self.lbl_score_tier.setStyleSheet("""
            background-color: rgba(239, 68, 68, 0.18);
            color: #EF4444;
            border: 1px solid #EF4444;
            border-radius: 6px;
            font-weight: bold;
            font-size: 12px;
            padding: 3px 10px;
        """)
        s_header_row.addWidget(self.lbl_score_tier)
        s_hud_layout.addLayout(s_header_row)

        score_row = QHBoxLayout()
        self.lbl_live_score = QLabel("0%")
        self.lbl_live_score.setStyleSheet("font-size: 38px; font-weight: bold; color: #EF4444;")
        score_row.addWidget(self.lbl_live_score)
        score_row.addStretch()

        # Hold Timer Widget inside score card
        timer_box = QVBoxLayout()
        self.lbl_hold_count = QLabel("00 / 20s")
        self.lbl_hold_count.setStyleSheet("font-size: 22px; font-weight: bold; color: #FFFFFF;")
        self.lbl_hold_count.setAlignment(Qt.AlignRight)
        timer_box.addWidget(self.lbl_hold_count)

        self.lbl_timer_status = QLabel("Score ≥80% to hold")
        self.lbl_timer_status.setStyleSheet("color: #64748B; font-size: 11px;")
        self.lbl_timer_status.setAlignment(Qt.AlignRight)
        timer_box.addWidget(self.lbl_timer_status)
        score_row.addLayout(timer_box)

        s_hud_layout.addLayout(score_row)

        self.progress_score = QProgressBar()
        self.progress_score.setRange(0, 100)
        self.progress_score.setValue(0)
        self.progress_score.setTextVisible(False)
        self.progress_score.setFixedHeight(6)
        self.progress_score.setStyleSheet("""
            QProgressBar {
                background-color: #334155;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #EF4444;
                border-radius: 3px;
            }
        """)
        s_hud_layout.addWidget(self.progress_score)
        right_panel.addWidget(score_hud_card)

        # 3. POSTURE STATUS (Joint-by-Joint Checklist with Circular Dots)
        checklist_card = QFrame()
        checklist_card.setProperty("class", "card")
        cl_layout = QVBoxLayout(checklist_card)
        cl_layout.setContentsMargins(14, 12, 14, 12)
        cl_layout.setSpacing(8)

        cl_header = QHBoxLayout()
        cl_title = QLabel("POSTURE STATUS")
        cl_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        cl_header.addWidget(cl_title)
        cl_header.addStretch()

        cl_legend = QLabel("🟢 Correct  🟡 Adjust  🔴 Needs Fix")
        cl_legend.setStyleSheet("color: #64748B; font-size: 10px;")
        cl_header.addWidget(cl_legend)
        cl_layout.addLayout(cl_header)

        scroll_cl = QScrollArea()
        scroll_cl.setWidgetResizable(True)
        scroll_cl.setFrameShape(QFrame.NoFrame)
        scroll_cl.setStyleSheet("background: transparent;")

        self.checklist_widget = QWidget()
        self.checklist_layout = QVBoxLayout(self.checklist_widget)
        self.checklist_layout.setContentsMargins(0, 2, 0, 2)
        self.checklist_layout.setSpacing(6)

        scroll_cl.setWidget(self.checklist_widget)
        cl_layout.addWidget(scroll_cl)
        right_panel.addWidget(checklist_card, stretch=4)

        # 4. Actionable FEEDBACK Box
        self.feedback_card = QFrame()
        self.feedback_card.setProperty("class", "card")
        self.feedback_card.setStyleSheet("""
            background-color: #1E293B;
            border-left: 4px solid #6366F1;
            border-radius: 8px;
            padding: 12px;
        """)
        fb_layout = QVBoxLayout(self.feedback_card)
        fb_layout.setContentsMargins(10, 10, 10, 10)
        fb_layout.setSpacing(6)

        fb_title = QLabel("FEEDBACK & CORRECTIONS")
        fb_title.setStyleSheet("color: #6366F1; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        fb_layout.addWidget(fb_title)

        scroll_fb = QScrollArea()
        scroll_fb.setWidgetResizable(True)
        scroll_fb.setFrameShape(QFrame.NoFrame)
        scroll_fb.setStyleSheet("background: transparent;")
        scroll_fb.setMaximumHeight(110)

        self.feedback_list_widget = QWidget()
        self.feedback_list_layout = QVBoxLayout(self.feedback_list_widget)
        self.feedback_list_layout.setContentsMargins(0, 0, 0, 0)
        self.feedback_list_layout.setSpacing(4)

        scroll_fb.setWidget(self.feedback_list_widget)
        fb_layout.addWidget(scroll_fb)

        right_panel.addWidget(self.feedback_card, stretch=2)

        main_split.addLayout(right_panel, stretch=4)
        outer_layout.addLayout(main_split)

    def start_camera(self) -> None:
        """Starts the background camera worker."""
        if self.camera_worker is None or not self.camera_worker.isRunning():
            cam_idx = self.combo_cam.currentIndex()
            self.camera_worker = CameraWorker(camera_index=cam_idx)
            self.camera_worker.frame_ready.connect(self._on_frame_received)
            self.camera_worker.error_occurred.connect(self._on_camera_error)
            self.camera_worker.start()
            logger.info("CameraWorker started.")

    def stop_camera(self) -> None:
        """Stops the camera worker."""
        if self.camera_worker and self.camera_worker.isRunning():
            self.camera_worker.stop()
            self.camera_worker = None
        self.hold_timer.stop()

    def _on_camera_selected(self, index: int) -> None:
        if self.camera_worker:
            self.stop_camera()
            self.start_camera()

    def _on_camera_error(self, err_msg: str) -> None:
        self.lbl_warning_banner.setText(f"❌ Camera Error: {err_msg}")
        self.lbl_warning_banner.setStyleSheet("background-color: #7F1D1D; color: #FECACA; padding: 8px; border-radius: 8px;")

    def _on_toggle_practice(self) -> None:
        if not self.is_practicing:
            # Start
            self.is_practicing = True
            self.is_paused = False
            self.session_start_time = time.time()
            self.btn_toggle_practice.setText("⏹ Stop Practice")
            self.btn_toggle_practice.setProperty("class", "btn_danger")
            self.btn_toggle_practice.setStyleSheet("background-color: #EF4444; color: white;")
            self.btn_pause.setEnabled(True)
            self.hold_timer.start()
        else:
            # Stop & show summary
            self._on_finish_session()

    def _on_toggle_pause(self) -> None:
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.setText("▶ Resume")
            self.hold_timer.stop()
        else:
            self.btn_pause.setText("⏸ Pause")
            self.hold_timer.start()

    def reset_session(self) -> None:
        """Resets all live practice statistics."""
        self.hold_time_seconds = 0
        self.score_samples.clear()
        self.mistake_frequencies.clear()
        self.corrections_count = 0
        self.elapsed_practice_time = 0
        target = self.selected_pose.get("hold_duration", 20) if self.selected_pose else 20
        self.lbl_hold_count.setText(f"00 / {target}s")
        self.lbl_timer_status.setText("Score ≥80% to hold")
        self.lbl_live_score.setText("0%")
        self.progress_score.setValue(0)

    def _on_hold_timer_tick(self) -> None:
        if not self.is_practicing or self.is_paused:
            return

        self.elapsed_practice_time += 1
        last_score = self.score_samples[-1] if self.score_samples else 0.0
        target_hold = self.selected_pose.get("hold_duration", settings.DEFAULT_HOLD_DURATION_SECONDS) if self.selected_pose else 20

        if last_score >= settings.HOLD_TIMER_ACTIVATION_SCORE:
            self.hold_time_seconds += 1
            self.lbl_hold_count.setText(f"{self.hold_time_seconds:02d} / {target_hold}s")
            self.lbl_timer_status.setText("✓ Posture holding steady!")
            self.lbl_timer_status.setStyleSheet("color: #10B981; font-weight: bold;")

            if self.hold_time_seconds >= target_hold:
                self.feedback_engine.speak_cue("Target hold achieved! Pose completed successfully.")
                self.lbl_timer_status.setText("🎉 Target Complete!")
                self._on_finish_session()
        else:
            self.lbl_timer_status.setText("⏸ Hold Paused — Correct Posture")
            self.lbl_timer_status.setStyleSheet("color: #F59E0B;")

    def _build_joint_checklist(self) -> None:
        """Constructs UI checklist rows with circular dots and labels for rules in the active pose."""
        while self.checklist_layout.count():
            item = self.checklist_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.selected_pose or not self.selected_pose.get("rules"):
            return

        for rule in self.selected_pose["rules"]:
            j_name = rule.get("joint_name", "")
            fmt_name = FeedbackEngine.format_joint_name(j_name)
            target = int(round(float(rule.get("target_angle", 0.0))))

            row = QFrame()
            row.setObjectName(f"joint_row_{j_name}")
            row.setStyleSheet("""
                QFrame {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 4px 8px;
                }
            """)
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(6, 4, 6, 4)
            r_layout.setSpacing(8)

            # Circular Status Dot
            lbl_dot = QLabel("⚪")
            lbl_dot.setObjectName(f"status_dot_{j_name}")
            lbl_dot.setFixedWidth(20)
            lbl_dot.setAlignment(Qt.AlignCenter)
            r_layout.addWidget(lbl_dot)

            # Body Part Name
            lbl_name = QLabel(fmt_name)
            lbl_name.setStyleSheet("color: #F8FAFC; font-weight: 500; font-size: 12px;")
            r_layout.addWidget(lbl_name)
            r_layout.addStretch()

            # Target Degrees
            lbl_deg = QLabel(f"-- / {target}°")
            lbl_deg.setObjectName(f"deg_val_{j_name}")
            lbl_deg.setStyleSheet("color: #64748B; font-size: 11px;")
            r_layout.addWidget(lbl_deg)

            # Status Text Badge (Correct / Adjust Slightly / Needs Correction / Not Detected)
            lbl_status_badge = QLabel("Not Detected")
            lbl_status_badge.setObjectName(f"status_badge_{j_name}")
            lbl_status_badge.setStyleSheet("""
                background-color: rgba(148, 163, 184, 0.15);
                color: #94A3B8;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 600;
            """)
            lbl_status_badge.setAlignment(Qt.AlignCenter)
            r_layout.addWidget(lbl_status_badge)

            self.checklist_layout.addWidget(row)

    def _update_joint_checklist(self, joint_results: List[Dict[str, Any]]) -> None:
        """Updates each joint row in real time with calculated angle, status dot, and badge."""
        for res in joint_results:
            j_name = res.get("joint_name", "")
            status_code = res.get("status_code", "CORRECT")
            status_label = res.get("status_label", "Correct")
            status_dot = res.get("status_dot", "🟢")
            status_color = res.get("status_color", "#10B981")

            actual = int(round(float(res.get("actual_angle", 0.0))))
            target = int(round(float(res.get("target_angle", 0.0))))

            dot_lbl = self.checklist_widget.findChild(QLabel, f"status_dot_{j_name}")
            deg_lbl = self.checklist_widget.findChild(QLabel, f"deg_val_{j_name}")
            badge_lbl = self.checklist_widget.findChild(QLabel, f"status_badge_{j_name}")

            if dot_lbl:
                dot_lbl.setText(status_dot)

            if deg_lbl:
                if status_code == "NOT_DETECTED":
                    deg_lbl.setText(f"-- / {target}°")
                    deg_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
                else:
                    deg_lbl.setText(f"{actual}° / {target}°")
                    deg_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")

            if badge_lbl:
                badge_lbl.setText(status_label)
                if status_code == "CORRECT":
                    badge_lbl.setStyleSheet("background-color: rgba(16, 185, 129, 0.18); color: #10B981; border: 1px solid #10B981; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600;")
                elif status_code == "WARNING":
                    badge_lbl.setStyleSheet("background-color: rgba(245, 158, 11, 0.18); color: #F59E0B; border: 1px solid #F59E0B; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600;")
                elif status_code == "NOT_DETECTED":
                    badge_lbl.setStyleSheet("background-color: rgba(148, 163, 184, 0.15); color: #94A3B8; border: 1px solid #64748B; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600;")
                else:
                    badge_lbl.setStyleSheet("background-color: rgba(239, 68, 68, 0.18); color: #EF4444; border: 1px solid #EF4444; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600;")

    def _update_feedback_box(self, structured_feedback: List[Dict[str, Any]]) -> None:
        """Renders actionable corrective messages with matching colored status dots."""
        while self.feedback_list_layout.count():
            item = self.feedback_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not structured_feedback:
            lbl = QLabel("🟢 Maintain position and breathe evenly.")
            lbl.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 500;")
            self.feedback_list_layout.addWidget(lbl)
            return

        for cue in structured_feedback[:4]:  # Show top prioritized cues
            dot = cue.get("dot", "🔴")
            msg = cue.get("message", "")
            color = cue.get("color", "#EF4444")

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)

            dot_lbl = QLabel(dot)
            dot_lbl.setFixedWidth(16)
            row.addWidget(dot_lbl)

            msg_lbl = QLabel(msg)
            msg_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 500;")
            msg_lbl.setWordWrap(True)
            row.addWidget(msg_lbl, stretch=1)

            c_w = QWidget()
            c_w.setLayout(row)
            self.feedback_list_layout.addWidget(c_w)

    def _on_frame_received(
        self,
        frame: np.ndarray,
        landmarks: Dict[str, Dict[str, float]],
        is_visible: bool,
        status_msg: str,
        confidence: float,
    ) -> None:
        """Main real-time frame processing callback invoked from CameraWorker thread."""
        if not self.selected_pose:
            return

        # 1. Check Body Visibility
        if not is_visible:
            self.lbl_warning_banner.setText(f"⚠️ {status_msg}")
            self.lbl_warning_banner.setStyleSheet("background-color: #78350F; color: #FDE68A; padding: 8px; border-radius: 8px;")
            pixmap = PoseDrawer.frame_to_pixmap(frame)
            self.lbl_video.setPixmap(pixmap.scaled(self.lbl_video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return
        else:
            self.lbl_warning_banner.setText(f"✓ Tracking Active (Detection Confidence: {int(confidence*100)}%)")
            self.lbl_warning_banner.setStyleSheet("background-color: #064E3B; color: #A7F3D0; padding: 8px; border-radius: 8px;")

        # 2. Extract Angles
        actual_angles = AngleCalculator.extract_all_angles(landmarks)

        # 3. Pose Identification (What is user performing?)
        detected_name, match_score, _ = PoseClassifier.identify_pose(actual_angles, self._all_poses_cache)
        if self.selected_pose["name"].lower() in detected_name.lower():
            self.lbl_detected_pose.setText(f"Detected: {detected_name} ✓ ({match_score:.0f}% match)")
            self.lbl_detected_pose.setStyleSheet("background-color: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981; border-radius: 6px; padding: 4px 8px; font-size: 11px;")
        else:
            self.lbl_detected_pose.setText(f"Detected: {detected_name} (Target: {self.selected_pose['name']})")
            self.lbl_detected_pose.setStyleSheet("background-color: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B; border-radius: 6px; padding: 4px 8px; font-size: 11px;")

        # 4. Posture Correction & Scoring
        posture_res = self.posture_checker.check_posture(self.selected_pose, actual_angles, is_body_visible=True)

        overall_score = posture_res.get("overall_score", 0.0)
        level_info = posture_res.get("level_info", settings.SCORE_LEVELS["INCORRECT"])
        primary_feedback = posture_res.get("primary_feedback", "")
        structured_fb = posture_res.get("structured_feedback", [])

        # Update Overall Posture Indicator HUD
        self.lbl_live_score.setText(f"{int(round(overall_score))}%")
        self.lbl_live_score.setStyleSheet(f"font-size: 38px; font-weight: bold; color: {level_info['color']};")

        # Large Status Badge: 🟢 EXCELLENT / 🟢 GOOD / 🟡 NEEDS IMPROVEMENT / 🔴 NEEDS CORRECTION
        dot_icon = level_info.get("dot", "🟢")
        self.lbl_score_tier.setText(f"{dot_icon} {level_info['label']}")
        self.lbl_score_tier.setStyleSheet(f"""
            background-color: {level_info['bg_color']};
            color: {level_info['color']};
            border: 1px solid {level_info['border_color']};
            border-radius: 6px;
            font-weight: bold;
            font-size: 12px;
            padding: 3px 10px;
        """)

        self.progress_score.setValue(int(round(overall_score)))
        self.progress_score.setStyleSheet(f"""
            QProgressBar {{
                background-color: #334155;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {level_info['color']};
                border-radius: 3px;
            }}
        """)

        # Voice Speech Cue
        if self.is_practicing and not self.is_paused:
            self.feedback_engine.speak_cue(primary_feedback)

        # Update Posture Status Checklist & Feedback Box
        self._update_joint_checklist(posture_res.get("joint_results", []))
        self._update_feedback_box(structured_fb)

        # Record samples if practice session is actively running
        if self.is_practicing and not self.is_paused:
            self.score_samples.append(overall_score)
            for j_res in posture_res.get("joint_results", []):
                if j_res.get("status_code") == "INCORRECT":
                    self.corrections_count += 1
                    j_fmt = j_res.get("formatted_name", "General")
                    self.mistake_frequencies[j_fmt] = self.mistake_frequencies.get(j_fmt, 0) + 1

        # Update Live Comparison on Reference Panel
        self.reference_panel.update_live_comparison(posture_res)
        self.lbl_header_match.setText(f"AI Match: {int(round(overall_score))}%")

        # 5. Draw Skeleton & Highlights on Frame
        annotated_frame = PoseDrawer.draw_skeleton(frame, landmarks, posture_res, show_angles=True)

        # 6. Draw Ghost Reference Skeleton if enabled
        if self.ghost_mode and self.selected_pose:
            annotated_frame = PoseDrawer.draw_ghost_reference_skeleton(
                annotated_frame,
                self.selected_pose.get("name", ""),
                alpha=0.38,
            )

        # Render to QLabel
        pixmap = PoseDrawer.frame_to_pixmap(annotated_frame)
        self.lbl_video.setPixmap(pixmap.scaled(self.lbl_video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _on_ghost_mode_toggled(self, enabled: bool) -> None:
        self.ghost_mode = enabled

    def _on_finish_session(self) -> None:
        """Finishes active session, records to SQLite, and launches summary dialog."""
        self.is_practicing = False
        self.hold_timer.stop()
        self.btn_toggle_practice.setText("▶ Start Practice")
        self.btn_toggle_practice.setProperty("class", "btn_success")
        self.btn_toggle_practice.setStyleSheet("")
        self.btn_pause.setEnabled(False)

        if not self.score_samples:
            self.score_samples = [0.0]

        avg_score = float(sum(self.score_samples) / len(self.score_samples))
        final_score = float(self.score_samples[-1])

        # Determine most frequent mistake
        frequent_mistake = ""
        if self.mistake_frequencies:
            top_mistake_part = max(self.mistake_frequencies, key=self.mistake_frequencies.get)
            frequent_mistake = f"{top_mistake_part} alignment deviation was detected repeatedly."

        # Save to database
        if self.user and self.selected_pose:
            self.db.save_practice_session(
                user_id=self.user["id"],
                pose_id=self.selected_pose["id"],
                duration=max(1, self.elapsed_practice_time),
                average_score=avg_score,
                final_score=final_score,
                hold_duration=self.hold_time_seconds,
                corrections_count=self.corrections_count,
            )

        # Launch Summary Modal
        summary_dialog = SessionSummaryDialog(
            pose=self.selected_pose,
            duration=self.elapsed_practice_time,
            avg_score=avg_score,
            final_score=final_score,
            hold_duration=self.hold_time_seconds,
            corrections_count=self.corrections_count,
            frequent_mistake=frequent_mistake,
            parent=self,
        )
        summary_dialog.practice_again_requested.connect(lambda p: self.set_active_pose(p))
        summary_dialog.return_home_requested.connect(self.back_to_library.emit)
        summary_dialog.exec()
