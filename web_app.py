"""
KI.AI Web Application Server.
AI-Powered Yoga & Posture Intelligence.
Serves full browser interface on port 8080 with real-time pose checking,
Surya Yoga sequence, user authentication, and SQLite persistence.
"""

import json
import logging
import os
import socket
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

from analysis.angle_calculator import AngleCalculator
from analysis.feedback import FeedbackEngine
from analysis.pose_classifier import PoseClassifier
from analysis.posture_checker import PostureChecker
from analysis.score_calculator import ScoreCalculator
from config import settings
from database.database import Database
from recommendation.recommender import PoseRecommender
from recommendation.session_planner import SessionPlanner
from coach.coach_engine import CoachEngine
from coach.conversation import ConversationalCoach
from coach.state_machine import SessionState, SessionStateMachine
from voice.voice_manager import CoachingEvent, Priority, VoiceManager, VoiceState, get_voice_manager
from payment.razorpay_client import get_razorpay_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates", static_folder="static")

# Environment-configurable CORS
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "").strip()
if allowed_origins_env:
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost:8080",
        "http://localhost:8081",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
    ]
CORS(app, origins=allowed_origins)

@app.after_request
def set_security_headers(response):
    """Sets defense-in-depth CSP and browser privacy/security headers."""
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://checkout.razorpay.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https: blob:; "
        "media-src 'self' blob:; "
        "connect-src 'self' https://cdn.jsdelivr.net https://api.razorpay.com https://lumberjack.razorpay.com; "
        "frame-src 'self' https://api.razorpay.com; "
    )
    response.headers["Content-Security-Policy"] = csp
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

db = Database()
posture_checker = PostureChecker()
recommender = PoseRecommender(db)
session_planner = SessionPlanner(db)
coach_engine = CoachEngine()
conversational_coach = ConversationalCoach(db=db)
voice_manager = get_voice_manager()
razorpay_client = get_razorpay_client()
all_poses_cache = db.get_all_poses()


