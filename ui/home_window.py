"""
Home Dashboard Screen for AI Yoga Assistant.
Displays profile summary, daily recommendations, performance metrics, quick actions,
and recent practice session history.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import settings
from database.database import Database
from recommendation.recommender import PoseRecommender


class HomeWindow(QWidget):
    """Home Dashboard displaying stats, recommendations, and recent sessions."""

    # Navigation signals
    navigate_to_practice = Signal(dict)
    navigate_to_library = Signal()
    navigate_to_recommendations = Signal()
    navigate_to_custom_pose = Signal()
    navigate_to_progress = Signal()

    # Aliases for MainWindow signal connection
    start_practice_clicked = navigate_to_practice
    view_library_clicked = navigate_to_library
    view_progress_clicked = navigate_to_progress
    add_pose_clicked = navigate_to_custom_pose

    def __init__(self, db: Database, user: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user = user
        self.recommender = PoseRecommender(self.db)
        self._init_ui()

    def set_user(self, user: Dict[str, Any]) -> None:
        """Updates the active user profile and refreshes metrics."""
        self.user = user
        self.refresh_dashboard()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scrollable area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(32, 28, 32, 28)
        self.content_layout.setSpacing(24)

        # 1. Header Section
        self.header_layout = QVBoxLayout()
        self.welcome_label = QLabel("Welcome to AI Yoga Assistant")
        self.welcome_label.setProperty("class", "heading1")
        self.welcome_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #F8FAFC;")
        self.header_layout.addWidget(self.welcome_label)

        self.user_sub_label = QLabel("Track your posture in real time with AI computer vision.")
        self.user_sub_label.setStyleSheet(f"color: {settings.THEME['text_secondary']}; font-size: 14px;")
        self.header_layout.addWidget(self.user_sub_label)
        self.content_layout.addLayout(self.header_layout)

        # 2. Today's AI Recommendation Highlight Card
        self.recom_card = QFrame()
        self.recom_card.setProperty("class", "highlight_card")
        recom_layout = QHBoxLayout(self.recom_card)
        recom_layout.setContentsMargins(24, 20, 24, 20)
        recom_layout.setSpacing(20)

        recom_text_box = QVBoxLayout()
        recom_tag = QLabel("⭐ TODAY'S TOP AI RECOMMENDATION")
        recom_tag.setStyleSheet("color: #A78BFA; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        recom_text_box.addWidget(recom_tag)

        self.recom_title = QLabel("Warrior II (Virabhadrasana II)")
        self.recom_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF; margin-top: 4px;")
        recom_text_box.addWidget(self.recom_title)

        self.recom_desc = QLabel("Builds leg strength, expands lung capacity, and improves physical stamina.")
        self.recom_desc.setStyleSheet("color: #E2E8F0; font-size: 13px; margin-top: 2px;")
        self.recom_desc.setWordWrap(True)
        recom_text_box.addWidget(self.recom_desc)

        self.recom_reason = QLabel("🎯 Recommended based on your fitness goals")
        self.recom_reason.setStyleSheet("color: #38BDF8; font-size: 12px; font-style: italic; margin-top: 6px;")
        recom_text_box.addWidget(self.recom_reason)

        recom_layout.addLayout(recom_text_box, stretch=3)

        self.btn_practice_recom = QPushButton("Start Practice →")
        self.btn_practice_recom.setProperty("class", "btn_primary")
        self.btn_practice_recom.setStyleSheet("""
            background-color: #6366F1;
            color: #FFFFFF;
            border-radius: 10px;
            padding: 14px 28px;
            font-size: 15px;
            font-weight: bold;
        """)
        self.btn_practice_recom.clicked.connect(self._on_start_recommended_pose)
        recom_layout.addWidget(self.btn_practice_recom, alignment=Qt.AlignVCenter)
        self.content_layout.addWidget(self.recom_card)

        # 3. Performance Metrics Row (3 Cards)
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(16)

        # Metric 1: Average Score
        self.card_avg = QFrame()
        self.card_avg.setProperty("class", "card")
        l_avg = QVBoxLayout(self.card_avg)
        self.lbl_avg_score = QLabel("0.0%")
        self.lbl_avg_score.setProperty("class", "metric_value")
        self.lbl_avg_score.setStyleSheet("color: #10B981; font-size: 32px; font-weight: bold;")
        l_avg.addWidget(self.lbl_avg_score)
        lbl_avg_desc = QLabel("Average Accuracy Score")
        lbl_avg_desc.setProperty("class", "metric_label")
        l_avg.addWidget(lbl_avg_desc)
        metrics_grid.addWidget(self.card_avg, 0, 0)

        # Metric 2: Best Score
        self.card_best = QFrame()
        self.card_best.setProperty("class", "card")
        l_best = QVBoxLayout(self.card_best)
        self.lbl_best_score = QLabel("0.0%")
        self.lbl_best_score.setProperty("class", "metric_value")
        self.lbl_best_score.setStyleSheet("color: #38BDF8; font-size: 32px; font-weight: bold;")
        l_best.addWidget(self.lbl_best_score)
        lbl_best_desc = QLabel("Personal Best Score")
        lbl_best_desc.setProperty("class", "metric_label")
        l_best.addWidget(lbl_best_desc)
        metrics_grid.addWidget(self.card_best, 0, 1)

        # Metric 3: Total Sessions
        self.card_sessions = QFrame()
        self.card_sessions.setProperty("class", "card")
        l_sess = QVBoxLayout(self.card_sessions)
        self.lbl_sessions_count = QLabel("0")
        self.lbl_sessions_count.setProperty("class", "metric_value")
        self.lbl_sessions_count.setStyleSheet("color: #A78BFA; font-size: 32px; font-weight: bold;")
        l_sess.addWidget(self.lbl_sessions_count)
        lbl_sess_desc = QLabel("Total Completed Sessions")
        lbl_sess_desc.setProperty("class", "metric_label")
        l_sess.addWidget(lbl_sess_desc)
        metrics_grid.addWidget(self.card_sessions, 0, 2)

        self.content_layout.addLayout(metrics_grid)

        # 4. Quick Actions Row
        qa_label = QLabel("Quick Actions")
        qa_label.setProperty("class", "heading2")
        self.content_layout.addWidget(qa_label)

        qa_layout = QHBoxLayout()
        qa_layout.setSpacing(14)

        btn_qa_lib = QPushButton("📚 Browse Yoga Library")
        btn_qa_lib.setProperty("class", "btn_secondary")
        btn_qa_lib.clicked.connect(self.navigate_to_library.emit)
        qa_layout.addWidget(btn_qa_lib)

        btn_qa_recs = QPushButton("✨ AI Recommendations")
        btn_qa_recs.setProperty("class", "btn_secondary")
        btn_qa_recs.clicked.connect(self.navigate_to_recommendations.emit)
        qa_layout.addWidget(btn_qa_recs)

        btn_qa_custom = QPushButton("➕ Add Custom Pose")
        btn_qa_custom.setProperty("class", "btn_secondary")
        btn_qa_custom.clicked.connect(self.navigate_to_custom_pose.emit)
        qa_layout.addWidget(btn_qa_custom)

        btn_qa_prog = QPushButton("📈 View Progress & Trends")
        btn_qa_prog.setProperty("class", "btn_secondary")
        btn_qa_prog.clicked.connect(self.navigate_to_progress.emit)
        qa_layout.addWidget(btn_qa_prog)

        self.content_layout.addLayout(qa_layout)

        # 5. Recent Practice History Table
        history_header_row = QHBoxLayout()
        hist_title = QLabel("Recent Practice Sessions")
        hist_title.setProperty("class", "heading2")
        history_header_row.addWidget(hist_title)
        history_header_row.addStretch()

        btn_view_all = QPushButton("View Full History →")
        btn_view_all.setProperty("class", "btn_secondary")
        btn_view_all.clicked.connect(self.navigate_to_progress.emit)
        history_header_row.addWidget(btn_view_all)
        self.content_layout.addLayout(history_header_row)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Pose", "Category", "Avg Score", "Hold Time", "Date / Time"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setMinimumHeight(220)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.content_layout.addWidget(self.history_table)

        # 6. Safety Disclaimer Box
        disclaimer_card = QFrame()
        disclaimer_card.setProperty("class", "card")
        disclaimer_card.setStyleSheet("background-color: rgba(30, 41, 59, 0.4); border: 1px dashed #475569;")
        disc_layout = QHBoxLayout(disclaimer_card)
        disc_label = QLabel(f"⚠️ {settings.SAFETY_DISCLAIMER}")
        disc_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        disc_label.setWordWrap(True)
        disc_layout.addWidget(disc_label)
        self.content_layout.addWidget(disclaimer_card)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        self._active_top_pose: Optional[Dict[str, Any]] = None
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        """Refreshes profile greetings, recommendations, and analytics."""
        if not self.user:
            return

        user_name = self.user.get("name", "User")
        goal = self.user.get("goal", "General Fitness")
        exp = self.user.get("experience", "Beginner")

        self.welcome_label.setText(f"Welcome back, {user_name} 👋")
        self.user_sub_label.setText(f"Level: {exp}   •   Primary Goal: {goal}")

        # Fetch stats
        stats = self.db.get_user_stats(self.user["id"])
        self.lbl_avg_score.setText(f"{stats['overall_avg_score']}%")
        self.lbl_best_score.setText(f"{stats['best_score']}%")
        self.lbl_sessions_count.setText(str(stats["total_sessions"]))

        # Recommendation
        recs = self.recommender.get_recommendations(self.user["id"], limit=1)
        top_poses = recs.get("daily_routine") or recs.get("goal_based") or []
        if top_poses:
            self._active_top_pose = top_poses[0]
            self.recom_title.setText(f"{self._active_top_pose['name']} ({self._active_top_pose.get('sanskrit_name', '')})")
            self.recom_desc.setText(self._active_top_pose.get("description", ""))
            self.recom_reason.setText(f"🎯 Target Goal: {self._active_top_pose.get('goal', goal)}")

        # Practice History
        sessions = self.db.get_user_sessions(self.user["id"], limit=6)
        self.history_table.setRowCount(len(sessions))
        for row_idx, s in enumerate(sessions):
            self.history_table.setItem(row_idx, 0, QTableWidgetItem(s["pose_name"]))
            self.history_table.setItem(row_idx, 1, QTableWidgetItem(s.get("pose_category", "Standard")))
            
            score_item = QTableWidgetItem(f"{s['average_score']}%")
            if s["average_score"] >= 90:
                score_item.setForeground(Qt.green)
            elif s["average_score"] >= 80:
                score_item.setForeground(Qt.cyan)
            else:
                score_item.setForeground(Qt.yellow)
            self.history_table.setItem(row_idx, 2, score_item)

            self.history_table.setItem(row_idx, 3, QTableWidgetItem(f"{s['hold_duration']} sec"))
            self.history_table.setItem(row_idx, 4, QTableWidgetItem(str(s["created_at"])[:16]))

    def _on_start_recommended_pose(self) -> None:
        if self._active_top_pose:
            # Attach full rules
            pose_with_rules = self.db.get_pose_by_id(self._active_top_pose["id"])
            if pose_with_rules:
                self.navigate_to_practice.emit(pose_with_rules)
