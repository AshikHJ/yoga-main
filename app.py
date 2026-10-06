"""
Main Application Entry Point for KI.AI.
AI-Powered Yoga & Posture Intelligence.
Initializes PySide6, applies Emerald Dark Theme, manages authentication lifecycle,
and launches MainWindow upon successful login.
"""

import logging
import sys
from typing import Any, Dict, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QStackedWidget

from config import settings
from database.database import Database
from ui.login_view import LoginView
from ui.main_window import MainWindow
from ui.register_view import RegisterView
from ui.styles import MAIN_STYLESHEET

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("app")


class AppController:
    """Manages application windows and user session transitions."""

    def __init__(self, db: Database):
        self.db = db
        self.auth_stack: Optional[QStackedWidget] = None
        self.main_window: Optional[MainWindow] = None

    def show_auth(self) -> None:
        """Launches the authentication container with Login and Register views."""
        if self.main_window:
            self.main_window.close()
            self.main_window = None

        self.auth_stack = QStackedWidget()
        self.auth_stack.setWindowTitle(settings.WINDOW_TITLE)
        self.auth_stack.resize(960, 620)

        self.login_view = LoginView(self.db)
        self.register_view = RegisterView(self.db)

        self.auth_stack.addWidget(self.login_view)      # Index 0
        self.auth_stack.addWidget(self.register_view)   # Index 1

        # Connect navigation signals
        self.login_view.login_successful.connect(self.on_login_success)
        self.login_view.navigate_to_register.connect(lambda: self.auth_stack.setCurrentIndex(1))
        self.register_view.navigate_to_login.connect(lambda: self.auth_stack.setCurrentIndex(0))

        self.auth_stack.show()

    def on_login_success(self, user_dict: dict) -> None:
        """Transitions from Auth view to Main Dashboard upon verified login."""
        logger.info(f"User '{user_dict.get('name')}' authenticated successfully.")
        if self.auth_stack:
            self.auth_stack.close()
            self.auth_stack = None

        self.main_window = MainWindow(self.db, user=user_dict)
        self.main_window.logout_requested.connect(self.show_auth)
        self.main_window.show()


def main() -> int:
    """Initializes and runs the KI.AI application."""
    logger.info(f"Starting {settings.APP_NAME} — {settings.APP_SUBTITLE} v{settings.APP_VERSION}...")

    # Enable High DPI attribute if available
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(settings.APP_NAME)
    app.setApplicationVersion(settings.APP_VERSION)

    # Set base application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Apply global modern emerald dark stylesheet
    app.setStyleSheet(MAIN_STYLESHEET)

    # Initialize Database & Seed data
    db = Database()

    # Launch Authentication Controller
    controller = AppController(db)
    controller.show_auth()

    logger.info("KI.AI Application lifecycle initialized.")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