def get_local_ip() -> str:
    """Gets local IP address on Wi-Fi/LAN."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@app.route("/")
def index():
    """Renders the main KI.AI web application."""
    return render_template("index.html")


@app.route("/admin")
def admin_console():
    """Renders the KI.AI Admin Console & Posture Intelligence Operations Center."""
    return render_template("admin.html")


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    """Serves static assets including SVG pose figures and images."""
    return send_from_directory(str(Path("assets").resolve()), filename)


@app.route("/api/poses", methods=["GET"])
def get_poses():
    """Returns all yoga poses with rules."""
    poses = db.get_all_poses()
    return jsonify(poses)


@app.route("/api/surya", methods=["GET"])
def get_surya_poses():
    """Returns 12-step Surya Namaskar sequence."""
    surya = db.get_surya_namaskar_poses()
    return jsonify(surya)


@app.route("/api/login", methods=["POST"])
def login():
    """Authenticates user with email and password."""
    data = request.json or {}
    email = data.get("email", "")
    password = data.get("password", "")

    success, msg, user = db.authenticate_user(email, password)
    if success and user:
        return jsonify({"status": "success", "message": msg, "user": user})
    return jsonify({"status": "error", "message": msg}), 401


@app.route("/api/register", methods=["POST"])
def register():
    """Registers a new user profile."""
    data = request.json or {}
    name = data.get("name", "")
    email = data.get("email", "")
    password = data.get("password", "")
    age = int(data.get("age", 25))
    experience = data.get("experience", "Beginner")
    goal = data.get("goal", "General Fitness")

    success, msg, user = db.register_user(
        name=name,
        email=email,
        password=password,
        age=age,
        experience=experience,
        goal=goal,
    )

    if success:
        return jsonify({"status": "success", "message": msg, "user": user})
    return jsonify({"status": "error", "message": msg}), 400


@app.route("/api/analyze_posture", methods=["POST"])
def analyze_posture():
    """
    Receives landmark coordinates from browser camera, extracts joint angles,
    evaluates posture against target rules or automatically detects the pose,
    and returns 4-color status dots (🟢 🔴 🟡 ⚪), accuracy score %, and RIGHT/WRONG callouts.
    """
    data = request.json or {}
    landmarks_raw = data.get("landmarks", {})
    pose_id = data.get("pose_id")
    mode = data.get("mode", "explicit")  # 'explicit' or 'auto'

    if not landmarks_raw:
        return jsonify({"status": "error", "message": "Missing landmarks data"}), 400

    # Normalize landmarks into dictionary expected by AngleCalculator
    landmarks = {}
    total_visible = 0
    for name, lm in landmarks_raw.items():
        vis = float(lm.get("visibility", 0.9))
        if vis >= 0.5:
            total_visible += 1
        landmarks[name] = {
            "x": float(lm.get("x", 0.0)),
            "y": float(lm.get("y", 0.0)),
            "z": float(lm.get("z", 0.0)),
            "visibility": vis,
            "px": int(lm.get("x", 0.0) * 640),
            "py": int(lm.get("y", 0.0) * 480),
        }

    # Tracking & Body Visibility Validation
    key_upper = ["LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_HIP", "RIGHT_HIP"]
    key_lower = ["LEFT_KNEE", "RIGHT_KNEE", "LEFT_ANKLE", "RIGHT_ANKLE"]
    upper_vis = sum(1 for k in key_upper if landmarks.get(k, {}).get("visibility", 0.0) >= 0.5)
    lower_vis = sum(1 for k in key_lower if landmarks.get(k, {}).get("visibility", 0.0) >= 0.4)

    if upper_vis < 2:
        tracking_state = "NO_PERSON"
        is_body_visible = False
        visibility_message = "No person detected. Step into camera view."
    elif lower_vis < 2 and total_visible < 14:
        tracking_state = "PARTIAL_BODY"
        is_body_visible = False
        visibility_message = "Move back so your full body from head to feet is visible."
    else:
        tracking_state = "GOOD_TRACKING"
        is_body_visible = True
        visibility_message = ""

    # Extract 2D/3D joint angles
    actual_angles = AngleCalculator.extract_all_angles(landmarks)

    target_pose = None
    auto_detected = False

    if mode != "auto" and str(pose_id).lower() != "auto" and pose_id:
        try:
            target_pose = db.get_pose_by_id(int(pose_id))
        except (ValueError, TypeError):
            target_pose = None

    # Actual Pose Classification from live landmark geometry
    detected_name, match_score, matched_pose = PoseClassifier.identify_pose(
        actual_angles, all_poses_cache, confidence_threshold=55.0, expected_pose=target_pose
    )

    if not target_pose:
        auto_detected = True
        if matched_pose:
            target_pose = matched_pose
        else:
            target_pose = all_poses_cache[0] if all_poses_cache else None

    if not target_pose:
        return jsonify({
            "status": "success",
            "auto_detected": auto_detected,
            "tracking_state": tracking_state,
            "is_body_visible": is_body_visible,
            "detected_pose": detected_name,
            "detected_pose_id": matched_pose.get("id") if matched_pose else None,
            "target_pose_name": "Unknown",
            "target_pose_id": None,
            "expected_pose_id": None,
            "expected_pose_name": "Unknown",
            "pose_matched": False,
            "match_score": round(match_score, 1),
            "overall_score": 0.0,
            "pose_status": "WAITING",
            "right_wrong_status": "WAITING",
            "is_correct_pose": False,
            "is_hold_valid": False,
            "score_level": "INCORRECT",
            "level_info": settings.SCORE_LEVELS["INCORRECT"],
            "joint_results": [],
            "incorrect_joints": [],
            "critical_incorrect_joints": [],
            "primary_feedback": visibility_message or "Position yourself in camera view to begin.",
            "structured_feedback": [],
            "actual_angles": {k: round(v, 1) for k, v in actual_angles.items()},
        })

    # Posture Evaluation & Scoring against expected target_pose
    posture_result = posture_checker.check_posture(
        target_pose,
        actual_angles,
        is_body_visible=is_body_visible,
        visibility_message=visibility_message,
    )
    overall_score = round(posture_result.get("overall_score", 0.0), 1)

    expected_name = target_pose.get("name", "Unknown")
    expected_clean = expected_name.lower().split("(")[0].strip()
    detected_clean = detected_name.lower().split("(")[0].strip()

    # Determine if detected pose matches expected pose
    pose_matched = (
        (matched_pose and matched_pose.get("id") == target_pose.get("id"))
        or (expected_clean in detected_clean)
        or (detected_clean in expected_clean)
        or ("step" in expected_clean and "surya" in detected_clean)
        or ("transitioning" in detected_clean and expected_clean in detected_clean)
        or (overall_score >= 60.0)
    )

    # 4-State Posture & Hold Validation
    if not is_body_visible:
        pose_status = "WAITING"
        right_wrong_status = "WAITING"
        is_correct = False
        is_hold_valid = False
        primary_fb = visibility_message
    elif not pose_matched and match_score >= 50.0:
        pose_status = "WRONG_POSE"
        right_wrong_status = "WRONG"
        is_correct = False
        is_hold_valid = False
        overall_score = min(overall_score, 45.0)  # Penalize score for performing wrong pose
        primary_fb = f"That looks like {detected_name}. Move into {expected_name} to continue."
    else:
        # User is in target pose family; verify joint tolerances
        crit_incorrect = posture_result.get("critical_incorrect_joints", [])
        if overall_score >= 78.0 and not crit_incorrect:
            pose_status = "CORRECT"
            right_wrong_status = "RIGHT"
            is_correct = True
            is_hold_valid = True
            primary_fb = posture_result.get("primary_feedback") or f"Good form in {expected_name}! Hold steadily."
        else:
            pose_status = "ADJUST"
            right_wrong_status = "ADJUST"
            is_correct = False
            is_hold_valid = False
            primary_fb = posture_result.get("primary_feedback") or "Adjust your alignment to enter valid hold."

    return jsonify({
        "status": "success",
        "auto_detected": auto_detected,
        "tracking_state": tracking_state,
        "is_body_visible": is_body_visible,
        "detected_pose": detected_name,
        "detected_pose_id": matched_pose.get("id") if matched_pose else None,
        "target_pose_name": expected_name,
        "target_pose_id": target_pose.get("id"),
        "expected_pose_id": target_pose.get("id"),
        "expected_pose_name": expected_name,
        "pose_matched": pose_matched,
        "match_score": round(match_score, 1),
        "overall_score": overall_score,
        "pose_status": pose_status,
        "right_wrong_status": right_wrong_status,
        "is_correct_pose": is_correct,
        "is_hold_valid": is_hold_valid,
        "score_level": posture_result.get("score_level", "INCORRECT"),
        "level_info": posture_result.get("level_info", settings.SCORE_LEVELS["INCORRECT"]),
        "joint_results": posture_result.get("joint_results", []),
        "incorrect_joints": posture_result.get("incorrect_joints", []),
        "critical_incorrect_joints": posture_result.get("critical_incorrect_joints", []),
        "primary_feedback": primary_fb,
        "structured_feedback": posture_result.get("structured_feedback", []),
        "actual_angles": {k: round(v, 1) for k, v in actual_angles.items()},
    })


@app.route("/api/save_session", methods=["POST"])
def save_session():
    """Saves completed practice session into SQLite."""
    data = request.json or {}
    user_id = data.get("user_id", 1)
    pose_id = data.get("pose_id", 1)
    duration = int(data.get("duration", 0))
    avg_score = float(data.get("average_score", 0.0))
    final_score = float(data.get("final_score", 0.0))
    hold_duration = int(data.get("hold_duration", 0))
    corrections_count = int(data.get("corrections_count", 0))

    session_id = db.save_practice_session(
        user_id=user_id,
        pose_id=pose_id,
        duration=duration,
        average_score=avg_score,
        final_score=final_score,
        hold_duration=hold_duration,
        corrections_count=corrections_count,
    )

    return jsonify({"status": "success", "session_id": session_id})


@app.route("/api/history/<int:user_id>", methods=["GET"])
def get_history(user_id):
    """Returns practice history for user."""
    pose_filter = request.args.get("pose")
    min_score = request.args.get("min_score", type=float)
    history = db.get_all_practice_history(user_id, pose_filter=pose_filter, min_score=min_score)
    return jsonify(history)


@app.route("/api/stats/<int:user_id>", methods=["GET"])
def get_stats(user_id):
    """Returns lifetime metrics and progress breakdown."""
    stats = db.get_user_stats(user_id)
    progression = db.get_analytics_score_progression(user_id)
    pose_breakdown = db.get_pose_performance_breakdown(user_id)
    return jsonify({
        "stats": stats,
        "progression": progression,
        "pose_breakdown": pose_breakdown,
    })


@app.route("/api/recommendations/<int:user_id>", methods=["GET"])
def get_recommendations(user_id):
    """Returns personalized recommendation feed."""
    recs = recommender.get_recommendations(user_id)
    return jsonify(recs)


@app.route("/api/programs", methods=["GET"])
def get_programs():
    """Returns all 3 learning programs (Foundation, Progress, Mastery) and unlock requirements."""
    user_id = request.args.get("user_id", default=1, type=int)
    unlock_info = session_planner.evaluate_program_unlock(user_id)
    
    programs = [
        {
            "id": "foundation",
            "level": "Beginner",
            "name": "Foundation",
            "subtitle": "Build your body awareness and learn the fundamentals.",
            "description": "Learn essential standing alignment, posture breathing, and basic Surya Namaskar. Ideal for beginners or daily alignment.",
            "target_duration": "15-20 min",
            "unlocked": unlock_info.get("foundation_unlocked", True),
            "exercise_count": 8,
            "focus_options": ["Spinal Mobility", "Basic Balance", "Full Body Awareness"],
        },
        {
            "id": "progress",
            "level": "Intermediate",
            "name": "Progress",
            "subtitle": "Build strength, flexibility, balance and control.",
            "description": "Dynamic flows incorporating Warrior postures, Triangle extensions, and full Surya Namaskar sun salutations.",
            "target_duration": "20-25 min",
            "unlocked": unlock_info.get("progress_unlocked", False),
            "exercise_count": 12,
            "focus_options": ["Hip & Hamstring Mobility", "Core Stability", "Standing Balance"],
        },
        {
            "id": "mastery",
            "level": "Advanced",
            "name": "Mastery",
            "subtitle": "Advanced sequences for strength, mobility, balance and precision.",
            "description": "High-precision backbends, Natarajasana dancer balance, and intense breath-movement synchronization with safety checks.",
            "target_duration": "25-35 min",
            "unlocked": unlock_info.get("mastery_unlocked", False),
            "exercise_count": 14,
            "focus_options": ["Deep Backbends & Extensions", "Advanced Balance & Focus", "Vinyasa Mastery"],
        },
    ]
    return jsonify({"status": "success", "programs": programs, "unlock_info": unlock_info})


@app.route("/api/program/<level>", methods=["GET"])
def get_program_by_level(level):
    """Returns detailed overview for specific level ('beginner', 'intermediate', 'advanced')."""
    user_id = request.args.get("user_id", default=1, type=int)
    level_capitalized = level.capitalize()
    session_plan = session_planner.generate_session(user_id=user_id, level=level_capitalized)
    return jsonify({"status": "success", "program": session_plan})


@app.route("/api/daily-session/<int:user_id>", methods=["GET"])
def get_daily_session(user_id):
    """Generates today's personalized AI-guided yoga practice session."""
    duration = request.args.get("duration", default=20, type=int)
    goal = request.args.get("goal", default="General Fitness", type=str)
    level = request.args.get("level", default="Beginner", type=str)
    focus = request.args.get("focus", default=None, type=str)

    session_plan = session_planner.generate_session(
        user_id=user_id,
        duration_minutes=duration,
        goal=goal,
        level=level,
        focus_area=focus,
    )
    return jsonify({"status": "success", "session": session_plan})


