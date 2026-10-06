"""
Progress & Analytics Screen with Embedded Matplotlib Charts.
Visualizes posture score trends over time, pose-wise accuracy comparisons,
category distribution, and complete practice history.
"""

from typing import Any, Dict, List, Optional
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import settings
from database.database import Database


class MatplotlibWidget(QWidget):
    """Reusable QWidget wrapper around a styled Matplotlib FigureCanvas."""

    def __init__(self, parent=None, width=5, height=3, dpi=100):
        super().__init__(parent)
        self.figure = Figure(figsize=(width, height), dpi=dpi, facecolor="#1E293B")
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)


class ProgressWindow(QWidget):
    """Analytics and progress visualization dashboard."""

    def __init__(self, db: Database, user: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user = user
        self._init_ui()

    def set_user(self, user: Dict[str, Any]) -> None:
        self.user = user
        self.refresh_analytics()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(20)

        # Header Title
        title_box = QVBoxLayout()
        title_lbl = QLabel("📈 Progress & Practice Analytics")
        title_lbl.setProperty("class", "heading1")
        title_lbl.setStyleSheet("font-size: 26px; font-weight: bold; color: #F8FAFC;")
        title_box.addWidget(title_lbl)

        sub_lbl = QLabel("Detailed performance insights, posture accuracy progression over time, and pose comparisons.")
        sub_lbl.setStyleSheet(f"color: {settings.THEME['text_secondary']}; font-size: 13px;")
        title_box.addWidget(sub_lbl)
        main_layout.addLayout(title_box)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 8, 0, 8)
        self.content_layout.setSpacing(24)

        # Top Stats Summary Cards (4 Cards)
        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)

        # Card 1: Total Practice Time
        self.card_time = self._create_stat_card("Total Practice Time", "0 min", "#38BDF8")
        stats_grid.addWidget(self.card_time, 0, 0)

        # Card 2: Total Hold Time
        self.card_hold = self._create_stat_card("Total Hold Time", "0 min", "#10B981")
        stats_grid.addWidget(self.card_hold, 0, 1)

        # Card 3: Overall Average
        self.card_avg = self._create_stat_card("Overall Accuracy", "0.0%", "#6366F1")
        stats_grid.addWidget(self.card_avg, 0, 2)

        # Card 4: Most Practiced
        self.card_most = self._create_stat_card("Most Practiced Pose", "None", "#A78BFA")
        stats_grid.addWidget(self.card_most, 0, 3)

        self.content_layout.addLayout(stats_grid)

        # Matplotlib Charts Section
        charts_row = QHBoxLayout()
        charts_row.setSpacing(20)

        # Chart 1: Score Progression Over Time
        c1_card = QFrame()
        c1_card.setProperty("class", "card")
        c1_layout = QVBoxLayout(c1_card)
        c1_title = QLabel("📊 Accuracy Score Progression (Over Time)")
        c1_title.setProperty("class", "heading3")
        c1_layout.addWidget(c1_title)

        self.chart_timeline = MatplotlibWidget(self, width=5.5, height=3.5)
        c1_layout.addWidget(self.chart_timeline)
        charts_row.addWidget(c1_card, stretch=1)

        # Chart 2: Pose-Wise Accuracy Breakdown
        c2_card = QFrame()
        c2_card.setProperty("class", "card")
        c2_layout = QVBoxLayout(c2_card)
        c2_title = QLabel("🏆 Pose-Wise Average Score Comparison")
        c2_title.setProperty("class", "heading3")
        c2_layout.addWidget(c2_title)

        self.chart_poses = MatplotlibWidget(self, width=5.5, height=3.5)
        c2_layout.addWidget(self.chart_poses)
        charts_row.addWidget(c2_card, stretch=1)

        self.content_layout.addLayout(charts_row)

        # Full Practice History Table
        hist_card = QFrame()
        hist_card.setProperty("class", "card")
        h_layout = QVBoxLayout(hist_card)

        h_title = QLabel("📜 Complete Practice History")
        h_title.setProperty("class", "heading3")
        h_layout.addWidget(h_title)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Session ID", "Pose Name", "Category", "Avg Score", "Hold Time", "Recorded At"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setMinimumHeight(240)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        h_layout.addWidget(self.history_table)

        self.content_layout.addWidget(hist_card)

        scroll.setWidget(self.content)
        main_layout.addWidget(scroll)

        self.refresh_analytics()

    def _create_stat_card(self, label: str, default_val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)

        val_lbl = QLabel(default_val)
        val_lbl.setObjectName(f"val_{label.replace(' ', '_')}")
        val_lbl.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {color_hex};")
        layout.addWidget(val_lbl)

        txt_lbl = QLabel(label.upper())
        txt_lbl.setStyleSheet("font-size: 11px; color: #64748B; font-weight: bold; letter-spacing: 0.5px;")
        layout.addWidget(txt_lbl)
        return card

    def refresh_analytics(self) -> None:
        """Fetches fresh data and renders Matplotlib charts and history."""
        if not self.user:
            return

        user_id = self.user["id"]
        stats = self.db.get_user_stats(user_id)

        # Update Stat Cards
        lbl_time = self.card_time.findChild(QLabel, "val_Total_Practice_Time")
        if lbl_time:
            mins = stats["total_practice_time"] // 60
            secs = stats["total_practice_time"] % 60
            lbl_time.setText(f"{mins}m {secs}s")

        lbl_hold = self.card_hold.findChild(QLabel, "val_Total_Hold_Time")
        if lbl_hold:
            lbl_hold.setText(f"{stats['total_hold_time']} sec")

        lbl_avg = self.card_avg.findChild(QLabel, "val_Overall_Accuracy")
        if lbl_avg:
            lbl_avg.setText(f"{stats['overall_avg_score']}%")

        lbl_most = self.card_most.findChild(QLabel, "val_Most_Practiced_Pose")
        if lbl_most:
            lbl_most.setText(stats["most_practiced_pose"][:18])

        # Render Chart 1: Timeline
        timeline_data = self.db.get_score_history_timeline(user_id, limit=15)
        self._plot_timeline(timeline_data)

        # Render Chart 2: Pose Breakdown
        pose_breakdown = self.db.get_pose_performance_breakdown(user_id)
        self._plot_pose_breakdown(pose_breakdown)

        # Render History Table
        sessions = self.db.get_user_sessions(user_id, limit=50)
        self.history_table.setRowCount(len(sessions))
        for r_idx, s in enumerate(sessions):
            self.history_table.setItem(r_idx, 0, QTableWidgetItem(f"#{s['id']}"))
            self.history_table.setItem(r_idx, 1, QTableWidgetItem(s["pose_name"]))
            self.history_table.setItem(r_idx, 2, QTableWidgetItem(s.get("pose_category", "Standard")))
            
            score_item = QTableWidgetItem(f"{s['average_score']}%")
            if s["average_score"] >= 90:
                score_item.setForeground(Qt.green)
            elif s["average_score"] >= 80:
                score_item.setForeground(Qt.cyan)
            else:
                score_item.setForeground(Qt.yellow)
            self.history_table.setItem(r_idx, 3, score_item)

            self.history_table.setItem(r_idx, 4, QTableWidgetItem(f"{s['hold_duration']}s"))
            self.history_table.setItem(r_idx, 5, QTableWidgetItem(str(s["created_at"])[:16]))

    def _plot_timeline(self, data: List[Dict[str, Any]]) -> None:
        fig = self.chart_timeline.figure
        fig.clear()
        ax = fig.add_subplot(111)
        ax.set_facecolor("#1E293B")

        if not data:
            ax.text(0.5, 0.5, "No sessions recorded yet.\nStart practicing to see score trends!",
                    ha='center', va='center', color='#94A3B8', transform=ax.transAxes)
            self.chart_timeline.canvas.draw()
            return

        x = list(range(1, len(data) + 1))
        y = [d["average_score"] for d in data]

        ax.plot(x, y, color="#6366F1", marker="o", linewidth=2.5, markersize=6, label="Avg Score")
        ax.fill_between(x, y, color="#6366F1", alpha=0.2)

        # Target threshold line at 80%
        ax.axhline(80, color="#10B981", linestyle="--", alpha=0.6, label="Target (80%)")

        ax.set_ylim(0, 105)
        ax.set_xlabel("Practice Session #", color="#94A3B8", fontsize=9)
        ax.set_ylabel("Accuracy Score (%)", color="#94A3B8", fontsize=9)
        ax.tick_params(colors="#94A3B8", labelsize=8)
        ax.grid(True, color="#334155", linestyle=":", alpha=0.6)
        ax.legend(facecolor="#0F172A", edgecolor="#334155", labelcolor="#F8FAFC", fontsize=8)

        fig.tight_layout()
        self.chart_timeline.canvas.draw()

    def _plot_pose_breakdown(self, data: List[Dict[str, Any]]) -> None:
        fig = self.chart_poses.figure
        fig.clear()
        ax = fig.add_subplot(111)
        ax.set_facecolor("#1E293B")

        if not data:
            ax.text(0.5, 0.5, "No pose breakdown available.",
                    ha='center', va='center', color='#94A3B8', transform=ax.transAxes)
            self.chart_poses.canvas.draw()
            return

        poses = [d["pose_name"][:12] for d in data]
        scores = [d["avg_score"] for d in data]
        colors = ["#10B981" if s >= 90 else "#38BDF8" if s >= 80 else "#F59E0B" if s >= 70 else "#EF4444" for s in scores]

        bars = ax.bar(poses, scores, color=colors, width=0.55, edgecolor="#0F172A")
        ax.set_ylim(0, 105)
        ax.set_ylabel("Avg Accuracy (%)", color="#94A3B8", fontsize=9)
        ax.tick_params(colors="#94A3B8", labelsize=8)
        ax.grid(True, axis='y', color="#334155", linestyle=":", alpha=0.6)

        # Bar value labels
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2.0, h + 2, f"{int(round(h))}%",
                    ha='center', va='bottom', color='#F8FAFC', fontsize=8, fontweight='bold')

        fig.tight_layout()
        self.chart_poses.canvas.draw()
