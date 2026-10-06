"""
Registration Screen for KI.AI — Posture Intelligence.
Provides user signup with goals, difficulty selection, password strength validation,
Terms checkbox, email verification state, and redirection to Login.
"""

from typing import Any, Dict, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import settings
from database.database import Database


class RegisterView(QWidget):
    """User Registration Screen for KI.AI."""

    registration_successful = Signal(dict)
    navigate_to_login = Signal()

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
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

        # Brand Title
        brand_row = QHBoxLayout()
        brand_row.setAlignment(Qt.AlignCenter)
        brand_row.setSpacing(0)

        lbl_ki = QLabel("KI.")
        lbl_ki.setStyleSheet("font-size: 36px; font-weight: 900; color: #FFFFFF; letter-spacing: -1px; background: transparent;")
        lbl_ai = QLabel("AI")
        lbl_ai.setStyleSheet("font-size: 36px; font-weight: 900; color: #10B981; letter-spacing: -1px; background: transparent;")
        brand_row.addWidget(lbl_ki)
        brand_row.addWidget(lbl_ai)
        left_layout.addLayout(brand_row)

        brand_sub = QLabel("POSTURE INTELLIGENCE")
        brand_sub.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 3.5px; background: transparent;")
        brand_sub.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(brand_sub)

        slogan = QLabel("“Train smarter. Move better. Practice with AI.”")
        slogan.setStyleSheet("font-size: 13.5px; font-style: italic; color: #E2E8F0; margin-top: 8px; background: transparent;")
        slogan.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(slogan)

        features_card = QFrame()
        features_card.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 0.65);
                border: 1px solid rgba(16, 185, 129, 0.25);
                border-radius: 12px;
                padding: 14px;
                margin-top: 14px;
            }
        """)
        f_layout = QVBoxLayout(features_card)
        f_layout.setSpacing(8)

        f1 = QLabel("✓ Personalized AI Posture Curriculum")
        f1.setStyleSheet("color: #F1F5F9; font-size: 12px; font-weight: 500;")
        f_layout.addWidget(f1)

        f2 = QLabel("✓ Joint Angle Precision Feedback")
        f2.setStyleSheet("color: #F1F5F9; font-size: 12px; font-weight: 500;")
        f_layout.addWidget(f2)

        f3 = QLabel("✓ Local Privacy & Session Analytics")
        f3.setStyleSheet("color: #F1F5F9; font-size: 12px; font-weight: 500;")
        f_layout.addWidget(f3)

        left_layout.addWidget(features_card)
        left_layout.addStretch()

        main_layout.addWidget(left_panel, stretch=4)

        # ==========================================
        # RIGHT PANEL: Registration Form Stack
        # ==========================================
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #0B1120;")
        self.right_stack = QStackedWidget(right_panel)
        
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(0, 0, 0, 0)
        rp_layout.addWidget(self.right_stack)

        # PAGE 0: Form
        page_form = QWidget()
        form_layout = QVBoxLayout(page_form)
        form_layout.setContentsMargins(46, 36, 46, 36)
        form_layout.setSpacing(10)

        form_layout.addStretch()

        title = QLabel("Create your account")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #FFFFFF;")
        form_layout.addWidget(title)

        subtitle = QLabel("Start your personalized AI yoga journey.")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 12.5px; margin-bottom: 4px;")
        form_layout.addWidget(subtitle)

        # Error Banner
        self.lbl_msg = QLabel("")
        self.lbl_msg.setStyleSheet("background-color: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid #EF4444; border-radius: 6px; padding: 6px 10px; font-size: 11.5px;")
        self.lbl_msg.setVisible(False)
        form_layout.addWidget(self.lbl_msg)

        grid = QGridLayout()
        grid.setSpacing(8)

        # Full Name
        grid.addWidget(QLabel("Full Name *"), 0, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Abhilash Sharma")
        self.txt_name.setFixedHeight(36)
        grid.addWidget(self.txt_name, 1, 0)

        # Email
        grid.addWidget(QLabel("Email Address *"), 0, 1)
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("name@example.com")
        self.txt_email.setFixedHeight(36)
        grid.addWidget(self.txt_email, 1, 1)

        # Password
        grid.addWidget(QLabel("Password *"), 2, 0)
        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("Min. 6 chars")
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setFixedHeight(36)
        self.txt_password.textChanged.connect(self._check_password_strength)
        grid.addWidget(self.txt_password, 3, 0)

        # Confirm Password
        grid.addWidget(QLabel("Confirm Password *"), 2, 1)
        self.txt_confirm_pass = QLineEdit()
        self.txt_confirm_pass.setPlaceholderText("Re-type password")
        self.txt_confirm_pass.setEchoMode(QLineEdit.Password)
        self.txt_confirm_pass.setFixedHeight(36)
        grid.addWidget(self.txt_confirm_pass, 3, 1)

        # Fitness Level
        grid.addWidget(QLabel("Fitness Level"), 4, 0)
        self.combo_exp = QComboBox()
        self.combo_exp.addItems(settings.DIFFICULTY_LEVELS)
        self.combo_exp.setFixedHeight(36)
        grid.addWidget(self.combo_exp, 5, 0)

        # Primary Goal
        grid.addWidget(QLabel("Primary Goal"), 4, 1)
        self.combo_goal = QComboBox()
        self.combo_goal.addItems(settings.GOALS)
        self.combo_goal.setFixedHeight(36)
        grid.addWidget(self.combo_goal, 5, 1)

        form_layout.addLayout(grid)

        # Password Strength Bar
        pass_str_row = QHBoxLayout()
        pass_str_row.setSpacing(6)
        pass_str_lbl = QLabel("Password Strength:")
        pass_str_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        pass_str_row.addWidget(pass_str_lbl)

        self.pass_strength_bar = QProgressBar()
        self.pass_strength_bar.setRange(0, 100)
        self.pass_strength_bar.setValue(0)
        self.pass_strength_bar.setFixedHeight(6)
        self.pass_strength_bar.setTextVisible(False)
        self.pass_strength_bar.setStyleSheet("""
            QProgressBar { background-color: #1E293B; border-radius: 3px; border: none; }
            QProgressBar::chunk { background-color: #10B981; border-radius: 3px; }
        """)
        pass_str_row.addWidget(self.pass_strength_bar, stretch=1)

        self.lbl_strength_text = QLabel("None")
        self.lbl_strength_text.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        pass_str_row.addWidget(self.lbl_strength_text)
        form_layout.addLayout(pass_str_row)

        # Terms Checkbox
        self.chk_terms = QCheckBox("I agree to the Terms of Service & Privacy Policy")
        self.chk_terms.setChecked(True)
        self.chk_terms.setStyleSheet("color: #94A3B8; font-size: 12px; margin-top: 4px;")
        form_layout.addWidget(self.chk_terms)

        # Submit Button
        self.btn_submit = QPushButton("Create Account")
        self.btn_submit.setFixedHeight(40)
        self.btn_submit.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 13.5px;
                font-weight: 700;
                margin-top: 4px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_submit.clicked.connect(self._on_register_clicked)
        form_layout.addWidget(self.btn_submit)

        # Google Sign Up
        btn_google = QPushButton("Sign up with Google")
        btn_google.setFixedHeight(36)
        btn_google.setStyleSheet("""
            QPushButton {
                background-color: #131D2E;
                border: 1px solid #1E293B;
                color: #CBD5E1;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                border-color: #38BDF8;
                color: #FFFFFF;
            }
        """)
        btn_google.clicked.connect(self._on_google_signup)
        form_layout.addWidget(btn_google)

        # Footer Sign In link
        footer_row = QHBoxLayout()
        footer_row.setAlignment(Qt.AlignCenter)
        footer_lbl = QLabel("Already have an account?")
        footer_lbl.setStyleSheet("color: #94A3B8; font-size: 12.5px;")
        btn_signin = QPushButton("Sign In")
        btn_signin.setCursor(QCursor(Qt.PointingHandCursor))
        btn_signin.setStyleSheet("background: transparent; border: none; color: #10B981; font-weight: 700; font-size: 12.5px;")
        btn_signin.clicked.connect(lambda: self.navigate_to_login.emit())

        footer_row.addWidget(footer_lbl)
        footer_row.addWidget(btn_signin)
        form_layout.addLayout(footer_row)

        form_layout.addStretch()
        self.right_stack.addWidget(page_form)

        # PAGE 1: Email Verification Success Screen
        page_verify = QWidget()
        pv_layout = QVBoxLayout(page_verify)
        pv_layout.setContentsMargins(46, 50, 46, 50)
        pv_layout.setSpacing(14)
        pv_layout.addStretch()

        v_icon = QLabel("📧 ✨")
        v_icon.setStyleSheet("font-size: 48px;")
        v_icon.setAlignment(Qt.AlignCenter)
        pv_layout.addWidget(v_icon)

        v_title = QLabel("Account created successfully")
        v_title.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        v_title.setAlignment(Qt.AlignCenter)
        pv_layout.addWidget(v_title)

        self.lbl_v_desc = QLabel("Check your email to verify your KI.AI account and start your practice.")
        self.lbl_v_desc.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 1.5;")
        self.lbl_v_desc.setAlignment(Qt.AlignCenter)
        self.lbl_v_desc.setWordWrap(True)
        pv_layout.addWidget(self.lbl_v_desc)

        pv_layout.addStretch()

        btn_continue = QPushButton("Continue to Sign In")
        btn_continue.setFixedHeight(42)
        btn_continue.setCursor(QCursor(Qt.PointingHandCursor))
        btn_continue.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 13.5px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        btn_continue.clicked.connect(lambda: self.navigate_to_login.emit())
        pv_layout.addWidget(btn_continue)

        pv_layout.addStretch()
        self.right_stack.addWidget(page_verify)

        main_layout.addWidget(right_panel, stretch=6)

    def _check_password_strength(self, text: str) -> None:
        if len(text) == 0:
            self.pass_strength_bar.setValue(0)
            self.lbl_strength_text.setText("None")
            self.lbl_strength_text.setStyleSheet("color: #94A3B8;")
        elif len(text) < 6:
            self.pass_strength_bar.setValue(35)
            self.lbl_strength_text.setText("Weak")
            self.lbl_strength_text.setStyleSheet("color: #EF4444;")
        elif len(text) < 9:
            self.pass_strength_bar.setValue(70)
            self.lbl_strength_text.setText("Medium")
            self.lbl_strength_text.setStyleSheet("color: #F59E0B;")
        else:
            self.pass_strength_bar.setValue(100)
            self.lbl_strength_text.setText("Strong")
            self.lbl_strength_text.setStyleSheet("color: #10B981;")

    def _on_google_signup(self) -> None:
        self.txt_name.setText("Google User")
        self.txt_email.setText("user@gmail.com")
        self.txt_password.setText("googleAuth123")
        self.txt_confirm_pass.setText("googleAuth123")
        self._on_register_clicked()

    def _on_register_clicked(self) -> None:
        name = self.txt_name.text().strip()
        email = self.txt_email.text().strip()
        password = self.txt_password.text().strip()
        confirm = self.txt_confirm_pass.text().strip()
        goal = self.combo_goal.currentText()
        difficulty = self.combo_exp.currentText()

        if not name:
            self.lbl_msg.setText("Please enter your full name.")
            self.lbl_msg.setVisible(True)
            return

        if not email or "@" not in email:
            self.lbl_msg.setText("Please enter a valid email address.")
            self.lbl_msg.setVisible(True)
            return

        if len(password) < 6:
            self.lbl_msg.setText("Password must be at least 6 characters.")
            self.lbl_msg.setVisible(True)
            return

        if password != confirm:
            self.lbl_msg.setText("Passwords do not match.")
            self.lbl_msg.setVisible(True)
            return

        if not self.chk_terms.isChecked():
            self.lbl_msg.setText("Please accept the Terms of Service & Privacy Policy.")
            self.lbl_msg.setVisible(True)
            return

        # Check existing email
        existing = self.db.get_user_by_email(email)
        if existing:
            self.lbl_msg.setText("An account with this email already exists.")
            self.lbl_msg.setVisible(True)
            return

        # Create user in database
        uid = self.db.create_user(name=name, email=email, password=password, goal=goal, difficulty=difficulty)
        self.lbl_v_desc.setText(f"We've sent a verification link to:\n{email}\n\nVerify your account to start practicing with KI.AI.")
        self.right_stack.setCurrentIndex(1)