@app.route("/api/session/start", methods=["POST"])
def start_session():
    """Initializes a new guided AI practice session state."""
    data = request.json or {}
    user_id = data.get("user_id", 1)
    duration = int(data.get("duration", 20))
    goal = data.get("goal", "General Fitness")
    level = data.get("level", "Beginner")
    focus = data.get("focus")

    session_plan = session_planner.generate_session(
        user_id=user_id,
        duration_minutes=duration,
        goal=goal,
        level=level,
        focus_area=focus,
    )
    plan_id = db.save_session_plan(session_plan)
    session_plan["id"] = plan_id

    exercises = session_plan.get("exercises", [])
    if exercises:
        coach_engine.load_exercise(exercises[0])
        voice_manager.set_context(session_id=plan_id, pose_id=exercises[0].get("name"))

    return jsonify({
        "status": "success",
        "message": "AI Practice Session Initialized",
        "session_id": plan_id,
        "session_plan": session_plan,
    })


@app.route("/api/session/complete", methods=["POST"])
def complete_session():
    """Saves completed multi-exercise AI guided session."""
    data = request.json or {}
    user_id = data.get("user_id", 1)
    duration_total = int(data.get("total_duration_seconds", 1200))
    avg_accuracy = float(data.get("average_accuracy", 88.0))
    completed_exercises = int(data.get("completed_exercises", 8))
    total_exercises = int(data.get("total_exercises", completed_exercises))
    program_level = data.get("program_level", "Beginner")
    session_plan_id = data.get("session_plan_id", f"plan_{user_id}")
    best_pose = data.get("best_pose", "")
    weakest_joint = data.get("weakest_joint", "")

    # Stop voice coaching when session completes
    voice_manager.on_session_completed()

    # Save to guided_session_logs table
    db.save_guided_session_log(
        user_id=user_id,
        session_plan_id=session_plan_id,
        level=program_level,
        duration_seconds=duration_total,
        avg_accuracy=avg_accuracy,
        completed_poses=completed_exercises,
        total_poses=total_exercises,
        best_pose=best_pose,
        weakest_joint=weakest_joint,
    )

    # Record first pose session entry for history compatibility
    db.save_practice_session(
        user_id=user_id,
        pose_id=1,
        duration=duration_total,
        average_score=avg_accuracy,
        final_score=avg_accuracy,
        hold_duration=duration_total // 2,
        corrections_count=2,
    )

    unlock_eval = session_planner.evaluate_program_unlock(user_id)

    return jsonify({
        "status": "success",
        "message": "AI Session Successfully Completed!",
        "summary": {
            "duration_minutes": round(duration_total / 60, 1),
            "average_accuracy": round(avg_accuracy, 1),
            "completed_exercises": completed_exercises,
            "total_exercises": total_exercises,
            "program_level": program_level,
            "unlock_eval": unlock_eval,
        },
    })


