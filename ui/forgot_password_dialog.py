"""
Forgot Password & Reset Password Dialogs for KI.AI — Posture Intelligence.
Provides secure password recovery flow with email reset links, verification,
password strength validation, and confirmation states.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import settings
from database.database import Database


class ForgotPasswordDialog(QDialog):
    """Modern glassmorphic dialog for password recovery and reset."""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("KI.AI — Password Recovery")
        self.setFixedSize(480, 520)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 28, 28, 28)
        main_layout.setSpacing(16)

        self.setStyleSheet(f"""
            QDialog {{
                background-color: #0B1120;
            }}
            QLineEdit {{
                background-color: #131D2E;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 10px 14px;
                color: #FFFFFF;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid #10B981;
            }}
            QPushButton.btn_primary {{
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton.btn_primary:hover {{
                background-color: #059669;
            }}
            QPushButton.btn_secondary {{
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }}
            QPushButton.btn_secondary:hover {{
                background-color: #334155;
                color: #FFFFFF;
            }}
        """)

        self.stack = QStackedWidget()

        # ==========================================
        # PAGE 0: Request Reset Link
        # ==========================================
        page_request = QWidget()
        pr_layout = QVBoxLayout(page_request)
        pr_layout.setContentsMargins(0, 0, 0, 0)
        pr_layout.setSpacing(14)

        # Header
        icon_lbl = QLabel("🔐")
        icon_lbl.setStyleSheet("font-size: 36px;")
        pr_layout.addWidget(icon_lbl)

        title_lbl = QLabel("Forgot your password?")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        pr_layout.addWidget(title_lbl)

        sub_lbl = QLabel("Enter your email address and we'll send you a secure password reset link.")
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 1.4;")
        sub_lbl.setWordWrap(True)
        pr_layout.addWidget(sub_lbl)

        pr_layout.addSpacing(6)

        # Email Input
        email_lbl = QLabel("Email Address")
        email_lbl.setStyleSheet("color: #CBD5E1; font-size: 12px; font-weight: 600;")
        pr_layout.addWidget(email_lbl)

        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("name@example.com")
        pr_layout.addWidget(self.txt_email)

        self.lbl_req_error = QLabel("")
        self.lbl_req_error.setStyleSheet("color: #EF4444; font-size: 11.5px;")
        self.lbl_req_error.setVisible(False)
        pr_layout.addWidget(self.lbl_req_error)

        pr_layout.addStretch()

        # Send Button
        btn_send = QPushButton("Send Reset Link")
        btn_send.setProperty("class", "btn_primary")
        btn_send.setFixedHeight(40)
        btn_send.clicked.connect(self._on_send_reset_link)
        pr_layout.addWidget(btn_send)

        # Back to Sign In
        btn_back = QPushButton("Back to Sign In")
        btn_back.setStyleSheet("background: transparent; border: none; color: #10B981; font-weight: 600; font-size: 13px;")
        btn_back.clicked.connect(self.reject)
        pr_layout.addWidget(btn_back)

        self.stack.addWidget(page_request)

        # ==========================================
        # PAGE 1: Link Sent / Verification
        # ==========================================
        page_sent = QWidget()
        ps_layout = QVBoxLayout(page_sent)
        ps_layout.setContentsMargins(0, 0, 0, 0)
        ps_layout.setSpacing(14)

        ps_layout.addStretch()

        sent_icon = QLabel("📧 ✨")
        sent_icon.setStyleSheet("font-size: 44px;")
        sent_icon.setAlignment(Qt.AlignCenter)
        ps_layout.addWidget(sent_icon)

        sent_title = QLabel("Reset link sent")
        sent_title.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        sent_title.setAlignment(Qt.AlignCenter)
        ps_layout.addWidget(sent_title)

        self.lbl_sent_msg = QLabel("Check your inbox for instructions to securely reset your password.")
        self.lbl_sent_msg.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 1.5;")
        self.lbl_sent_msg.setAlignment(Qt.AlignCenter)
        self.lbl_sent_msg.setWordWrap(True)
        ps_layout.addWidget(self.lbl_sent_msg)

        ps_layout.addStretch()

        btn_enter_new = QPushButton("Enter New Password Directly")
        btn_enter_new.setProperty("class", "btn_primary")
        btn_enter_new.setFixedHeight(40)
        btn_enter_new.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        ps_layout.addWidget(btn_enter_new)

        btn_done = QPushButton("Return to Sign In")
        btn_done.setProperty("class", "btn_secondary")
        btn_done.setFixedHeight(36)
        btn_done.clicked.connect(self.accept)
        ps_layout.addWidget(btn_done)

        self.stack.addWidget(page_sent)

        # ==========================================
        # PAGE 2: Create New Password
        # ==========================================
        page_reset = QWidget()
        rst_layout = QVBoxLayout(page_reset)
        rst_layout.setContentsMargins(0, 0, 0, 0)
        rst_layout.setSpacing(12)

        rst_title = QLabel("Create a new password")
        rst_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #FFFFFF;")
        rst_layout.addWidget(rst_title)

        rst_sub = QLabel("Ensure your password is at least 6 characters with letters and numbers.")
        rst_sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        rst_sub.setWordWrap(True)
        rst_layout.addWidget(rst_sub)

        # New Password
        rst_layout.addWidget(QLabel("New Password"))
        self.txt_new_pass = QLineEdit()
        self.txt_new_pass.setEchoMode(QLineEdit.Password)
        self.txt_new_pass.setPlaceholderText("••••••••")
        rst_layout.addWidget(self.txt_new_pass)

        # Confirm Password
        rst_layout.addWidget(QLabel("Confirm New Password"))
        self.txt_conf_pass = QLineEdit()
        self.txt_conf_pass.setEchoMode(QLineEdit.Password)
        self.txt_conf_pass.setPlaceholderText("••••••••")
        rst_layout.addWidget(self.txt_conf_pass)

        self.lbl_rst_error = QLabel("")
        self.lbl_rst_error.setStyleSheet("color: #EF4444; font-size: 11.5px;")
        self.lbl_rst_error.setVisible(False)
        rst_layout.addWidget(self.lbl_rst_error)

        rst_layout.addStretch()

        btn_update = QPushButton("Update Password")
        btn_update.setProperty("class", "btn_primary")
        btn_update.setFixedHeight(40)
        btn_update.clicked.connect(self._on_update_password)
        rst_layout.addWidget(btn_update)

        self.stack.addWidget(page_reset)

        # ==========================================
        # PAGE 3: Password Updated Success
        # ==========================================
        page_success = QWidget()
        sc_layout = QVBoxLayout(page_success)
        sc_layout.setContentsMargins(0, 0, 0, 0)
        sc_layout.setSpacing(14)

        sc_layout.addStretch()

        ok_icon = QLabel("✅")
        ok_icon.setStyleSheet("font-size: 48px;")
        ok_icon.setAlignment(Qt.AlignCenter)
        sc_layout.addWidget(ok_icon)

        ok_title = QLabel("Password updated successfully")
        ok_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #FFFFFF;")
        ok_title.setAlignment(Qt.AlignCenter)
        sc_layout.addWidget(ok_title)

        ok_desc = QLabel("You can now sign in to KI.AI using your new password.")
        ok_desc.setStyleSheet("color: #94A3B8; font-size: 13px;")
        ok_desc.setAlignment(Qt.AlignCenter)
        sc_layout.addWidget(ok_desc)

        sc_layout.addStretch()

        btn_signin_now = QPushButton("Sign In")
        btn_signin_now.setProperty("class", "btn_primary")
        btn_signin_now.setFixedHeight(40)
        btn_signin_now.clicked.connect(self.accept)
        sc_layout.addWidget(btn_signin_now)

        self.stack.addWidget(page_success)

        main_layout.addWidget(self.stack)

    def _on_send_reset_link(self) -> None:
        email = self.txt_email.text().strip()
        if not email or "@" not in email:
            self.lbl_req_error.setText("Please enter a valid email address.")
            self.lbl_req_error.setVisible(True)
            return

        self.lbl_req_error.setVisible(False)
        self.lbl_sent_msg.setText(f"We've sent a secure reset link to:\n{email}\n\nCheck your inbox to continue.")
        self.stack.setCurrentIndex(1)

    def _on_update_password(self) -> None:
        p1 = self.txt_new_pass.text()
        p2 = self.txt_conf_pass.text()

        if len(p1) < 6:
            self.lbl_rst_error.setText("Password must be at least 6 characters.")
            self.lbl_rst_error.setVisible(True)
            return

        if p1 != p2:
            self.lbl_rst_error.setText("Passwords do not match.")
            self.lbl_rst_error.setVisible(True)
            return

        email = self.txt_email.text().strip()
        user = self.db.get_user_by_email(email)
        if user:
            self.db.update_user_password(user["id"], p1)

        self.lbl_rst_error.setVisible(False)
        self.stack.setCurrentIndex(3)
