"""
Logout Confirmation Dialog for KI.AI — Posture Intelligence.
Glassmorphism confirmation modal prompting user before terminating session.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from config import settings


class LogoutConfirmDialog(QDialog):
    """Modern dark confirmation modal for secure sign-out."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KI.AI — Sign Out")
        self.setFixedSize(420, 240)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(14)

        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                border: 1.5px solid #1E293B;
                border-radius: 14px;
            }
        """)

        # Icon & Title Header
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        icon_lbl = QLabel("🚪")
        icon_lbl.setStyleSheet("font-size: 26px; background: rgba(239, 68, 68, 0.12); padding: 8px; border-radius: 10px; border: 1px solid rgba(239, 68, 68, 0.3);")
        header_row.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_lbl = QLabel("Sign out of KI.AI?")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 800; color: #FFFFFF;")
        title_col.addWidget(title_lbl)

        sub_lbl = QLabel("Are you sure you want to end your current session?")
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 12.5px;")
        title_col.addWidget(sub_lbl)

        header_row.addLayout(title_col)
        layout.addLayout(header_row)

        layout.addSpacing(6)

        note_lbl = QLabel("Your practice progress and session metrics are automatically saved locally.")
        note_lbl.setStyleSheet("color: #64748B; font-size: 11.5px; line-height: 1.3;")
        note_lbl.setWordWrap(True)
        layout.addWidget(note_lbl)

        layout.addStretch()

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #CBD5E1;
                border: 1px solid #334155;
                border-radius: 8px;
                font-weight: 600;
                font-size: 12.5px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #FFFFFF;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_signout = QPushButton("Sign Out")
        btn_signout.setFixedHeight(38)
        btn_signout.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-weight: 700;
                font-size: 12.5px;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
        """)
        btn_signout.clicked.connect(self.accept)
        btn_row.addWidget(btn_signout)

        layout.addLayout(btn_row)