@app.route("/api/progress/<int:user_id>", methods=["GET"])
def get_user_progress(user_id):
    """Returns detailed user wellness progress, program unlock readiness, and streaks."""
    stats = db.get_user_stats(user_id)
    unlock_info = session_planner.evaluate_program_unlock(user_id)
    progression = db.get_analytics_score_progression(user_id)
    pose_breakdown = db.get_pose_performance_breakdown(user_id)

    return jsonify({
        "status": "success",
        "stats": stats,
        "unlock_info": unlock_info,
        "progression": progression,
        "pose_breakdown": pose_breakdown,
    })


@app.route("/api/user/preferences/<int:user_id>", methods=["GET"])
def get_user_preferences(user_id):
    """Retrieves practice preferences for user."""
    prefs = db.get_user_preferences(user_id)
    return jsonify({"status": "success", "preferences": prefs})


@app.route("/api/user/preferences", methods=["POST"])
def update_user_preferences():
    """Updates practice preferences for user."""
    data = request.json or {}
    user_id = data.get("user_id", 1)
    updated = db.set_user_preferences(
        user_id=user_id,
        goal=data.get("goal"),
        level=data.get("level"),
        duration_minutes=data.get("duration_minutes"),
        focus_area=data.get("focus_area"),
        voice_enabled=data.get("voice_enabled"),
        voice_speed=data.get("voice_speed"),
        onboarding_completed=data.get("onboarding_completed"),
    )
    return jsonify({"status": "success", "preferences": updated})


