"""
User Profile Screen for KI.AI.
Displays user account metrics, experience level, fitness goals,
and profile updating form.
"""

from typing import Any, Dict, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config import settings
from database.database import Database


class ProfileWindow(QWidget):
    """User Profile and Account Preferences Screen."""

    def __init__(self, db: Database, user: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user = user
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # Title
        title_box = QVBoxLayout()
        title = QLabel("User Profile")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        subtitle = QLabel("Personalize your bio, fitness goals, and training experience level.")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Lifetime Summary Card
        stat_card = QFrame()
        stat_card.setProperty("class", "highlight_card")
        st_layout = QHBoxLayout(stat_card)
        st_layout.setContentsMargins(20, 16, 20, 16)

        user_id = self.user["id"] if self.user else 1
        stats = self.db.get_user_stats(user_id)

        st_layout.addWidget(self._create_metric_pill("TOTAL SESSIONS", str(stats.get("total_sessions", 0))))
        st_layout.addWidget(self._create_metric_pill("AVG ACCURACY", f"{stats.get('avg_score', 0.0):.1f}%"))
        st_layout.addWidget(self._create_metric_pill("BEST ACCURACY", f"{stats.get('best_score', 0.0):.1f}%"))
        st_layout.addWidget(self._create_metric_pill("TOP POSE", stats.get("favorite_pose", "Warrior II")))
        layout.addWidget(stat_card)

        # Editable Profile Form Card
        form_card = QFrame()
        form_card.setProperty("class", "card")
        f_layout = QVBoxLayout(form_card)
        f_layout.setContentsMargins(20, 20, 20, 20)
        f_layout.setSpacing(14)

        f_title = QLabel("Account Details")
        f_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        f_layout.addWidget(f_title)

        grid = QGridLayout()
        grid.setSpacing(12)

        grid.addWidget(QLabel("Full Name"), 0, 0)
        self.txt_name = QLineEdit(self.user.get("name", "Abhilash") if self.user else "Abhilash")
        self.txt_name.setFixedHeight(36)
        grid.addWidget(self.txt_name, 1, 0)

        grid.addWidget(QLabel("Age"), 0, 1)
        self.spin_age = QSpinBox()
        self.spin_age.setRange(10, 100)
        self.spin_age.setValue(self.user.get("age", 23) if self.user else 23)
        self.spin_age.setFixedHeight(36)
        self.spin_age.setStyleSheet("background-color: #0F172A; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; color: white;")
        grid.addWidget(self.spin_age, 1, 1)

        grid.addWidget(QLabel("Experience Level"), 2, 0)
        self.combo_exp = QComboBox()
        self.combo_exp.addItems(settings.DIFFICULTY_LEVELS)
        if self.user:
            self.combo_exp.setCurrentText(self.user.get("experience", "Beginner"))
        self.combo_exp.setFixedHeight(36)
        grid.addWidget(self.combo_exp, 3, 0)

        grid.addWidget(QLabel("Primary Goal"), 2, 1)
        self.combo_goal = QComboBox()
        self.combo_goal.addItems(settings.GOALS)
        if self.user:
            self.combo_goal.setCurrentText(self.user.get("goal", "General Fitness"))
        self.combo_goal.setFixedHeight(36)
        grid.addWidget(self.combo_goal, 3, 1)

        f_layout.addLayout(grid)

        # Save Button
        btn_save = QPushButton("Save Profile Changes")
        btn_save.setProperty("class", "btn_primary")
        btn_save.setFixedHeight(38)
        btn_save.clicked.connect(self._on_save_profile)
        f_layout.addWidget(btn_save)

        layout.addWidget(form_card)
        layout.addStretch()

    def _create_metric_pill(self, label: str, val: str) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)
        v_lbl = QLabel(val)
        v_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #10B981;")
        l_lbl = QLabel(label)
        l_lbl.setStyleSheet("font-size: 10px; color: #A7F3D0; font-weight: 700; letter-spacing: 0.5px;")
        l.addWidget(v_lbl)
        l.addWidget(l_lbl)
        return w

    def _on_save_profile(self) -> None:
        if not self.user:
            return
        new_name = self.txt_name.text().strip()
        new_age = self.spin_age.value()
        new_exp = self.combo_exp.currentText()
        new_goal = self.combo_goal.currentText()

        success = self.db.update_user_profile(
            user_id=self.user["id"],
            name=new_name,
            age=new_age,
            experience=new_exp,
            goal=new_goal,
        )
        if success:
            self.user["name"] = new_name
            self.user["age"] = new_age
            self.user["experience"] = new_exp
            self.user["goal"] = new_goal
            QMessageBox.information(self, "Profile Updated", "Your profile changes were saved successfully!")
