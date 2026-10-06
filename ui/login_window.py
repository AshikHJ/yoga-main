"""
User Login and Profile Selection Dialog.
Provides a clean, streamlined user switcher and registration workflow.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import settings
from database.database import Database


class LoginDialog(QDialog):
    """Dialog for selecting an existing user profile or creating a new one."""

    user_selected = Signal(dict)

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Select User Profile - AI Yoga Assistant")
        self.setMinimumSize(520, 560)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header Title
        title_label = QLabel("🧘 Welcome to AI Yoga Assistant")
        title_label.setProperty("class", "heading1")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #6366F1;")
        main_layout.addWidget(title_label)

        sub_label = QLabel("Select your profile to load personalized goals, pose recommendations, and history.")
        sub_label.setStyleSheet(f"color: {settings.THEME['text_secondary']};")
        sub_label.setWordWrap(True)
        main_layout.addWidget(sub_label)

        # Stacked Widget (Page 0: Profile List, Page 1: Create Profile Form)
        self.stack = QStackedWidget()

        # Page 0: Profile Selector
        self.page_list = QWidget()
        list_layout = QVBoxLayout(self.page_list)
        list_layout.setContentsMargins(0, 8, 0, 0)
        list_layout.setSpacing(12)

        self.user_list = QListWidget()
        self.user_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {settings.THEME['surface']};
                border: 1px solid {settings.THEME['border']};
                border-radius: 8px;
                padding: 6px;
            }}
            QListWidget::item {{
                background-color: {settings.THEME['surface_light']};
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 6px;
                color: {settings.THEME['text_primary']};
                font-size: 13px;
            }}
            QListWidget::item:selected {{
                background-color: {settings.THEME['primary']};
                color: #FFFFFF;
            }}
        """)
        list_layout.addWidget(self.user_list)

        btn_row = QHBoxLayout()
        self.btn_login = QPushButton("Continue with Profile")
        self.btn_login.setProperty("class", "btn_primary")
        self.btn_login.clicked.connect(self._on_login_clicked)
        btn_row.addWidget(self.btn_login)

        self.btn_new_user = QPushButton("+ New Profile")
        self.btn_new_user.setProperty("class", "btn_secondary")
        self.btn_new_user.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_row.addWidget(self.btn_new_user)
        list_layout.addLayout(btn_row)

        # Page 1: New Profile Form
        self.page_form = QWidget()
        form_layout = QVBoxLayout(self.page_form)
        form_layout.setContentsMargins(0, 8, 0, 0)
        form_layout.setSpacing(14)

        form_card = QFrame()
        form_card.setProperty("class", "card")
        card_layout = QFormLayout(form_card)
        card_layout.setSpacing(12)

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Enter your full name or nickname")
        card_layout.addRow("Full Name:", self.input_name)

        self.input_age = QSpinBox()
        self.input_age.setRange(10, 100)
        self.input_age.setValue(24)
        card_layout.addRow("Age:", self.input_age)

        self.combo_exp = QComboBox()
        self.combo_exp.addItems(settings.DIFFICULTY_LEVELS)
        card_layout.addRow("Experience:", self.combo_exp)

        self.combo_goal = QComboBox()
        self.combo_goal.addItems(settings.GOALS)
        card_layout.addRow("Primary Goal:", self.combo_goal)

        form_layout.addWidget(form_card)

        form_btn_row = QHBoxLayout()
        btn_save = QPushButton("Create Profile")
        btn_save.setProperty("class", "btn_success")
        btn_save.clicked.connect(self._on_save_new_user)
        form_btn_row.addWidget(btn_save)

        btn_cancel = QPushButton("Back")
        btn_cancel.setProperty("class", "btn_secondary")
        btn_cancel.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        form_btn_row.addWidget(btn_cancel)
        form_layout.addLayout(form_btn_row)

        self.stack.addWidget(self.page_list)
        self.stack.addWidget(self.page_form)
        main_layout.addWidget(self.stack)

        self._refresh_users_list()

    def _refresh_users_list(self) -> None:
        self.user_list.clear()
        users = self.db.get_all_users()
        if not users:
            # Create default demo user if none exists
            default_id = self.db.create_user("Yoga Practitioner", 26, "Beginner", "General Fitness")
            users = self.db.get_all_users()

        for u in users:
            item = QListWidgetItem(f"👤 {u['name']}   •   {u['experience']}   •   Goal: {u['goal']}")
            item.setData(Qt.UserRole, u)
            self.user_list.addItem(item)

        if self.user_list.count() > 0:
            self.user_list.setCurrentRow(0)

    def _on_login_clicked(self) -> None:
        item = self.user_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Select Profile", "Please select a user profile to continue.")
            return
        user_data = item.data(Qt.UserRole)
        self.user_selected.emit(user_data)
        self.accept()

    def _on_save_new_user(self) -> None:
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid profile name.")
            return

        age = self.input_age.value()
        exp = self.combo_exp.currentText()
        goal = self.combo_goal.currentText()

        user_id = self.db.create_user(name, age, exp, goal)
        user_data = self.db.get_user_by_id(user_id)
        if user_data:
            self.user_selected.emit(user_data)
            self.accept()