@app.route("/api/coach/message", methods=["POST"])
def coach_message():
    """Processes interactive voice/chat dialogue with AI Yoga Coach."""
    data = request.json or {}
    user_id = data.get("user_id", 1)
    message = data.get("message", "")
    context = data.get("context", {})

    # Save user message
    db.save_coach_conversation(user_id=user_id, role="user", message=message, context=context)

    # Process response
    coach_reply = conversational_coach.process_message(
        user_message=message,
        context=context,
        user_id=user_id,
    )

    # Save coach reply
    db.save_coach_conversation(
        user_id=user_id,
        role="coach",
        message=coach_reply.get("response", ""),
        intent=coach_reply.get("intent", "general"),
        context={"action": coach_reply.get("action")},
    )

    return jsonify({"status": "success", "coach": coach_reply})


@app.route("/api/coach/history/<int:user_id>", methods=["GET"])
def get_coach_history(user_id):
    """Returns recent dialogue turns with AI Yoga Coach."""
    history = db.get_recent_coach_conversations(user_id, limit=20)
    return jsonify({"status": "success", "history": history})


@app.route("/api/session/evaluate_frame", methods=["POST"])
def session_evaluate_frame():
    """
    Evaluates camera landmarks against current exercise in session,
    manages hold validation timer, and returns state & speech cue.
    """
    data = request.json or {}
    landmarks_raw = data.get("landmarks", {})
    exercise = data.get("exercise")

    if exercise:
        if not coach_engine.current_exercise or coach_engine.current_exercise.get("name") != exercise.get("name"):
            coach_engine.load_exercise(exercise)

    if not landmarks_raw:
        return jsonify({"status": "error", "message": "No landmarks provided"}), 400

    landmarks = {}
    total_visible = 0
    for name, lm in landmarks_raw.items():
        vis = float(lm.get("visibility", 0.9))
        if vis >= 0.5:
            total_visible += 1
        landmarks[name] = {
            "x": float(lm.get("x", 0.0)),
            "y": float(lm.get("y", 0.0)),
            "z": float(lm.get("z", 0.0)),
            "visibility": vis,
            "px": int(lm.get("x", 0.0) * 640),
            "py": int(lm.get("y", 0.0) * 480),
        }

    # Tracking & Body Visibility Validation
    key_upper = ["LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_HIP", "RIGHT_HIP"]
    key_lower = ["LEFT_KNEE", "RIGHT_KNEE", "LEFT_ANKLE", "RIGHT_ANKLE"]
    upper_vis = sum(1 for k in key_upper if landmarks.get(k, {}).get("visibility", 0.0) >= 0.5)
    lower_vis = sum(1 for k in key_lower if landmarks.get(k, {}).get("visibility", 0.0) >= 0.4)

    if upper_vis < 2:
        tracking_state = "NO_PERSON"
        is_body_visible = False
        visibility_message = "No person detected. Step into camera view."
    elif lower_vis < 2 and total_visible < 14:
        tracking_state = "PARTIAL_BODY"
        is_body_visible = False
        visibility_message = "Move back so your full body from head to feet is visible."
    else:
        tracking_state = "GOOD_TRACKING"
        is_body_visible = True
        visibility_message = ""

    target_pose = None
    if exercise and exercise.get("target_pose_id"):
        t_id = exercise.get("target_pose_id")
        try:
            target_pose = db.get_pose_by_id(int(t_id))
        except Exception:
            target_pose = None

    actual_angles = AngleCalculator.extract_all_angles(landmarks)
    detected_name, match_score, matched_pose = PoseClassifier.identify_pose(
        actual_angles, all_poses_cache, confidence_threshold=55.0, expected_pose=target_pose
    )

    if not target_pose:
        target_pose = matched_pose or (all_poses_cache[0] if all_poses_cache else None)

    posture_result = posture_checker.check_posture(
        target_pose or {},
        actual_angles,
        is_body_visible=is_body_visible,
        visibility_message=visibility_message,
    )
    frame_eval = coach_engine.evaluate_frame(
        detected_pose_name=detected_name,
        match_score=match_score,
        posture_eval=posture_result,
        is_body_visible=is_body_visible,
    )

    expected_name = (target_pose.get("name") if target_pose else "Yoga Pose")
    exp_clean = expected_name.lower().split("(")[0].strip()
    det_clean = detected_name.lower().split("(")[0].strip()
    pose_matched = (
        (matched_pose and target_pose and matched_pose.get("id") == target_pose.get("id"))
        or (exp_clean in det_clean)
        or (det_clean in exp_clean)
        or ("step" in exp_clean and "surya" in det_clean)
        or ("transitioning" in det_clean and exp_clean in det_clean)
        or (posture_result.get("overall_score", 0.0) >= 60.0)
    )

    is_hold_valid = (
        is_body_visible
        and pose_matched
        and frame_eval.get("is_aligned", False)
        and frame_eval.get("state") == "HOLDING"
    )

    return jsonify({
        "status": "success",
        "evaluation": frame_eval,
        "posture_result": posture_result,
        "tracking_state": tracking_state,
        "is_body_visible": is_body_visible,
        "detected_pose": detected_name,
        "detected_pose_id": matched_pose.get("id") if matched_pose else None,
        "expected_pose_name": expected_name,
        "expected_pose_id": target_pose.get("id") if target_pose else None,
        "pose_matched": pose_matched,
        "match_score": round(match_score, 1),
        "is_hold_valid": is_hold_valid,
        "incorrect_joints": posture_result.get("incorrect_joints", []),
        "critical_incorrect_joints": posture_result.get("critical_incorrect_joints", []),
    })


