"""
AI Yoga Pose Recommendation Screen.
Displays personalized daily routines, goal-aligned recommendations,
weakness-targeted practice suggestions, and coaching insights.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from config import settings
from database.database import Database
from recommendation.recommender import PoseRecommender
from ui.yoga_library import PoseCard


class RecommendationWindow(QWidget):
    """Personalized Yoga Recommendation View."""

    start_practice = Signal(dict)
    practice_pose_selected = start_practice

    def __init__(self, db: Database, user: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user = user
        self.recommender = PoseRecommender(self.db)
        self._init_ui()

    def set_user(self, user: Dict[str, Any]) -> None:
        self.user = user
        self.refresh_recommendations()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(20)

        # Header Title
        title_box = QVBoxLayout()
        title_lbl = QLabel("✨ Personalized AI Recommendations")
        title_lbl.setProperty("class", "heading1")
        title_lbl.setStyleSheet("font-size: 26px; font-weight: bold; color: #F8FAFC;")
        title_box.addWidget(title_lbl)

        self.sub_lbl = QLabel("AI-curated recommendations based on your fitness goals, experience level, and past practice scores.")
        self.sub_lbl.setStyleSheet(f"color: {settings.THEME['text_secondary']}; font-size: 13px;")
        title_box.addWidget(self.sub_lbl)
        main_layout.addLayout(title_box)

        # Scroll Area for dynamic recommendation sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 8, 0, 8)
        self.content_layout.setSpacing(24)

        # AI Insights Banner Card
        self.insights_card = QFrame()
        self.insights_card.setProperty("class", "highlight_card")
        self.ins_layout = QVBoxLayout(self.insights_card)
        self.ins_title = QLabel("💡 AI COACH INSIGHT")
        self.ins_title.setStyleSheet("color: #A78BFA; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        self.ins_layout.addWidget(self.ins_title)
        self.lbl_insights = QLabel("Loading insights...")
        self.lbl_insights.setStyleSheet("color: #FFFFFF; font-size: 14px; margin-top: 4px;")
        self.lbl_insights.setWordWrap(True)
        self.ins_layout.addWidget(self.lbl_insights)
        self.content_layout.addWidget(self.insights_card)

        # 1. Daily Balanced Routine Section
        sec1_title = QLabel("📅 Recommended Daily Routine (Warmup → Peak → Cooldown)")
        sec1_title.setProperty("class", "heading2")
        self.content_layout.addWidget(sec1_title)
        self.grid_routine = QGridLayout()
        self.grid_routine.setSpacing(16)
        self.content_layout.addLayout(self.grid_routine)

        # 2. Goal-Based Section
        self.lbl_goal_title = QLabel("🎯 Aligned with Your Fitness Goal")
        self.lbl_goal_title.setProperty("class", "heading2")
        self.content_layout.addWidget(self.lbl_goal_title)
        self.grid_goal = QGridLayout()
        self.grid_goal.setSpacing(16)
        self.content_layout.addLayout(self.grid_goal)

        # 3. Weakness-Targeted Practice Section
        self.lbl_weakness_title = QLabel("⚡ Focus & Alignment Refinement (Weakness-Targeted)")
        self.lbl_weakness_title.setProperty("class", "heading2")
        self.content_layout.addWidget(self.lbl_weakness_title)
        self.grid_weakness = QGridLayout()
        self.grid_weakness.setSpacing(16)
        self.content_layout.addLayout(self.grid_weakness)

        scroll.setWidget(self.content_widget)
        main_layout.addWidget(scroll)

        self.refresh_recommendations()

    def _clear_grid(self, grid: QGridLayout) -> None:
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def refresh_recommendations(self) -> None:
        if not self.user:
            return

        user_id = self.user["id"]
        goal = self.user.get("goal", "General Fitness")
        exp = self.user.get("experience", "Beginner")

        self.lbl_goal_title.setText(f"🎯 Recommended for Your Goal: {goal}")

        recs = self.recommender.get_recommendations(user_id, limit=3)

        # Update Insights
        insights = recs.get("insights", [])
        if insights:
            self.lbl_insights.setText(" • " + "\n • ".join(insights))

        # Clear Grids
        self._clear_grid(self.grid_routine)
        self._clear_grid(self.grid_goal)
        self._clear_grid(self.grid_weakness)

        # Populate Routine Grid
        routine = recs.get("daily_routine", [])
        for idx, pose in enumerate(routine):
            card = PoseCard(pose)
            card.start_practice.connect(self._on_start_practice)
            self.grid_routine.addWidget(card, 0, idx)

        # Populate Goal Grid
        goal_poses = recs.get("goal_based", [])
        for idx, pose in enumerate(goal_poses):
            card = PoseCard(pose)
            card.start_practice.connect(self._on_start_practice)
            self.grid_goal.addWidget(card, 0, idx)

        # Populate Weakness / Practice More Grid
        practice_more = recs.get("practice_more", [])
        if practice_more:
            for idx, pose in enumerate(practice_more):
                card = PoseCard(pose)
                card.start_practice.connect(self._on_start_practice)
                self.grid_weakness.addWidget(card, 0, idx)
        else:
            good_lbl = QLabel("No poses need immediate correction. Keep up the high accuracy!")
            good_lbl.setStyleSheet("color: #10B981; font-style: italic; margin: 10px;")
            self.grid_weakness.addWidget(good_lbl, 0, 0)

    def _on_start_practice(self, pose: Dict[str, Any]) -> None:
        pose_with_rules = self.db.get_pose_by_id(pose["id"]) or pose
        self.start_practice.emit(pose_with_rules)
