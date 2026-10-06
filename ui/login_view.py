"""
Login Screen for KI.AI — Posture Intelligence.
Modern split-screen authentication UI with official KI.AI branding,
show/hide password toggle, inline validation, Forgot Password integration,
and smooth transition to registration.
"""

from typing import Any, Dict, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import settings
from database.database import Database
from ui.forgot_password_dialog import ForgotPasswordDialog


class LoginView(QWidget):
    """Modern split-screen Login view for KI.AI."""

    login_successful = Signal(dict)       # Emits user_dict
    navigate_to_register = Signal()       # Switch to Register screen

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.password_visible = False
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==========================================
        # LEFT PANEL: KI.AI Branding & Visual Hero
        # ==========================================
        left_panel = QFrame()
        left_panel.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #064E3B, stop:0.45 #0F172A, stop:1 #061520);
                border-right: 1px solid #1E293B;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(46, 50, 46, 50)
        left_layout.setSpacing(14)

        left_layout.addStretch()

        # Meditating Logo Icon
        logo_icon = QLabel()
        logo_icon.setAlignment(Qt.AlignCenter)
        logo_pix = QPixmap("assets/icons/logo_icon.svg")
        if not logo_pix.isNull():
            logo_icon.setPixmap(logo_pix.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_icon.setText("🧘‍♂️")
            logo_icon.setStyleSheet("font-size: 48px;")
        left_layout.addWidget(logo_icon)

        # Brand Title (KI.AI with KI in white and AI in gradient/emerald)
        brand_row = QHBoxLayout()
        brand_row.setAlignment(Qt.AlignCenter)
        brand_row.setSpacing(0)

        lbl_ki = QLabel("KI.")
        lbl_ki.setStyleSheet("font-size: 38px; font-weight: 900; color: #FFFFFF; letter-spacing: -1px; background: transparent;")
        lbl_ai = QLabel("AI")
        lbl_ai.setStyleSheet("font-size: 38px; font-weight: 900; color: #10B981; letter-spacing: -1px; background: transparent;")
        brand_row.addWidget(lbl_ki)
        brand_row.addWidget(lbl_ai)
        left_layout.addLayout(brand_row)

        # Tagline
        brand_sub = QLabel("POSTURE INTELLIGENCE")
        brand_sub.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 3.5px; background: transparent;")
        brand_sub.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(brand_sub)

        # Slogan
        slogan = QLabel("“Train smarter. Move better. Practice with AI.”")
        slogan.setStyleSheet("font-size: 14px; font-style: italic; color: #E2E8F0; margin-top: 10px; background: transparent;")
        slogan.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(slogan)

        # Highlights Card
        features_card = QFrame()
        features_card.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 0.65);
                border: 1px solid rgba(16, 185, 129, 0.25);
                border-radius: 12px;
                padding: 14px;
                margin-top: 16px;
            }
        """)
        f_layout = QVBoxLayout(features_card)
        f_layout.setSpacing(8)

        f1 = QLabel("🟢 Real-Time Joint Angle Guidance")
        f1.setStyleSheet("color: #F1F5F9; font-size: 12px; font-weight: 500;")
        f_layout.addWidget(f1)

        f2 = QLabel("☀ 12-Step Surya Yoga Flow Coaching")
        f2.setStyleSheet("color: #F1F5F9; font-size: 12px; font-weight: 500;")
        f_layout.addWidget(f2)

        f3 = QLabel("🔒 100% Local AI Computer Vision")
        f3.setStyleSheet("color: #F1F5F9; font-size: 12px; font-weight: 500;")
        f_layout.addWidget(f3)

        left_layout.addWidget(features_card)
        left_layout.addStretch()

        privacy_note = QLabel("100% Local Processing • No Cloud Streaming")
        privacy_note.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        privacy_note.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(privacy_note)

        main_layout.addWidget(left_panel, stretch=5)

        # ==========================================
        # RIGHT PANEL: Login Form Card
        # ==========================================
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #0B1120;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(50, 40, 50, 40)
        right_layout.setSpacing(12)

        right_layout.addStretch()

        login_header = QLabel("Welcome back")
        login_header.setStyleSheet("font-size: 26px; font-weight: 800; color: #FFFFFF;")
        right_layout.addWidget(login_header)

        login_sub = QLabel("Sign in to continue your KI.AI practice.")
        login_sub.setStyleSheet("color: #94A3B8; font-size: 13px; margin-bottom: 4px;")
        right_layout.addWidget(login_sub)

        # Error / Feedback Banner
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("background-color: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid #EF4444; border-radius: 6px; padding: 8px; font-size: 12px;")
        self.lbl_error.setVisible(False)
        right_layout.addWidget(self.lbl_error)

        # Email Field
        lbl_email = QLabel("Email Address")
        lbl_email.setStyleSheet("color: #CBD5E1; font-size: 12px; font-weight: 600;")
        right_layout.addWidget(lbl_email)

        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("name@example.com")
        self.txt_email.setText("abhilash@ki.ai")
        self.txt_email.setFixedHeight(38)
        self.txt_email.setStyleSheet("""
            QLineEdit {
                background-color: #131D2E;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 8px 12px;
                color: #FFFFFF;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #10B981;
            }
        """)
        right_layout.addWidget(self.txt_email)

        # Password Field with Show/Hide Toggle
        lbl_pass = QLabel("Password")
        lbl_pass.setStyleSheet("color: #CBD5E1; font-size: 12px; font-weight: 600; margin-top: 4px;")
        right_layout.addWidget(lbl_pass)

        pass_row = QHBoxLayout()
        pass_row.setSpacing(6)

        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("Enter password")
        self.txt_password.setText("password123")
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setFixedHeight(38)
        self.txt_password.setStyleSheet("""
            QLineEdit {
                background-color: #131D2E;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 8px 12px;
                color: #FFFFFF;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #10B981;
            }
        """)
        pass_row.addWidget(self.txt_password, stretch=1)

        self.btn_toggle_pass = QPushButton("👁️")
        self.btn_toggle_pass.setFixedSize(38, 38)
        self.btn_toggle_pass.setToolTip("Show/Hide password")
        self.btn_toggle_pass.setStyleSheet("""
            QPushButton {
                background-color: #131D2E;
                border: 1px solid #1E293B;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                border: 1px solid #10B981;
            }
        """)
        self.btn_toggle_pass.clicked.connect(self._toggle_password_visibility)
        pass_row.addWidget(self.btn_toggle_pass)
        right_layout.addLayout(pass_row)

        # Remember Me & Forgot Password Row
        opts_row = QHBoxLayout()
        opts_row.setContentsMargins(0, 2, 0, 4)

        self.chk_remember = QCheckBox("Remember me")
        self.chk_remember.setChecked(True)
        self.chk_remember.setStyleSheet("color: #94A3B8; font-size: 12px;")
        opts_row.addWidget(self.chk_remember)

        opts_row.addStretch()

        btn_forgot = QPushButton("Forgot password?")
        btn_forgot.setCursor(QCursor(Qt.PointingHandCursor))
        btn_forgot.setStyleSheet("background: transparent; border: none; color: #10B981; font-size: 12px; font-weight: 600;")
        btn_forgot.clicked.connect(self._on_forgot_password)
        opts_row.addWidget(btn_forgot)

        right_layout.addLayout(opts_row)

        # Sign In Button
        self.btn_signin = QPushButton("Sign In")
        self.btn_signin.setFixedHeight(42)
        self.btn_signin.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_signin.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_signin.clicked.connect(self._on_login_clicked)
        right_layout.addWidget(self.btn_signin)

        # OR Divider
        div_row = QHBoxLayout()
        div_row.setSpacing(10)
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setStyleSheet("border-color: #1E293B;")
        div_lbl = QLabel("OR")
        div_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: bold;")
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("border-color: #1E293B;")
        div_row.addWidget(line1)
        div_row.addWidget(div_lbl)
        div_row.addWidget(line2)
        right_layout.addLayout(div_row)

        # Google Sign In
        btn_google = QPushButton("Continue with Google")
        btn_google.setFixedHeight(38)
        btn_google.setStyleSheet("""
            QPushButton {
                background-color: #131D2E;
                border: 1px solid #1E293B;
                color: #CBD5E1;
                border-radius: 8px;
                font-size: 12.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                border-color: #38BDF8;
                color: #FFFFFF;
            }
        """)
        btn_google.clicked.connect(self._on_google_signin)
        right_layout.addWidget(btn_google)

        # Footer Link: Don't have an account? Create account
        footer_row = QHBoxLayout()
        footer_row.setAlignment(Qt.AlignCenter)
        footer_lbl = QLabel("Don't have an account?")
        footer_lbl.setStyleSheet("color: #94A3B8; font-size: 12.5px;")
        btn_register = QPushButton("Create account")
        btn_register.setCursor(QCursor(Qt.PointingHandCursor))
        btn_register.setStyleSheet("background: transparent; border: none; color: #10B981; font-weight: 700; font-size: 12.5px;")
        btn_register.clicked.connect(lambda: self.navigate_to_register.emit())

        footer_row.addWidget(footer_lbl)
        footer_row.addWidget(btn_register)
        right_layout.addLayout(footer_row)

        right_layout.addStretch()

        main_layout.addWidget(right_panel, stretch=6)

    def _toggle_password_visibility(self) -> None:
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.txt_password.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_pass.setText("🔒")
        else:
            self.txt_password.setEchoMode(QLineEdit.Password)
            self.btn_toggle_pass.setText("👁️")

    def _on_forgot_password(self) -> None:
        dialog = ForgotPasswordDialog(self.db, parent=self)
        dialog.exec()

    def _on_google_signin(self) -> None:
        """Demo Google sign-in workflow."""
        user = self.db.get_user_by_id(1) or {"id": 1, "name": "Abhilash", "email": "abhilash@ki.ai", "goal": "General Fitness"}
        self.login_successful.emit(user)

    def _on_login_clicked(self) -> None:
        email = self.txt_email.text().strip()
        password = self.txt_password.text().strip()

        if not email:
            self.lbl_error.setText("Please enter your email address.")
            self.lbl_error.setVisible(True)
            return

        if not password:
            self.lbl_error.setText("Please enter your password.")
            self.lbl_error.setVisible(True)
            return

        user = self.db.authenticate_user(email, password)
        if user:
            self.lbl_error.setVisible(False)
            self.login_successful.emit(user)
        else:
            # Fallback for demo or invalid credentials
            all_users = self.db.get_all_users()
            if not all_users:
                # Seed demo user
                uid = self.db.create_user("Abhilash", email, password)
                demo_user = self.db.get_user_by_id(uid)
                self.login_successful.emit(demo_user)
            else:
                self.lbl_error.setText("Invalid email or password. Please try again.")
                self.lbl_error.setVisible(True)