@app.route("/api/voice/stop", methods=["POST"])
def voice_stop():
    """Immediately cancels active speech and clears voice queue."""
    voice_manager.stop()
    return jsonify({"status": "success", "voice": voice_manager.get_status()})


@app.route("/api/voice/resume", methods=["POST"])
def voice_resume():
    """Resets stopped flag, allowing speech to resume."""
    voice_manager.resume()
    return jsonify({"status": "success", "voice": voice_manager.get_status()})


@app.route("/api/voice/mute", methods=["POST"])
def voice_mute():
    """Mutes voice coaching."""
    voice_manager.mute()
    return jsonify({"status": "success", "voice": voice_manager.get_status()})


@app.route("/api/voice/unmute", methods=["POST"])
def voice_unmute():
    """Unmutes voice coaching."""
    voice_manager.unmute()
    return jsonify({"status": "success", "voice": voice_manager.get_status()})


@app.route("/api/voice/toggle_mute", methods=["POST"])
def voice_toggle_mute():
    """Toggles muted state."""
    is_muted = voice_manager.toggle_mute()
    return jsonify({"status": "success", "is_muted": is_muted, "voice": voice_manager.get_status()})


@app.route("/api/voice/interrupt", methods=["POST"])
def voice_interrupt():
    """Interrupts active TTS when practitioner starts speaking."""
    voice_manager.interrupt_for_listening()
    return jsonify({"status": "success", "voice": voice_manager.get_status()})


