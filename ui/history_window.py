"""
Practice History Screen for KI.AI.
Displays tabular log of past workout sessions with filters by pose and accuracy.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import settings
from database.database import Database


class HistoryWindow(QWidget):
    """User Practice History and Log Screen."""

    def __init__(self, db: Database, user: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user = user
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header & Filter Toolbar
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Practice History")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        subtitle = QLabel("Chronological log of all recorded yoga and posture sessions.")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top_bar.addLayout(title_box)
        top_bar.addStretch()

        # Pose Filter Combo
        self.combo_pose = QComboBox()
        self.combo_pose.addItem("All Poses")
        for p in self.db.get_all_poses():
            self.combo_pose.addItem(p["name"])
        self.combo_pose.currentIndexChanged.connect(self.refresh_history)
        top_bar.addWidget(self.combo_pose)

        # Refresh Button
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setProperty("class", "btn_secondary")
        btn_refresh.clicked.connect(self.refresh_history)
        top_bar.addWidget(btn_refresh)

        layout.addLayout(top_bar)

        # History Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Pose Name", "Category", "Duration", "Average Score", "Final Score", "Date & Time"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        self.refresh_history()

    def refresh_history(self) -> None:
        user_id = self.user["id"] if self.user else 1
        pose_filter = self.combo_pose.currentText()
        if pose_filter == "All Poses":
            pose_filter = None

        history = self.db.get_all_practice_history(user_id, pose_filter=pose_filter)
        self.table.setRowCount(len(history))

        for row_idx, h in enumerate(history):
            self.table.setItem(row_idx, 0, QTableWidgetItem(h.get("pose_name", "Pose")))
            self.table.setItem(row_idx, 1, QTableWidgetItem(h.get("category", "General")))
            self.table.setItem(row_idx, 2, QTableWidgetItem(f"{h.get('duration', 0)} sec"))

            avg_score = float(h.get("average_score", 0.0))
            score_item = QTableWidgetItem(f"{avg_score:.1f}%")
            if avg_score >= 90:
                score_item.setForeground(Qt.green)
            elif avg_score >= 80:
                score_item.setForeground(Qt.cyan)
            elif avg_score >= 70:
                score_item.setForeground(Qt.yellow)
            else:
                score_item.setForeground(Qt.red)
            self.table.setItem(row_idx, 3, score_item)

            self.table.setItem(row_idx, 4, QTableWidgetItem(f"{float(h.get('final_score', 0.0)):.1f}%"))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(h.get("created_at", ""))))
