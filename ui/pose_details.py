"""
Pose Details Modal Dialog for KI.AI — AI-Powered Yoga & Posture Intelligence.
Shows full instructions, benefits, precautions, target joint angles,
pose-specific reference figures, 3-mode Reference Assist, and a Start Practice button.
"""

from typing import Any, Dict, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from config import settings
from ui.reference_assist import ReferenceAssistWidget
from vision.reference_helper import ReferenceHelper


class PoseDetailsDialog(QDialog):
    """Detailed view for a specific yoga pose with Reference Assist & Pose Figures."""

    start_practice_clicked = Signal(dict)

    def __init__(self, pose: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.pose = pose
        self.setWindowTitle(f"KI.AI — {pose.get('name', 'Pose')} Details")
        self.setMinimumSize(740, 760)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # ==========================================
        # 1. Header with Pose Figure & Names
        # ==========================================
        header_card = QFrame()
        header_card.setProperty("class", "card")
        header_card.setStyleSheet("background-color: #111827; border: 1px solid #1E293B; border-radius: 12px; padding: 14px;")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(8, 8, 8, 8)
        h_layout.setSpacing(14)

        # Pose Figure Icon
        figure_lbl = QLabel()
        figure_lbl.setFixedSize(60, 60)
        figure_lbl.setAlignment(Qt.AlignCenter)
        figure_lbl.setStyleSheet("""
            QLabel {
                background-color: rgba(15, 23, 42, 0.9);
                border: 2px solid #10B981;
                border-radius: 10px;
                padding: 4px;
            }
        """)
        pix = ReferenceHelper.get_pose_figure_pixmap(self.pose, size=(50, 50))
        figure_lbl.setPixmap(pix)
        h_layout.addWidget(figure_lbl)

        # Title Info
        title_box = QVBoxLayout()
        name_lbl = QLabel(self.pose.get("name", "Pose Name"))
        name_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        title_box.addWidget(name_lbl)

        sanskrit_lbl = QLabel(self.pose.get("sanskrit_name", ""))
        sanskrit_lbl.setStyleSheet(f"font-size: 13px; color: {settings.THEME['primary']}; font-weight: 600;")
        title_box.addWidget(sanskrit_lbl)

        # Badges Row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(6)

        diff = self.pose.get("difficulty", "Beginner")
        diff_badge = QLabel(diff.upper())
        diff_badge.setStyleSheet(f"""
            background-color: rgba(15, 23, 42, 0.85);
            color: {'#10B981' if diff == 'Beginner' else '#F59E0B' if diff == 'Intermediate' else '#EF4444'};
            border: 1px solid {'#10B981' if diff == 'Beginner' else '#F59E0B' if diff == 'Intermediate' else '#EF4444'};
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 10px;
            font-weight: bold;
        """)
        badge_row.addWidget(diff_badge)

        cat_badge = QLabel(f"🏷️ {self.pose.get('category', 'General')}")
        cat_badge.setStyleSheet("background-color: #0F172A; border: 1px solid #334155; border-radius: 4px; padding: 2px 6px; font-size: 10px; color: #94A3B8;")
        badge_row.addWidget(cat_badge)

        goal_badge = QLabel(f"🎯 {self.pose.get('goal', 'Fitness')}")
        goal_badge.setStyleSheet("background-color: #0F172A; border: 1px solid #334155; border-radius: 4px; padding: 2px 6px; font-size: 10px; color: #94A3B8;")
        badge_row.addWidget(goal_badge)

        badge_row.addStretch()
        title_box.addLayout(badge_row)
        h_layout.addLayout(title_box)

        layout.addWidget(header_card)

        # ==========================================
        # 2. Reference Assist (PHOTO / SKELETON / OVERLAY)
        # ==========================================
        ref_assist = ReferenceAssistWidget(self.pose)
        layout.addWidget(ref_assist)

        # ==========================================
        # 3. Overview Description
        # ==========================================
        desc_card = QFrame()
        desc_card.setProperty("class", "card")
        d_layout = QVBoxLayout(desc_card)
        d_title = QLabel("Overview")
        d_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        d_layout.addWidget(d_title)

        d_text = QLabel(self.pose.get("description", "No description available."))
        d_text.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 1.4;")
        d_text.setWordWrap(True)
        d_layout.addWidget(d_text)
        layout.addWidget(desc_card)

        # ==========================================
        # 4. Instructions
        # ==========================================
        inst_card = QFrame()
        inst_card.setProperty("class", "card")
        i_layout = QVBoxLayout(inst_card)
        i_title = QLabel("Step-by-Step Instructions")
        i_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        i_layout.addWidget(i_title)

        instructions = self.pose.get("instructions", [])
        if isinstance(instructions, list) and instructions:
            for idx, step in enumerate(instructions, 1):
                step_lbl = QLabel(f"<b>{idx}.</b>  {step}")
                step_lbl.setStyleSheet("color: #E2E8F0; font-size: 12px; margin-bottom: 3px;")
                step_lbl.setWordWrap(True)
                i_layout.addWidget(step_lbl)
        layout.addWidget(inst_card)

        # ==========================================
        # 5. Benefits & Precautions
        # ==========================================
        ben_card = QFrame()
        ben_card.setProperty("class", "card")
        b_layout = QVBoxLayout(ben_card)
        b_title = QLabel("Key Health Benefits")
        b_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        b_layout.addWidget(b_title)

        benefits = self.pose.get("benefits", [])
        if isinstance(benefits, list) and benefits:
            for b in benefits:
                b_lbl = QLabel(f"✓  {b}")
                b_lbl.setStyleSheet("color: #10B981; font-size: 12px; margin-bottom: 2px;")
                b_lbl.setWordWrap(True)
                b_layout.addWidget(b_lbl)
        layout.addWidget(ben_card)

        precautions = self.pose.get("precautions")
        if precautions:
            p_card = QFrame()
            p_card.setProperty("class", "card")
            p_card.setStyleSheet("border-left: 4px solid #F59E0B; background-color: #1E293B; padding: 10px;")
            p_layout = QVBoxLayout(p_card)
            p_title = QLabel("⚠️ Safety & Precautions")
            p_title.setStyleSheet("color: #F59E0B; font-weight: bold; font-size: 12px;")
            p_layout.addWidget(p_title)
            p_text = QLabel(precautions)
            p_text.setStyleSheet("color: #E2E8F0; font-size: 12px;")
            p_text.setWordWrap(True)
            p_layout.addWidget(p_text)
            layout.addWidget(p_card)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # ==========================================
        # 6. Bottom Action Bar
        # ==========================================
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        btn_close = QPushButton("Close")
        btn_close.setProperty("class", "btn_secondary")
        btn_close.setFixedHeight(40)
        btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(btn_close)

        btn_practice = QPushButton("▶ Start Practice")
        btn_practice.setProperty("class", "btn_primary")
        btn_practice.setFixedHeight(40)
        btn_practice.clicked.connect(self._on_start_practice)
        btn_bar.addWidget(btn_practice)

        main_layout.addLayout(btn_bar)

    def _on_start_practice(self) -> None:
        self.accept()
        self.start_practice_clicked.emit(self.pose)