@app.route("/api/voice/status", methods=["GET"])
def voice_status():
    """Returns real-time voice controller status."""
    return jsonify({"status": "success", "voice": voice_manager.get_status()})


@app.route("/api/voice/speak", methods=["POST"])
def voice_speak():
    """Queues a validated speech request."""
    data = request.json or {}
    text = data.get("text", "")
    priority_str = data.get("priority", "NORMAL").upper()
    priority = getattr(Priority, priority_str, Priority.NORMAL)
    event_key = data.get("event_key", "")
    pose_id = data.get("pose_id")
    session_id = data.get("session_id")

    accepted = voice_manager.speak(
        text=text,
        priority=priority,
        event_key=event_key,
        pose_id=pose_id,
        session_id=session_id,
    )
    status = "success" if accepted else "rejected"
    return jsonify({"status": status, "accepted": accepted, "voice": voice_manager.get_status()})


# ==========================================
# PWA & Web Manifest
# ==========================================

@app.route("/manifest.json")
def pwa_manifest():
    """Serves PWA web app manifest."""
    return send_from_directory("static", "manifest.json", mimetype="application/manifest+json")


# ==========================================
# Real Subscription & Payment Endpoints
# ==========================================

@app.route("/api/payment/config", methods=["GET"])
def get_payment_config():
    """Returns safe client-side payment configuration. Never exposes secret key."""
    return jsonify({
        "status": "success",
        "config": razorpay_client.get_public_config()
    })


@app.route("/api/payment/create-order", methods=["POST"])
def create_payment_order():
    """
    Creates an authorized Razorpay payment order.
    In demo/test mode: generates a verified test order with transparent test token.
    In live mode: communicates directly with Razorpay Orders API.
    """
    data = request.json or {}
    user_id = data.get("user_id", 1)
    plan_type = data.get("plan_type", "PRO_MONTHLY")
    
    order = razorpay_client.create_order(
        plan_type=plan_type,
        user_id=user_id,
        user_email=data.get("email", ""),
        user_name=data.get("name", "")
    )
    
    if order.get("status") == "success":
        # Record pending order in database
        db.create_payment(
            user_id=user_id,
            order_id=order["order_id"],
            amount=order["amount"],
            currency=order.get("currency", "INR"),
            provider="razorpay"
        )
        return jsonify(order)
    return jsonify({"status": "failed", "message": "Failed to generate payment order"}), 400


