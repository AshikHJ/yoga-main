"""
Reference Pose Panel for KI.AI Live Practice Screen.
Provides a dedicated visual reference panel showing:
  - Pose Name, Sanskrit Name, and verified 2D anatomical figure.
  - Key alignment checkpoints (✓ Head, ✓ Shoulders, ✓ Legs, etc.).
  - Side-by-side 'Compare With Reference' (REFERENCE vs YOUR POSE with % match).
  - Ghost Reference skeleton toggle.
  - Learning Mode (Beginner) and Minimal Mode (Advanced) controls.
  - Size controls (− ○ +), Pinning, and Position selection.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from config import settings
from vision.reference_helper import ReferenceHelper


class ReferencePosePanel(QFrame):
    """Interactive Reference Pose & Alignment Comparison Panel."""

    ghost_mode_toggled = Signal(bool)
    size_mode_changed = Signal(str)  # 'minimal', 'normal', 'learning'
    position_changed = Signal(str)   # 'right', 'left', 'floating'

    def __init__(self, pose: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.pose = pose or {}
        self.size_mode = "normal"  # 'minimal', 'normal', 'learning'
        self.is_pinned = True
        self.compare_enabled = True
        self.ghost_enabled = False

        self.setProperty("class", "card")
        self.setStyleSheet(f"""
            QFrame.card {{
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 4px;
            }}
        """)

        self._init_ui()
        if self.pose:
            self.set_pose(self.pose)

    def _init_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(10)

        # ==========================================
        # 1. Header with Controls & Transition Banner
        # ==========================================
        header_row = QHBoxLayout()
        ref_title_box = QVBoxLayout()
        
        ref_badge = QLabel("REFERENCE POSE")
        ref_badge.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        ref_title_box.addWidget(ref_badge)

        self.lbl_pose_name = QLabel("Vrikshasana")
        self.lbl_pose_name.setStyleSheet("color: #FFFFFF; font-size: 17px; font-weight: 800;")
        ref_title_box.addWidget(self.lbl_pose_name)

        self.lbl_sanskrit = QLabel("Tree Pose")
        self.lbl_sanskrit.setStyleSheet("color: #94A3B8; font-size: 12px; font-style: italic;")
        ref_title_box.addWidget(self.lbl_sanskrit)

        header_row.addLayout(ref_title_box)
        header_row.addStretch()

        # Mode Selector Buttons (Learning vs Minimal)
        mode_btn_row = QHBoxLayout()
        mode_btn_row.setSpacing(4)

        self.btn_size_minus = QPushButton("−")
        self.btn_size_minus.setFixedSize(26, 26)
        self.btn_size_minus.setToolTip("Minimal Mode (Advanced)")
        self.btn_size_minus.clicked.connect(lambda: self.set_size_mode("minimal"))
        mode_btn_row.addWidget(self.btn_size_minus)

        self.btn_size_norm = QPushButton("○")
        self.btn_size_norm.setFixedSize(26, 26)
        self.btn_size_norm.setToolTip("Normal Reference Mode")
        self.btn_size_norm.clicked.connect(lambda: self.set_size_mode("normal"))
        mode_btn_row.addWidget(self.btn_size_norm)

        self.btn_size_plus = QPushButton("+")
        self.btn_size_plus.setFixedSize(26, 26)
        self.btn_size_plus.setToolTip("Learning Mode (Beginner)")
        self.btn_size_plus.clicked.connect(lambda: self.set_size_mode("learning"))
        mode_btn_row.addWidget(self.btn_size_plus)

        header_row.addLayout(mode_btn_row)
        self.main_layout.addLayout(header_row)

        # Transition Notification Banner
        self.lbl_transition = QLabel("Next Pose → Reference Updated ✨")
        self.lbl_transition.setAlignment(Qt.AlignCenter)
        self.lbl_transition.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.2);
            color: #34D399;
            border: 1px solid #10B981;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 700;
        """)
        self.lbl_transition.setVisible(False)
        self.main_layout.addWidget(self.lbl_transition)

        # ==========================================
        # 2. Human Pose Visual Figure
        # ==========================================
        self.figure_frame = QFrame()
        self.figure_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0B1120, stop:1 #064E3B);
                border: 1.5px solid #10B981;
                border-radius: 10px;
            }
        """)
        fig_layout = QVBoxLayout(self.figure_frame)
        fig_layout.setContentsMargins(8, 8, 8, 8)
        fig_layout.setAlignment(Qt.AlignCenter)

        self.lbl_figure = QLabel()
        self.lbl_figure.setAlignment(Qt.AlignCenter)
        fig_layout.addWidget(self.lbl_figure)

        self.main_layout.addWidget(self.figure_frame)

        # ==========================================
        # 3. Alignment Checkpoints Card
        # ==========================================
        self.checkpoints_frame = QFrame()
        self.checkpoints_frame.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        self.chk_layout = QVBoxLayout(self.checkpoints_frame)
        self.chk_layout.setContentsMargins(8, 8, 8, 8)
        self.chk_layout.setSpacing(4)

        chk_header = QLabel("KEY ALIGNMENT CUES")
        chk_header.setStyleSheet("color: #38BDF8; font-size: 10px; font-weight: 800; letter-spacing: 0.5px;")
        self.chk_layout.addWidget(chk_header)

        self.checkpoints_container = QVBoxLayout()
        self.checkpoints_container.setSpacing(3)
        self.chk_layout.addLayout(self.checkpoints_container)

        self.main_layout.addWidget(self.checkpoints_frame)

        # ==========================================
        # 4. Compare With Reference Section
        # ==========================================
        self.compare_frame = QFrame()
        self.compare_frame.setStyleSheet("""
            QFrame {
                background-color: #131D2E;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        comp_layout = QVBoxLayout(self.compare_frame)
        comp_layout.setContentsMargins(8, 8, 8, 8)
        comp_layout.setSpacing(6)

        comp_top_row = QHBoxLayout()
        lbl_comp_title = QLabel("REFERENCE vs YOUR POSE")
        lbl_comp_title.setStyleSheet("color: #E2E8F0; font-size: 10.5px; font-weight: 800;")
        comp_top_row.addWidget(lbl_comp_title)
        comp_top_row.addStretch()

        self.lbl_match_score = QLabel("94% Match")
        self.lbl_match_score.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.2);
            color: #10B981;
            border: 1px solid #10B981;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 10px;
            font-weight: 800;
        """)
        comp_top_row.addWidget(self.lbl_match_score)
        comp_layout.addLayout(comp_top_top := comp_top_row)

        self.diff_list_layout = QVBoxLayout()
        self.diff_list_layout.setSpacing(2)
        comp_layout.addLayout(self.diff_list_layout)

        self.main_layout.addWidget(self.compare_frame)

        # ==========================================
        # 5. Interactive Feature Toggles (Ghost & Pin)
        # ==========================================
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(8)

        self.chk_ghost = QCheckBox("👤 Ghost Reference")
        self.chk_ghost.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 600;")
        self.chk_ghost.toggled.connect(self._on_ghost_toggled)
        toggle_row.addWidget(self.chk_ghost)

        self.chk_compare = QCheckBox("⚖ Compare")
        self.chk_compare.setChecked(True)
        self.chk_compare.setStyleSheet("color: #E2E8F0; font-size: 11px; font-weight: 600;")
        self.chk_compare.toggled.connect(self._on_compare_toggled)
        toggle_row.addWidget(self.chk_compare)

        self.chk_pin = QCheckBox("📌 Pin")
        self.chk_pin.setChecked(True)
        self.chk_pin.setStyleSheet("color: #E2E8F0; font-size: 11px; font-weight: 600;")
        self.chk_pin.toggled.connect(lambda v: setattr(self, "is_pinned", v))
        toggle_row.addWidget(self.chk_pin)

        toggle_row.addStretch()
        self.main_layout.addLayout(toggle_row)

        self.main_layout.addStretch()

    def set_pose(self, pose: Dict[str, Any]) -> None:
        """Updates the reference pose with smooth transition."""
        self.pose = pose
        self.lbl_pose_name.setText(pose.get("name", "Pose"))
        self.lbl_sanskrit.setText(pose.get("sanskrit_name", ""))

        self._update_figure_pixmap()
        self._update_checkpoints()

        # Trigger transition animation banner
        self.lbl_transition.setText(f"Next Pose → {pose.get('name', 'Pose')} Updated ✨")
        self.lbl_transition.setVisible(True)
        QTimer.singleShot(2500, lambda: self.lbl_transition.setVisible(False))

    def _update_figure_pixmap(self) -> None:
        """Renders the exact pose SVG or silhouette figure based on size mode."""
        if self.size_mode == "minimal":
            size = (60, 60)
            self.figure_frame.setFixedHeight(75)
        elif self.size_mode == "learning":
            size = (180, 180)
            self.figure_frame.setFixedHeight(200)
        else:
            size = (120, 120)
            self.figure_frame.setFixedHeight(140)

        pix = ReferenceHelper.get_pose_figure_pixmap(self.pose, size=size)
        self.lbl_figure.setPixmap(pix)

    def _update_checkpoints(self) -> None:
        """Builds alignment cues from pose data."""
        while self.checkpoints_container.count():
            item = self.checkpoints_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        name = self.pose.get("name", "").lower()
        cues = []
        if "tree" in name or "vrikshasana" in name:
            cues = [
                "✓ Head centered & gaze fixed ahead",
                "✓ Shoulders relaxed & level",
                "✓ Standing leg straight & grounded",
                "✓ Raised knee open outward 90°",
                "✓ Hands pressed in Anjali Mudra",
            ]
        elif "warrior" in name or "virabhadrasana" in name:
            cues = [
                "✓ Torso vertical & hips squared",
                "✓ Front knee bent directly over ankle (90°)",
                "✓ Back leg extended straight & locked",
                "✓ Arms parallel to floor reaching outward",
                "✓ Gaze directed over front fingertips",
            ]
        elif "triangle" in name or "trikonasana" in name:
            cues = [
                "✓ Spine elongated horizontally",
                "✓ Both legs straight without hyperextension",
                "✓ Upper arm reaching vertically to sky",
                "✓ Chest turned upward & open",
            ]
        elif "cobra" in name or "bhujangasana" in name:
            cues = [
                "✓ Chest lifted forward & shoulders back",
                "✓ Elbows slightly bent hugging ribs",
                "✓ Tops of feet pressed firmly to mat",
                "✓ Neck neutral without excessive strain",
            ]
        elif "downward" in name or "adho" in name:
            cues = [
                "✓ Hips pressed high forming inverted 'V'",
                "✓ Spine lengthened with flat back",
                "✓ Heels reaching toward floor",
                "✓ Hands shoulder-width pressing evenly",
            ]
        else:
            # Generate from instructions or generic posture checkpoints
            instructions = self.pose.get("instructions", [])
            if isinstance(instructions, list) and instructions:
                cues = [f"✓ {step}" for step in instructions[:4]]
            else:
                cues = [
                    "✓ Spine upright and aligned",
                    "✓ Shoulders level and relaxed",
                    "✓ Core gently engaged",
                    "✓ Steady, continuous rhythmic breathing",
                ]

        for cue in cues:
            lbl = QLabel(cue)
            lbl.setStyleSheet("color: #E2E8F0; font-size: 11px; line-height: 1.3;")
            lbl.setWordWrap(True)
            self.checkpoints_container.addWidget(lbl)

    def update_live_comparison(self, posture_data: Dict[str, Any]) -> None:
        """Updates the real-time REFERENCE vs YOUR POSE joint differences."""
        if not self.compare_enabled:
            return

        score = Math_round = int(round(posture_data.get("overall_score", 0)))
        self.lbl_match_score.setText(f"{score}% Match")
        if score >= 85:
            self.lbl_match_score.setStyleSheet("background: rgba(16,185,129,0.2); color: #10B981; border: 1px solid #10B981; border-radius: 4px; padding: 2px 6px; font-weight: bold;")
        elif score >= 70:
            self.lbl_match_score.setStyleSheet("background: rgba(245,158,11,0.2); color: #F59E0B; border: 1px solid #F59E0B; border-radius: 4px; padding: 2px 6px; font-weight: bold;")
        else:
            self.lbl_match_score.setStyleSheet("background: rgba(239,68,68,0.2); color: #EF4444; border: 1px solid #EF4444; border-radius: 4px; padding: 2px 6px; font-weight: bold;")

        # Clear previous diff items
        while self.diff_list_layout.count():
            item = self.diff_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        joint_results = posture_data.get("joint_results", [])
        for j in joint_results[:4]:  # Show top 4 key joints
            name = j.get("formatted_name") or j.get("joint_name", "")
            code = j.get("status_code", "CORRECT")
            diff = abs(j.get("deviation", 0))

            if code == "CORRECT":
                dot = "🟢"
                txt = f"{name} — Correct"
                color = "#10B981"
            elif code == "WARNING":
                dot = "🟡"
                txt = f"{name} — Adjust {int(diff)}°"
                color = "#F59E0B"
            else:
                dot = "🔴"
                txt = f"{name} — Adjust {int(diff)}°"
                color = "#EF4444"

            row = QLabel(f"{dot} {txt}")
            row.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 600;")
            self.diff_list_layout.addWidget(row)

    def set_size_mode(self, mode: str) -> None:
        """Switches between 'minimal' (Advanced), 'normal', and 'learning' (Beginner)."""
        self.size_mode = mode
        if mode == "minimal":
            self.checkpoints_frame.setVisible(False)
            self.compare_frame.setVisible(False)
            self.setFixedWidth(160)
        elif mode == "learning":
            self.checkpoints_frame.setVisible(True)
            self.compare_frame.setVisible(True)
            self.setFixedWidth(300)
        else:  # normal
            self.checkpoints_frame.setVisible(True)
            self.compare_frame.setVisible(True)
            self.setFixedWidth(240)

        self._update_figure_pixmap()
        self.size_mode_changed.emit(mode)

    def _on_ghost_toggled(self, checked: bool) -> None:
        self.ghost_enabled = checked
        self.ghost_mode_toggled.emit(checked)

    def _on_compare_toggled(self, checked: bool) -> None:
        self.compare_enabled = checked
        self.compare_frame.setVisible(checked)
