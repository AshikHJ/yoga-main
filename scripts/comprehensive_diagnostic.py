"""
Comprehensive diagnostic script to detect any runtime errors, missing database methods,
attribute errors, signal mismatches, or web route issues.
"""

import os
import sys
import traceback
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

def run_diagnostics():
    errors = []
    print("--- 1. Testing Database & Models ---")
    try:
        from database.database import Database
        db = Database()
        # Test methods
        u = db.get_user_by_id(1)
        print("db.get_user_by_id:", bool(u))
        
        # Test authenticate
        auth_res = db.authenticate_user("abhilash@ki.ai", "password123")
        print("db.authenticate_user:", auth_res)
        
        poses = db.get_all_poses()
        print("db.get_all_poses count:", len(poses))
        
        surya = db.get_surya_namaskar_poses()
        print("db.get_surya_namaskar_poses count:", len(surya))
        
        # Test update_user_password
        try:
            db.update_user_password(1, "password123")
            print("db.update_user_password: OK")
        except AttributeError as e:
            errors.append(f"Database missing method: {e}")
            
    except Exception as e:
        errors.append(f"Database error: {e}\n{traceback.format_exc()}")

    print("--- 2. Testing Core Vision & Analysis Engines ---")
    try:
        from analysis.angle_calculator import AngleCalculator
        from analysis.feedback import FeedbackEngine
        from analysis.pose_classifier import PoseClassifier
        from analysis.posture_checker import PostureChecker
        from analysis.score_calculator import ScoreCalculator
        from vision.reference_helper import ReferenceHelper
        from recommendation.recommender import PoseRecommender
        
        pc = PostureChecker()
        fb = FeedbackEngine()
        sc = ScoreCalculator()
        rec = PoseRecommender(db)
        
        print("Vision & Analysis engines initialized: OK")
    except Exception as e:
        errors.append(f"Vision/Analysis error: {e}\n{traceback.format_exc()}")

    print("--- 3. Testing PySide6 UI Classes & Dialogs ---")
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        
        from ui.login_view import LoginView
        from ui.register_view import RegisterView
        from ui.forgot_password_dialog import ForgotPasswordDialog
        from ui.logout_dialog import LogoutConfirmDialog
        from ui.yoga_library import YogaLibrary, PoseCard
        from ui.main_window import MainWindow
        from ui.home_window import HomeWindow
        from ui.surya_yoga_window import SuryaYogaWindow
        from ui.camera_window import CameraWindow
        from ui.recommendation_window import RecommendationWindow
        from ui.history_window import HistoryWindow
        from ui.progress_window import ProgressWindow
        from ui.add_pose_window import AddPoseWindow
        from ui.profile_window import ProfileWindow
        from ui.settings_window import SettingsWindow

        user = db.get_user_by_id(1) or {"id": 1, "name": "Abhilash", "goal": "General Fitness"}
        
        # Instantiate widgets
        lv = LoginView(db)
        rv = RegisterView(db)
        fp = ForgotPasswordDialog(db)
        lg = LogoutConfirmDialog()
        yl = YogaLibrary(db)
        
        # Test pose card on first pose
        if poses:
            card = PoseCard(poses[0])
            print("PoseCard initialized: OK")
            
        mw = MainWindow(db, user)
        print("MainWindow initialized: OK")
        
    except Exception as e:
        errors.append(f"PySide6 UI error: {e}\n{traceback.format_exc()}")

    print("--- 4. Testing Web App & Flask API Endpoints ---")
    try:
        from web_app import app as flask_app
        client = flask_app.test_client()
        
        r1 = client.get("/")
        print("GET / status:", r1.status_code)
        if r1.status_code != 200:
            errors.append(f"GET / returned {r1.status_code}")
            
        r2 = client.get("/api/poses")
        print("GET /api/poses status:", r2.status_code, "items:", len(r2.get_json()))
        
        r3 = client.get("/api/surya")
        print("GET /api/surya status:", r3.status_code, "items:", len(r3.get_json()))
        
        r4 = client.post("/api/login", json={"email": "abhilash@ki.ai", "password": "password123"})
        print("POST /api/login status:", r4.status_code, "response:", r4.get_json())
        
    except Exception as e:
        errors.append(f"Flask Web App error: {e}\n{traceback.format_exc()}")

    print("\n==========================================")
    if errors:
        print(f"FAILED with {len(errors)} error(s):")
        for err in errors:
            print("------------------------------------------")
            print(err)
    else:
        print("ALL TESTS & RUNTIME DIAGNOSTICS PASSED WITH 0 ERRORS!")
    print("==========================================")

if __name__ == "__main__":
    run_diagnostics()
