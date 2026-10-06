"""
Session Summary Dialog for AI Yoga Assistant.
Presents post-practice analytics, hold durations, mistakes analysis,
and actionable coaching advice.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import settings


class SessionSummaryDialog(QDialog):
    """Post-practice summary dialog displaying session metrics and coaching tips."""

    practice_again_requested = Signal(dict)
    return_home_requested = Signal()

    def __init__(
        self,
        pose: Dict[str, Any],
        duration: int,
        avg_score: float,
        final_score: float,
        hold_duration: int,
        corrections_count: int,
        frequent_mistake: str,
        parent=None,
    ):
        super().__init__(parent)
        self.pose = pose
        self.duration = duration
        self.avg_score = avg_score
        self.final_score = final_score
        self.hold_duration = hold_duration
        self.corrections_count = corrections_count
        self.frequent_mistake = frequent_mistake

        self.setWindowTitle("Practice Complete - Session Summary")
        self.setMinimumSize(560, 620)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 28, 28, 28)
        main_layout.setSpacing(18)

        # Header
        top_box = QVBoxLayout()
        congrats_lbl = QLabel("🎉 Session Complete!")
        congrats_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #10B981;")
        top_box.addWidget(congrats_lbl)

        pose_lbl = QLabel(f"Pose: <b>{self.pose.get('name', 'Yoga Pose')}</b> ({self.pose.get('sanskrit_name', '')})")
        pose_lbl.setStyleSheet("font-size: 15px; color: #E2E8F0; margin-top: 4px;")
        top_box.addWidget(pose_lbl)
        main_layout.addLayout(top_box)

        # Score Card Highlight
        score_card = QFrame()
        score_card.setProperty("class", "card")
        score_card.setStyleSheet("""
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E1B4B, stop:1 #312E81);
            border: 1px solid #6366F1;
            border-radius: 12px;
            padding: 18px;
        """)
        s_layout = QHBoxLayout(score_card)

        s_left = QVBoxLayout()
        s_title = QLabel("FINAL ACCURACY SCORE")
        s_title.setStyleSheet("color: #A78BFA; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        s_left.addWidget(s_title)

        s_val = QLabel(f"{self.final_score:.1f}%")
        s_val.setStyleSheet("font-size: 42px; font-weight: bold; color: #FFFFFF;")
        s_left.addWidget(s_val)
        s_layout.addLayout(s_left)

        # Status badge
        if self.final_score >= 90:
            badge_text, badge_color = "🌟 EXCELLENT", "#10B981"
        elif self.final_score >= 80:
            badge_text, badge_color = "✓ GOOD POSTURE", "#06B6D4"
        elif self.final_score >= 70:
            badge_text, badge_color = "⚡ IMPROVEMENT SEEN", "#F59E0B"
        else:
            badge_text, badge_color = "🔄 NEEDS PRACTICE", "#EF4444"

        badge_lbl = QLabel(badge_text)
        badge_lbl.setStyleSheet(f"""
            background-color: rgba(255, 255, 255, 0.1);
            color: {badge_color};
            border: 2px solid {badge_color};
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            padding: 8px 16px;
        """)
        badge_lbl.setAlignment(Qt.AlignCenter)
        s_layout.addWidget(badge_lbl, alignment=Qt.AlignVCenter)
        main_layout.addWidget(score_card)

        # Metrics Breakdown Grid
        grid_card = QFrame()
        grid_card.setProperty("class", "card")
        g_layout = QGridLayout(grid_card)
        g_layout.setSpacing(14)

        # Avg Score
        g_layout.addWidget(QLabel("<b>Average Score:</b>"), 0, 0)
        lbl_avg = QLabel(f"{self.avg_score:.1f}%")
        lbl_avg.setStyleSheet("color: #38BDF8; font-weight: bold;")
        g_layout.addWidget(lbl_avg, 0, 1)

        # Total Duration
        g_layout.addWidget(QLabel("<b>Total Time:</b>"), 0, 2)
        g_layout.addWidget(QLabel(f"{self.duration} seconds"), 0, 3)

        # Hold Duration Achieved
        target_hold = self.pose.get("hold_duration", 20)
        g_layout.addWidget(QLabel("<b>Hold Duration:</b>"), 1, 0)
        lbl_hold = QLabel(f"{self.hold_duration} / {target_hold} sec")
        if self.hold_duration >= target_hold:
            lbl_hold.setStyleSheet("color: #10B981; font-weight: bold;")
        else:
            lbl_hold.setStyleSheet("color: #F59E0B; font-weight: bold;")
        g_layout.addWidget(lbl_hold, 1, 1)

        # Corrections Count
        g_layout.addWidget(QLabel("<b>Corrections:</b>"), 1, 2)
        g_layout.addWidget(QLabel(str(self.corrections_count)), 1, 3)

        main_layout.addWidget(grid_card)

        # Coaching Feedback & Common Mistake Card
        advice_card = QFrame()
        advice_card.setProperty("class", "card")
        adv_layout = QVBoxLayout(advice_card)

        adv_title = QLabel("💡 AI Coach Improvement Insight")
        adv_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F8FAFC;")
        adv_layout.addWidget(adv_title)

        if self.frequent_mistake:
            mistake_lbl = QLabel(f"• <b>Focus Area:</b> {self.frequent_mistake}")
            mistake_lbl.setStyleSheet("color: #F59E0B; margin-top: 4px;")
            mistake_lbl.setWordWrap(True)
            adv_layout.addWidget(mistake_lbl)
        else:
            good_lbl = QLabel("• Excellent balance and symmetry maintained throughout the session!")
            good_lbl.setStyleSheet("color: #10B981; margin-top: 4px;")
            adv_layout.addWidget(good_lbl)

        rec_tip = QLabel("• Consistency Tip: Repeat this pose 2-3 times to build muscle memory.")
        rec_tip.setStyleSheet("color: #94A3B8; margin-top: 2px;")
        adv_layout.addWidget(rec_tip)

        main_layout.addWidget(advice_card)

        # Bottom Button Bar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(12)

        btn_home = QPushButton("Done & Go to Home")
        btn_home.setProperty("class", "btn_secondary")
        btn_home.clicked.connect(self._on_home)
        btn_bar.addWidget(btn_home)

        btn_retry = QPushButton("Practice Again 🔄")
        btn_retry.setProperty("class", "btn_primary")
        btn_retry.clicked.connect(self._on_retry)
        btn_bar.addWidget(btn_retry)

        main_layout.addLayout(btn_bar)

    def _on_home(self) -> None:
        self.return_home_requested.emit()
        self.accept()

    def _on_retry(self) -> None:
        self.practice_again_requested.emit(self.pose)
        self.accept()