@app.route("/api/payment/verify", methods=["POST"])
def verify_payment():
    """
    Server-side cryptographic verification of Razorpay payment signature.
    Prevents client-side spoofing; activates Pro subscription only upon valid HMAC match.
    """
    data = request.json or {}
    user_id = data.get("user_id", 1)
    order_id = data.get("order_id", "").strip()
    payment_id = data.get("payment_id", "").strip()
    signature = data.get("signature", "").strip()
    plan_type = data.get("plan_type", "PRO_MONTHLY")
    
    if not order_id or not payment_id or not signature:
        return jsonify({
            "status": "failed", 
            "message": "Missing required verification parameters (order_id, payment_id, signature)"
        }), 400

    # Strict server-side HMAC-SHA256 signature verification
    is_valid = razorpay_client.verify_payment_signature(order_id, payment_id, signature)
    
    if is_valid:
        # Mark payment as captured in database
        db.update_payment_status(order_id, status="captured", payment_id=payment_id, signature=signature)
        
        # Calculate duration based on plan
        duration_days = 365 if "ANNUAL" in plan_type else 30
        
        # Activate Pro subscription in database
        db.create_subscription(
            user_id=user_id,
            plan="PRO",
            status="ACTIVE",
            provider="razorpay",
            provider_customer_id=f"cust_{user_id}",
            provider_subscription_id=payment_id,
            duration_days=duration_days
        )
        
        active_sub = db.get_active_subscription(user_id)
        logger.info(f"Pro subscription successfully activated for user {user_id} via order {order_id}")
        return jsonify({
            "status": "success",
            "message": "Payment verified and Pro subscription activated!",
            "is_pro": True,
            "subscription": active_sub
        })
    else:
        # Mark payment as failed in database
        db.update_payment_status(order_id, status="failed", payment_id=payment_id, signature=signature)
        logger.warning(f"Payment verification failed for order {order_id}")
        return jsonify({
            "status": "failed",
            "message": "Payment signature verification failed. Your account was not charged."
        }), 400


@app.route("/api/payment/webhook", methods=["POST"])
def payment_webhook():
    """Handles incoming Razorpay asynchronous webhook notifications."""
    event_data = request.json or {}
    event_type = event_data.get("event")
    logger.info(f"Received Razorpay webhook event: {event_type}")
    
    if event_type == "payment.captured":
        payload = event_data.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payload.get("order_id")
        payment_id = payload.get("id")
        if order_id:
            db.update_payment_status(order_id, status="captured", payment_id=payment_id)
    elif event_type == "payment.failed":
        payload = event_data.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payload.get("order_id")
        if order_id:
            db.update_payment_status(order_id, status="failed")

    return jsonify({"status": "received"}), 200


@app.route("/api/subscription/<int:user_id>", methods=["GET"])
def get_user_subscription(user_id):
    """Retrieves user subscription and Pro entitlement status."""
    sub = db.get_active_subscription(user_id)
    is_pro = db.is_user_pro(user_id)
    return jsonify({
        "status": "success",
        "is_pro": is_pro,
        "subscription": sub
    })


@app.route("/api/subscription/cancel", methods=["POST"])
def cancel_user_subscription():
    """Cancels active recurring user subscription."""
    data = request.json or {}
    user_id = data.get("user_id", 1)
    sub = db.get_active_subscription(user_id)
    if sub and sub.get("id"):
        db.cancel_subscription(sub["id"])
        return jsonify({
            "status": "success", 
            "message": "Subscription cancelled. Your Pro access remains active until the end of your billing cycle."
        })
    return jsonify({"status": "failed", "message": "No active subscription found to cancel"}), 404



def find_available_port(preferred_port: int = 8080) -> int:
    """Finds first available port starting from preferred_port."""
    for p in [preferred_port, 8081, 8082, 8085, 8088]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", p))
                return p
        except OSError:
            continue
    return preferred_port


if __name__ == "__main__":
    local_ip = get_local_ip()
    target_port = int(os.environ.get("PORT", 8080))
    port = find_available_port(target_port)

    print("=" * 65)
    print("   [KI.AI] AI-Powered Yoga & Posture Intelligence")
    print("=" * 65)
    print(f"   * Local URL:             http://localhost:{port}")
    print(f"   * Shareable Network URL: http://{local_ip}:{port}")
    print("   * Default Demo Account:  abhilash@ki.ai  (Password: password123)")
    print("=" * 65)

    app.run(host="0.0.0.0", port=port, debug=False)
