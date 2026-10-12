"""
KI.AI Web Application Server.
AI-Powered Yoga & Posture Intelligence.
Serves full browser interface on port 8080 with real-time pose checking,
Surya Yoga sequence, user authentication, and SQLite persistence.
"""

import hmac
import json
import logging
import os
import socket
import threading
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, session
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
from payment.entitlements import EntitlementService
from coach.kiki import KikiService, KikiCharacterState, determine_kiki_state
from coach.session_controller import PracticeSessionController, SessionLifecycleState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates", static_folder="static")

# Production Secret Key & Session Cookie Security
app.secret_key = os.environ.get("SECRET_KEY", "ki_ai_production_secret_key_change_in_live")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

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
conversational_coach = ConversationalCoach(db=db)
voice_manager = get_voice_manager()
razorpay_client = get_razorpay_client()
kiki_service = KikiService(db=db)

# Thread-safe in-memory cache for catalog poses
_poses_cache_lock = threading.Lock()
all_poses_cache = db.get_all_poses()


def get_cached_poses() -> List[Dict[str, Any]]:
    """Returns the cached list of all yoga poses, reloading from DB if empty."""
    global all_poses_cache
    with _poses_cache_lock:
        if not all_poses_cache:
            all_poses_cache = db.get_all_poses()
        return all_poses_cache


def refresh_poses_cache() -> List[Dict[str, Any]]:
    """Refreshes the in-memory poses cache directly from SQLite."""
    global all_poses_cache
    with _poses_cache_lock:
        all_poses_cache = db.get_all_poses()
        return all_poses_cache


# Per-user isolated CoachEngine registry to prevent concurrent state crosstalk
_coach_registry: Dict[int, CoachEngine] = {}
_coach_registry_lock = threading.Lock()


def get_coach_engine_for_user(user_id: int = 1) -> CoachEngine:
    """Returns an isolated CoachEngine instance for the given user."""
    with _coach_registry_lock:
        if user_id not in _coach_registry:
            _coach_registry[user_id] = CoachEngine()
        return _coach_registry[user_id]


# Backward-compatible global coach_engine reference for single-user desktop code
coach_engine = get_coach_engine_for_user(1)

# Per-user isolated PracticeSessionController registry
_session_controller_registry: Dict[int, PracticeSessionController] = {}
_session_controller_lock = threading.Lock()


def get_session_controller_for_user(user_id: int = 1) -> Optional[PracticeSessionController]:
    """Returns active PracticeSessionController instance for user if present."""
    with _session_controller_lock:
        return _session_controller_registry.get(user_id)


def set_session_controller_for_user(user_id: int, controller: PracticeSessionController) -> PracticeSessionController:
    """Registers an active PracticeSessionController instance for user."""
    with _session_controller_lock:
        _session_controller_registry[user_id] = controller
        return controller


def clear_session_controller_for_user(user_id: int):
    """Clears user session controller on session complete or cancel."""
    with _session_controller_lock:
        _session_controller_registry.pop(user_id, None)



def check_user_access(target_user_id: int) -> Tuple[bool, Optional[str]]:
    """
    Validates user authorization for user-specific resources (IDOR defense).
    Returns (authorized: bool, error_message: Optional[str]).
    """
    sess_uid = session.get("user_id")
    is_admin = session.get("is_admin", False)

    if sess_uid is not None:
        try:
            if is_admin or int(sess_uid) == int(target_user_id):
                return True, None
        except (ValueError, TypeError):
            pass
        return False, "Access denied: Unauthorized access to requested user resource."

    # If no active session, allow default demo users (ID 1 Abhilash, ID 2 Guest) only if demo mode is active
    demo_allowed = os.environ.get("KI_AI_DEMO_MODE", "true").strip().lower() in {"true", "1", "yes"}
    if demo_allowed and int(target_user_id) in (1, 2):
        return True, None

    return False, "Authentication required to access user resource."


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
    """Renders the KI.AI Admin Console (protected by authentication & admin authorization)."""
    auth_header = request.headers.get("Authorization", "")
    bearer_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
    admin_token = request.args.get("admin_token") or request.headers.get("X-Admin-Token") or bearer_token
    configured_token = os.environ.get("ADMIN_TOKEN", "").strip()


    is_authorized = False
    if session.get("is_admin"):
        is_authorized = True
    elif configured_token and admin_token and hmac.compare_digest(admin_token, configured_token):
        is_authorized = True
    elif not configured_token:
        sess_user_id = session.get("user_id")
        if sess_user_id:
            u = db.get_user_by_id(sess_user_id)
            if u and u.get("is_admin"):
                is_authorized = True

    if not is_authorized:
        return jsonify({
            "status": "error",
            "message": "Access denied: Administrative privileges required."
        }), 403

    return render_template("admin.html")


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    """Serves static assets including SVG pose figures and images."""
    return send_from_directory(str(Path("assets").resolve()), filename)


# Contract for professional per-pose reference photographs.
# Drop one realistic photo per pose into static/images/poses/ using the
# basename below (any of .jpg/.jpeg/.webp/.png). The frontend discovers
# files through GET /api/pose-photos, so no code change is needed when
# photos are added later. Until then the UI falls back to the bundled
# illustrations — it never claims a photo exists when it does not.
POSE_PHOTO_BASENAMES = {
    1: "tadasana-mountain",
    2: "virabhadrasana-warrior-ii",
    3: "vrikshasana-tree",
    4: "trikonasana-triangle",
    5: "utkatasana-chair",
    6: "bhujangasana-cobra",
    7: "balasana-child",
    8: "adho-mukha-svanasana-downdog",
    9: "setu-bandhasana-bridge",
    10: "dhanurasana-bow",
    11: "natarajasana-dancer",
    12: "sukhasana-easy",
    13: "surya-namaskar-01-pranamasana",
    14: "surya-namaskar-02-hasta-uttanasana",
    15: "surya-namaskar-03-uttanasana",
    16: "surya-namaskar-04-ashwa-sanchalanasana",
    17: "surya-namaskar-05-dandasana-plank",
    18: "surya-namaskar-06-ashtanga-namaskara",
    19: "surya-namaskar-07-bhujangasana",
    20: "surya-namaskar-08-parvatasana",
    21: "surya-namaskar-09-ashwa-sanchalanasana",
    22: "surya-namaskar-10-uttanasana",
    23: "surya-namaskar-11-hasta-uttanasana",
    24: "surya-namaskar-12-pranamasana",
}
POSE_PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".webp", ".png")


@app.route("/api/pose-photos", methods=["GET"])
def pose_photos():
    """
    Returns per-pose reference photograph URLs for photo files that
    genuinely exist in static/images/poses/. Poses without a photo file
    are omitted so the frontend can fall back to bundled illustrations.
    Response: {status, photos: {pose_id: url}, count}.
    """
    poses_dir = Path(app.static_folder) / "images" / "poses"
    photos: Dict[str, str] = {}
    if poses_dir.is_dir():
        for pose_id, basename in POSE_PHOTO_BASENAMES.items():
            for ext in POSE_PHOTO_EXTENSIONS:
                candidate = poses_dir / f"{basename}{ext}"
                if candidate.is_file():
                    photos[str(pose_id)] = f"/static/images/poses/{basename}{ext}"
                    break
    return jsonify({"status": "success", "photos": photos, "count": len(photos)})


@app.route("/api/poses", methods=["GET"])
def get_poses():
    """Returns all yoga poses with rules."""
    poses = refresh_poses_cache()
    return jsonify(poses)


@app.route("/api/surya", methods=["GET"])
def get_surya_poses():
    """Returns 12-step Surya Namaskar sequence."""
    surya = db.get_surya_namaskar_poses()
    return jsonify(surya)


@app.route("/api/login", methods=["POST"])
def login():
    """Authenticates user with email and password with secure session binding."""
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", "")).strip()

    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required."}), 400

    success, msg, user = db.authenticate_user(email, password)
    if success and user:
        session["user_id"] = user["id"]
        session["user_email"] = user["email"]
        session["is_admin"] = bool(user.get("is_admin", 0))
        return jsonify({"status": "success", "message": msg, "user": user})
    return jsonify({"status": "error", "message": msg}), 401


@app.route("/api/logout", methods=["POST", "GET"])
def logout():
    """Clears active session on logout."""
    session.clear()
    return jsonify({"status": "success", "message": "Logged out successfully."})


@app.route("/api/me", methods=["GET"])
def get_session_user():
    """
    Returns the currently authenticated session user (frontend contract:
    GET /api/me -> {status, authenticated: bool, user: dict|null}).
    Read-only; used by the SPA to restore auth state after reload and to
    distinguish authenticated vs unauthenticated UI. Never exposes hashes.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "success", "authenticated": False, "user": None})
    try:
        user = db.get_user_by_id(int(user_id))
    except (ValueError, TypeError):
        user = None
    if not user:
        session.clear()
        return jsonify({"status": "success", "authenticated": False, "user": None})
    return jsonify({"status": "success", "authenticated": True, "user": user})


@app.route("/api/auth/google", methods=["GET"])
def auth_google_redirect():
    """
    Initiates Google OAuth 2.0 Authorization Code flow.
    Generates a cryptographically random state parameter for CSRF mitigation,
    stores it in the server session, and redirects to Google's consent screen.
    """
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        return jsonify({
            "status": "error",
            "message": "Google Sign-In is not configured yet. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file.",
            "setup_instructions": {
                "step_1": "Create OAuth 2.0 Client ID in Google Cloud Console",
                "step_2": f"Set Authorized redirect URIs to {settings.GOOGLE_REDIRECT_URI}",
                "step_3": "Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env file",
            },
        }), 503

    # Generate random state to protect against CSRF attacks
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    session.modified = True

    params = {
        "client_id": client_id,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    query_string = requests.compat.urlencode(params)
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"
    return redirect(google_auth_url)


@app.route("/api/auth/google/callback", methods=["GET"])
def auth_google_callback():
    """
    Handles the callback redirect from Google OAuth 2.0.
    Validates CSRF state, exchanges authorization code for tokens,
    retrieves user profile from Google, logs user in, and redirects to app.
    """
    error = request.args.get("error")
    if error:
        logger.warning(f"Google OAuth authorization denied or error: {error}")
        return redirect("/?auth_error=" + requests.compat.quote_plus(f"Google Sign-In was cancelled or denied: {error}"))

    code = request.args.get("code")
    state = request.args.get("state")
    saved_state = session.pop("oauth_state", None)

    # Validate state parameter against CSRF
    if not state or not saved_state or not secrets.compare_digest(state, saved_state):
        logger.warning("Google OAuth state mismatch (possible CSRF attack).")
        return redirect("/?auth_error=" + requests.compat.quote_plus("Security verification failed (state mismatch). Please try again."))

    if not code:
        return redirect("/?auth_error=" + requests.compat.quote_plus("No authorization code received from Google."))

    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET
    if not client_id or not client_secret:
        return redirect("/?auth_error=" + requests.compat.quote_plus("Google OAuth credentials missing on server."))

    try:
        # Exchange authorization code for tokens
        token_resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        if token_resp.status_code != 200:
            logger.error(f"Failed to exchange Google OAuth code: {token_resp.text}")
            return redirect("/?auth_error=" + requests.compat.quote_plus("Failed to exchange authentication code with Google."))

        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return redirect("/?auth_error=" + requests.compat.quote_plus("No access token received from Google."))

        # Retrieve user profile from Google UserInfo endpoint
        userinfo_resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if userinfo_resp.status_code != 200:
            logger.error(f"Failed to fetch Google userinfo: {userinfo_resp.text}")
            return redirect("/?auth_error=" + requests.compat.quote_plus("Failed to retrieve profile from Google."))

        user_info = userinfo_resp.json()
        google_id = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name") or user_info.get("given_name") or (email.split("@")[0] if email else "User")
        picture = user_info.get("picture")

        if not email or not google_id:
            return redirect("/?auth_error=" + requests.compat.quote_plus("Google account does not provide an email address."))

        # Authenticate or provision in SQLite database
        success, msg, user = db.get_or_create_google_user(
            email=email,
            name=name,
            google_id=google_id,
            avatar_url=picture,
        )
        if not success or not user:
            return redirect("/?auth_error=" + requests.compat.quote_plus(msg or "Failed to authenticate user profile."))

        # Set Flask session
        session.clear()
        session["user_id"] = user["id"]
        session["is_admin"] = bool(user.get("is_admin", 0))
        session.permanent = True
        logger.info(f"User {user['id']} ('{email}') authenticated successfully via Google.")

        return redirect("/?google_auth=success")

    except requests.RequestException as exc:
        logger.error(f"Network error during Google OAuth callback: {exc}")
        return redirect("/?auth_error=" + requests.compat.quote_plus("Network error communicating with Google servers."))
    except Exception as exc:
        logger.error(f"Unexpected error during Google OAuth callback: {exc}")
        return redirect("/?auth_error=" + requests.compat.quote_plus("Internal server error during Google Sign-In."))


@app.route("/api/beta/signup", methods=["POST"])
def beta_signup():
    """
    Accepts waitlist signups for future modules (e.g. Karate AI).
    Validates input and records signups safely without disrupting core tables.
    """
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    program = str(data.get("program", "karate")).strip().lower()
    if not email or "@" not in email or "." not in email:
        return jsonify({"status": "error", "message": "A valid email address is required."}), 400
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS beta_waitlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    program TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(email, program)
                )
                """
            )
            cursor.execute(
                "INSERT OR IGNORE INTO beta_waitlist (email, program) VALUES (?, ?)",
                (email, program)
            )
            conn.commit()
        return jsonify({"status": "success", "message": f"Successfully joined the {program} beta waitlist!"}), 201
    except Exception as e:
        logger.error(f"Beta signup error: {e}")
        return jsonify({"status": "error", "message": "Failed to record beta signup."}), 500


@app.route("/api/register", methods=["POST"])
def register():
    """Registers a new user profile with input validation."""
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", "")).strip()
    try:
        age = int(data.get("age", 25))
    except (ValueError, TypeError):
        age = 25
    experience = str(data.get("experience", "Beginner")).strip()
    goal = str(data.get("goal", "General Fitness")).strip()

    if not name or not email or not password:
        return jsonify({"status": "error", "message": "Full name, email, and password are required."}), 400

    success, msg, user = db.register_user(
        name=name,
        email=email,
        password=password,
        age=age,
        experience=experience,
        goal=goal,
    )

    if success and user:
        session["user_id"] = user["id"]
        session["user_email"] = user["email"]
        session["is_admin"] = bool(user.get("is_admin", 0))
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
    visibilities = []
    for name, lm in landmarks_raw.items():
        vis = float(lm.get("visibility", 0.9)) if isinstance(lm, dict) else 0.0
        visibilities.append(vis)
        if vis >= 0.5:
            total_visible += 1
        landmarks[name] = {
            "x": float(lm.get("x", 0.0)) if isinstance(lm, dict) else 0.0,
            "y": float(lm.get("y", 0.0)) if isinstance(lm, dict) else 0.0,
            "z": float(lm.get("z", 0.0)) if isinstance(lm, dict) else 0.0,
            "visibility": vis,
            "px": int(float(lm.get("x", 0.0)) * 640) if isinstance(lm, dict) else 0,
            "py": int(float(lm.get("y", 0.0)) * 480) if isinstance(lm, dict) else 0,
        }

    tracking_confidence = round((sum(visibilities) / len(visibilities)) if visibilities else 0.0, 2)

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

    user_id = session.get("user_id") or data.get("user_id") or 1
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        user_id = 1

    controller = get_session_controller_for_user(user_id)
    session_snapshot = None
    if controller:
        session_snapshot = controller.tick_evaluation(
            is_valid_hold=is_hold_valid,
            score=overall_score,
            pose_matched=pose_matched,
            is_body_visible=is_body_visible,
        )

    return jsonify({
        "status": "success",
        "auto_detected": auto_detected,
        "tracking_confidence": tracking_confidence,
        "tracking_state": tracking_state,
        "is_body_visible": is_body_visible,
        "accuracy_valid": is_body_visible,
        "session_id": session_snapshot["session_id"] if session_snapshot else None,
        "session_state": session_snapshot["session_state"] if session_snapshot else ("HOLDING" if is_hold_valid else "DETECTING"),
        "current_pose": session_snapshot["current_pose"] if session_snapshot else None,
        "next_pose": session_snapshot["next_pose"] if session_snapshot else None,
        "sequence_progress": session_snapshot["sequence_progress"] if session_snapshot else None,
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
    """Saves completed practice session into SQLite with validation and IDOR protection."""
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id", 1))
        pose_id = int(data.get("pose_id", 1))
        duration = max(0, int(data.get("duration", 0)))
        avg_score = max(0.0, min(100.0, float(data.get("average_score", 0.0))))
        final_score = max(0.0, min(100.0, float(data.get("final_score", 0.0))))
        hold_duration = max(0, int(data.get("hold_duration", 0)))
        corrections_count = max(0, int(data.get("corrections_count", 0)))
    except (ValueError, TypeError) as e:
        return jsonify({"status": "error", "message": f"Invalid numeric parameters: {e}"}), 400

    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"status": "error", "message": f"User ID {user_id} does not exist."}), 404

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
    """Returns practice history for user (IDOR protected)."""
    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"status": "error", "message": f"User ID {user_id} not found."}), 404

    pose_filter = request.args.get("pose")
    min_score = request.args.get("min_score", type=float)
    history = db.get_all_practice_history(user_id, pose_filter=pose_filter, min_score=min_score)
    return jsonify(history)


@app.route("/api/stats/<int:user_id>", methods=["GET"])
def get_stats(user_id):
    """Returns lifetime metrics and progress breakdown (IDOR protected)."""
    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"status": "error", "message": f"User ID {user_id} not found."}), 404

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
    """Returns personalized recommendation feed (IDOR protected)."""
    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"status": "error", "message": f"User ID {user_id} not found."}), 404

    recs = recommender.get_recommendations(user_id)
    return jsonify(recs)



@app.route("/api/programs", methods=["GET"])
def get_programs():
    """Returns all 3 learning programs (Foundation, Progress, Mastery) and unlock requirements."""
    try:
        user_id = int(request.args.get("user_id", default=1))
    except (ValueError, TypeError):
        user_id = 1

    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

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
    try:
        user_id = int(request.args.get("user_id", default=1))
    except (ValueError, TypeError):
        user_id = 1

    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

    level_capitalized = level.capitalize()
    session_plan = session_planner.generate_session(user_id=user_id, level=level_capitalized)
    return jsonify({"status": "success", "program": session_plan})


@app.route("/api/daily-session/<int:user_id>", methods=["GET"])
def get_daily_session(user_id):
    """Generates today's personalized AI-guided yoga practice session (IDOR protected)."""
    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

    try:
        duration = int(request.args.get("duration", default=20))
    except (ValueError, TypeError):
        duration = 20
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
    """Initializes a new guided AI practice session state with isolated per-user coach."""
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id", 1))
        duration = int(data.get("duration", 20))
    except (ValueError, TypeError):
        user_id = 1
        duration = 20

    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

    goal = str(data.get("goal", "General Fitness"))
    level = str(data.get("level", "Beginner"))
    focus = data.get("focus")

    custom_exercises = data.get("exercises") or data.get("roadmap")
    if custom_exercises and isinstance(custom_exercises, list):
        plan_id = str(data.get("session_id") or f"plan_{user_id}_{int(time.time())}")
        session_plan = {
            "id": plan_id,
            "title": str(data.get("title", f"{level} Yoga Sequence")),
            "level": level,
            "goal": goal,
            "exercises": custom_exercises,
            "roadmap": custom_exercises,
            "total_exercises": len(custom_exercises),
            "target_duration_minutes": duration,
        }
    else:
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
    controller = PracticeSessionController(
        session_id=str(plan_id),
        user_id=user_id,
        title=session_plan.get("title", "AI Practice Session"),
        level=level,
        goal=goal,
        exercises=exercises,
        db=db,
    )
    set_session_controller_for_user(user_id, controller)

    if exercises:
        engine = get_coach_engine_for_user(user_id)
        engine.load_exercise(exercises[0])
        voice_manager.set_context(session_id=plan_id, pose_id=exercises[0].get("name"))

    snapshot = controller.get_snapshot()

    return jsonify({
        "status": "success",
        "message": "AI Practice Session Initialized",
        "session_id": plan_id,
        "session_plan": session_plan,
        "session_state": snapshot["session_state"],
        "current_pose": snapshot["current_pose"],
        "next_pose": snapshot["next_pose"],
        "sequence_progress": snapshot["sequence_progress"],
    })


@app.route("/api/session/current", methods=["GET"])
def get_current_session():
    """Returns active session snapshot (supporting browser refresh and reload)."""
    user_id = session.get("user_id") or request.args.get("user_id") or 1
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        user_id = 1

    controller = get_session_controller_for_user(user_id)
    if not controller:
        return jsonify({"status": "idle", "active": False, "message": "No active practice session in progress."})
    snap = controller.get_snapshot()
    return jsonify({
        "status": "success",
        "active": True,
        "step_index": snap.get("sequence_progress", {}).get("current_index", 0),
        "session": snap,
        **snap,
    })


@app.route("/api/session/next", methods=["POST"])
def advance_session_pose():
    """Manually advances practice session to next asana in sequence."""
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id") or session.get("user_id") or 1)
    except (ValueError, TypeError):
        user_id = 1

    controller = get_session_controller_for_user(user_id)
    if not controller:
        return jsonify({"status": "error", "message": "No active session in progress."}), 404

    snap = controller.skip_current_asana()
    engine = get_coach_engine_for_user(user_id)
    if controller.current_step:
        engine.load_exercise(controller.current_step.to_dict())

    return jsonify({
        "status": "success",
        "step_index": snap.get("sequence_progress", {}).get("current_index", 0),
        "session": snap,
        **snap,
    })


@app.route("/api/session/skip", methods=["POST"])
def skip_session_pose():
    """Skips current posture in sequence."""
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id") or session.get("user_id") or 1)
    except (ValueError, TypeError):
        user_id = 1

    controller = get_session_controller_for_user(user_id)
    if not controller:
        return jsonify({"status": "error", "message": "No active session in progress."}), 404

    snap = controller.skip_current_asana()
    engine = get_coach_engine_for_user(user_id)
    if controller.current_step:
        engine.load_exercise(controller.current_step.to_dict())

    return jsonify({
        "status": "success",
        "step_index": snap.get("sequence_progress", {}).get("current_index", 0),
        "session": snap,
        **snap,
    })


@app.route("/api/session/pause", methods=["POST"])
def pause_session():
    """Pauses active session countdown."""
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id") or session.get("user_id") or 1)
    except (ValueError, TypeError):
        user_id = 1

    reason = str(data.get("reason", "Practitioner requested pause"))
    controller = get_session_controller_for_user(user_id)
    if not controller:
        return jsonify({"status": "error", "message": "No active session in progress."}), 404

    snap = controller.pause_session(reason=reason)
    return jsonify({
        "status": "success",
        "is_paused": snap.get("is_paused", True),
        "session": snap,
        **snap,
    })


@app.route("/api/session/resume", methods=["POST"])
def resume_session():
    """Resumes active session countdown."""
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id") or session.get("user_id") or 1)
    except (ValueError, TypeError):
        user_id = 1

    controller = get_session_controller_for_user(user_id)
    if not controller:
        return jsonify({"status": "error", "message": "No active session in progress."}), 404

    snap = controller.resume_session()
    return jsonify({
        "status": "success",
        "is_paused": snap.get("is_paused", False),
        "session": snap,
        **snap,
    })


@app.route("/api/session/camera_error", methods=["POST"])
def session_camera_error():
    """Notifies backend of camera disconnection to safely pause countdown without loss of data."""
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id") or session.get("user_id") or 1)
    except (ValueError, TypeError):
        user_id = 1

    err_msg = str(data.get("error", "Webcam interrupted"))
    controller = get_session_controller_for_user(user_id)
    if controller:
        controller.handle_camera_error(err_msg)
        snap = controller.get_snapshot()
        return jsonify({
            "status": "success",
            "tracking_warning": err_msg,
            "session": snap,
            **snap,
        })
    return jsonify({"status": "success", "tracking_warning": err_msg, "message": "Recorded camera failure."})


@app.route("/api/session/complete", methods=["POST"])
def complete_session():
    """Saves completed multi-exercise AI guided session."""
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id", 1))
        duration_total = max(0, int(data.get("total_duration_seconds", 0)))
        avg_accuracy = max(0.0, min(100.0, float(data.get("average_accuracy", 0.0))))
        completed_exercises = max(0, int(data.get("completed_exercises", 0)))
        total_exercises = max(completed_exercises, int(data.get("total_exercises", completed_exercises)))
        pose_id = max(1, int(data.get("pose_id", 1)))
        hold_duration = max(0, int(data.get("hold_duration", duration_total)))
        corrections_count = max(0, int(data.get("corrections_count", 0)))
    except (ValueError, TypeError) as e:
        return jsonify({"status": "error", "message": f"Invalid parameter: {e}"}), 400

    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"status": "error", "message": f"User ID {user_id} not found."}), 404

    program_level = str(data.get("program_level", "Beginner"))[:32]
    session_plan_id = str(data.get("session_plan_id", f"plan_{user_id}"))[:64]
    best_pose = str(data.get("best_pose", ""))[:64]
    weakest_joint = str(data.get("weakest_joint", ""))[:64]

    # Stop voice coaching when session completes
    voice_manager.on_session_completed()

    # Clear active session controller
    clear_session_controller_for_user(user_id)

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
        pose_id=pose_id,
        duration=duration_total,
        average_score=avg_accuracy,
        final_score=avg_accuracy,
        hold_duration=hold_duration,
        corrections_count=corrections_count,
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
    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"status": "error", "message": f"User ID {user_id} not found."}), 404

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
    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"status": "error", "message": f"User ID {user_id} not found."}), 404

    prefs = db.get_user_preferences(user_id)
    return jsonify({"status": "success", "preferences": prefs})


@app.route("/api/user/preferences", methods=["POST"])
def update_user_preferences():
    """Updates practice preferences for user."""
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id", 1))
    except (ValueError, TypeError):
        user_id = 1

    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

    duration_mins = data.get("duration_minutes")
    if duration_mins is not None:
        try:
            duration_mins = max(5, min(120, int(duration_mins)))
        except (ValueError, TypeError):
            duration_mins = 20

    updated = db.set_user_preferences(
        user_id=user_id,
        goal=data.get("goal"),
        level=data.get("level"),
        duration_minutes=duration_mins,
        focus_area=data.get("focus_area"),
        voice_enabled=data.get("voice_enabled"),
        voice_speed=data.get("voice_speed"),
        onboarding_completed=data.get("onboarding_completed"),
    )
    return jsonify({"status": "success", "preferences": updated})


@app.route("/api/coach/message", methods=["POST"])
def coach_message():
    """Processes interactive voice/chat dialogue with AI Yoga Coach."""
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id", 1))
    except (ValueError, TypeError):
        user_id = 1

    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

    message = str(data.get("message", "")).strip()[:1000]
    context = data.get("context", {})
    if not isinstance(context, dict):
        context = {}

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
    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "error", "message": auth_err}), 403

    history = db.get_recent_coach_conversations(user_id, limit=20)
    return jsonify({"status": "success", "history": history})



@app.route("/api/session/evaluate_frame", methods=["POST"])
def session_evaluate_frame():
    """
    Evaluates camera landmarks against current exercise in session,
    manages hold validation timer, and returns state & speech cue.
    Uses per-user coach engine to isolate practice state across concurrent users.
    """
    data = request.get_json(silent=True) or {}
    landmarks_raw = data.get("landmarks", {})
    exercise = data.get("exercise")
    try:
        user_id = int(data.get("user_id", 1))
    except (ValueError, TypeError):
        user_id = 1

    engine = get_coach_engine_for_user(user_id)
    controller = get_session_controller_for_user(user_id)

    if not landmarks_raw or not isinstance(landmarks_raw, (dict, list)):
        return jsonify({"status": "error", "message": "No landmarks provided"}), 400

    if isinstance(landmarks_raw, list):
        converted = {}
        for lm in landmarks_raw:
            if isinstance(lm, dict) and "name" in lm:
                converted[lm["name"]] = lm
        landmarks_raw = converted

    landmarks = {}
    total_visible = 0
    visibilities = []
    for name, lm in landmarks_raw.items():
        if not isinstance(lm, dict):
            continue
        try:
            vis = float(lm.get("visibility", 0.9))
            x = float(lm.get("x", 0.0))
            y = float(lm.get("y", 0.0))
            z = float(lm.get("z", 0.0))
        except (ValueError, TypeError):
            continue

        visibilities.append(vis)
        if vis >= 0.5:
            total_visible += 1
        landmarks[name] = {
            "x": x,
            "y": y,
            "z": z,
            "visibility": vis,
            "px": int(x * 640),
            "py": int(y * 480),
        }

    tracking_confidence = round((sum(visibilities) / len(visibilities)) if visibilities else 0.0, 2)

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

    # Synchronize target pose with controller or exercise param
    target_pose = None
    if controller and controller.current_step:
        target_pose = db.get_pose_by_id(controller.current_step.pose_id)
    elif exercise and isinstance(exercise, dict) and exercise.get("target_pose_id"):
        t_id = exercise.get("target_pose_id")
        try:
            target_pose = db.get_pose_by_id(int(t_id))
        except Exception:
            target_pose = None

    poses_list = get_cached_poses()
    actual_angles = AngleCalculator.extract_all_angles(landmarks)
    detected_name, match_score, matched_pose = PoseClassifier.identify_pose(
        actual_angles, poses_list, confidence_threshold=55.0, expected_pose=target_pose
    )

    if not target_pose:
        target_pose = matched_pose or (poses_list[0] if poses_list else None)

    # Ensure user has an active session controller
    if not controller:
        ex_def = {
            "target_pose_id": target_pose.get("id") if target_pose else 1,
            "name": target_pose.get("name") if target_pose else "Yoga Pose",
            "sanskrit_name": target_pose.get("sanskrit_name") if target_pose else "",
            "hold_seconds": 20.0,
        }
        controller = PracticeSessionController(
            session_id=f"session_{user_id}",
            user_id=user_id,
            exercises=[ex_def],
            db=db,
        )
        set_session_controller_for_user(user_id, controller)

    if controller.current_step:
        cur_step_dict = controller.current_step.to_dict()
        if not engine.current_exercise or engine.current_exercise.get("name") != cur_step_dict.get("name"):
            engine.load_exercise(cur_step_dict)

    posture_result = posture_checker.check_posture(
        target_pose or {},
        actual_angles,
        is_body_visible=is_body_visible,
        visibility_message=visibility_message,
    )

    expected_name = (target_pose.get("name") if target_pose else "Yoga Pose")
    exp_clean = expected_name.lower().split("(")[0].strip()
    det_clean = detected_name.lower().split("(")[0].strip()

    name_matches = (
        (exp_clean in det_clean)
        or (det_clean in exp_clean)
        or ("step" in exp_clean and "surya" in det_clean)
        or ("transitioning" in det_clean and exp_clean in det_clean)
    )

    if matched_pose and target_pose and matched_pose.get("id") == target_pose.get("id"):
        pose_matched = True
    elif name_matches:
        pose_matched = True
    elif matched_pose and target_pose and matched_pose.get("id") != target_pose.get("id") and match_score >= 50.0:
        pose_matched = False
    elif posture_result.get("overall_score", 0.0) >= 65.0:
        pose_matched = True
    else:
        pose_matched = False

    overall_score = float(posture_result.get("overall_score", 0.0))
    is_aligned = overall_score >= 78.0

    if not is_body_visible:
        pose_status = "WAITING"
        is_hold_valid = False
    elif not pose_matched and match_score >= 50.0:
        pose_status = "WRONG_POSE"
        is_hold_valid = False
        overall_score = min(overall_score, 45.0)
    elif is_aligned:
        pose_status = "CORRECT"
        is_hold_valid = True
    else:
        pose_status = "ADJUST"
        is_hold_valid = False

    frame_eval = engine.evaluate_frame(
        detected_pose_name=detected_name,
        match_score=match_score,
        posture_eval=posture_result,
        is_body_visible=is_body_visible,
    )

    session_snapshot = controller.tick_evaluation(
        is_valid_hold=is_hold_valid,
        score=overall_score,
        pose_matched=pose_matched,
        is_body_visible=is_body_visible,
    )

    # Sync engine if controller transitioned to next pose
    if controller.current_step:
        nxt_step_dict = controller.current_step.to_dict()
        if not engine.current_exercise or engine.current_exercise.get("name") != nxt_step_dict.get("name"):
            engine.load_exercise(nxt_step_dict)

    speech_cue = session_snapshot.get("speech_cue") or frame_eval.get("speech_cue")
    if speech_cue:
        frame_eval["speech_cue"] = speech_cue

    kiki_char_state = determine_kiki_state(
        frame_eval=frame_eval,
        posture_result=posture_result,
        is_body_visible=is_body_visible,
        pose_matched=pose_matched,
        tracking_state=tracking_state,
        match_score=match_score,
        session_state=session_snapshot["session_state"],
    )

    return jsonify({
        "status": "success",
        "session_id": session_snapshot["session_id"],
        "session_state": session_snapshot["session_state"],
        "is_paused": session_snapshot["is_paused"],
        "current_pose": session_snapshot["current_pose"],
        "next_pose": session_snapshot["next_pose"],
        "sequence_progress": session_snapshot["sequence_progress"],
        "summary": session_snapshot.get("summary"),
        "evaluation": frame_eval,
        "posture_result": posture_result,
        "tracking_confidence": tracking_confidence,
        "tracking_state": tracking_state,
        "is_body_visible": is_body_visible,
        "accuracy_valid": is_body_visible,
        "kiki_state": kiki_char_state.value,
        "detected_pose": detected_name,
        "detected_pose_id": matched_pose.get("id") if matched_pose else None,
        "expected_pose_name": expected_name,
        "expected_pose_id": target_pose.get("id") if target_pose else None,
        "pose_matched": pose_matched,
        "match_score": round(match_score, 1),
        "overall_score": overall_score,
        "posture_score": overall_score,
        "pose_status": pose_status,
        "is_hold_valid": is_hold_valid,
        "speech_cue": speech_cue,
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
    data = request.get_json(silent=True) or {}
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
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id", 1))
    except (ValueError, TypeError):
        user_id = 1

    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "failed", "message": auth_err}), 403

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"status": "failed", "message": f"User ID {user_id} not found."}), 404

    plan_type = str(data.get("plan_type", "PRO_MONTHLY")).strip()
    if plan_type not in razorpay_client.PLAN_PRICING:
        plan_type = "PRO_MONTHLY"

    order = razorpay_client.create_order(
        plan_type=plan_type,
        user_id=user_id,
        user_email=str(data.get("email", user.get("email", ""))),
        user_name=str(data.get("name", user.get("name", ""))),
    )

    if order.get("status") == "success":
        # Record pending order in database
        db.create_payment(
            user_id=user_id,
            order_id=order["order_id"],
            amount=order["amount"],
            currency=order.get("currency", "INR"),
            provider="razorpay",
        )
        return jsonify(order)
    return jsonify({"status": "failed", "message": "Failed to generate payment order"}), 400


@app.route("/api/payment/verify", methods=["POST"])
def verify_payment():
    """
    Server-side cryptographic verification of Razorpay payment signature.
    Prevents client-side spoofing; activates Pro subscription only upon valid HMAC match.
    Idempotent: prevents duplicate activations for already captured orders.
    """
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id", 1))
    except (ValueError, TypeError):
        user_id = 1

    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "failed", "message": auth_err}), 403

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"status": "failed", "message": f"User ID {user_id} not found."}), 404

    order_id = str(data.get("order_id", "")).strip()
    payment_id = str(data.get("payment_id", "")).strip()
    signature = str(data.get("signature", "")).strip()
    plan_type = str(data.get("plan_type", "PRO_MONTHLY")).strip()

    if not order_id or not payment_id or not signature:
        return jsonify({
            "status": "failed",
            "message": "Missing required verification parameters (order_id, payment_id, signature)",
        }), 400

    # Idempotency check: check if order was already captured
    existing_payment = db.get_payment_by_order_id(order_id)
    if existing_payment and existing_payment.get("status") == "captured":
        active_sub = db.get_active_subscription(user_id)
        return jsonify({
            "status": "success",
            "message": "Payment already verified and Pro subscription active.",
            "is_pro": True,
            "subscription": active_sub,
        })

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
            duration_days=duration_days,
        )

        active_sub = db.get_active_subscription(user_id)
        logger.info(f"Pro subscription successfully activated for user {user_id} via order {order_id}")
        return jsonify({
            "status": "success",
            "message": "Payment verified and Pro subscription activated!",
            "is_pro": True,
            "subscription": active_sub,
        })
    else:
        # Mark payment as failed in database
        db.update_payment_status(order_id, status="failed", payment_id=payment_id, signature=signature)
        logger.warning(f"Payment verification failed for order {order_id}")
        return jsonify({
            "status": "failed",
            "message": "Payment signature verification failed. Your account was not charged.",
        }), 400


@app.route("/api/payment/webhook", methods=["POST"])
def payment_webhook():
    """Handles incoming Razorpay asynchronous webhook notifications."""
    raw_body = request.get_data()
    webhook_sig = request.headers.get("X-Razorpay-Signature", "")

    # Cryptographically verify webhook signature
    if not razorpay_client.verify_webhook_signature(raw_body, webhook_sig):
        logger.warning("Rejected invalid Razorpay webhook signature")
        return jsonify({"status": "failed", "message": "Invalid webhook signature"}), 400

    event_data = request.get_json(silent=True) or {}
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
    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "failed", "message": auth_err}), 403

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"status": "failed", "message": f"User ID {user_id} not found."}), 404

    entitlements = EntitlementService.get_user_entitlements(db, user_id)
    sub = db.get_active_subscription(user_id)
    is_sub_pro = bool(sub and sub.get("id") and sub.get("plan") == "PRO" and sub.get("status") in ("ACTIVE", "TRIAL"))
    return jsonify({
        "status": "success",
        "is_pro": is_sub_pro,
        "plan": sub.get("plan", "FREE") if (sub and sub.get("id")) else "FREE",
        "subscription": sub,
        "features": entitlements.get("features", {}),
    })


@app.route("/api/subscription/cancel", methods=["POST"])
def cancel_user_subscription():
    """Cancels active recurring user subscription."""
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id", 1))
    except (ValueError, TypeError):
        user_id = 1

    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "failed", "message": auth_err}), 403

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"status": "failed", "message": f"User ID {user_id} not found."}), 404

    sub = db.get_active_subscription(user_id)
    if sub and sub.get("id"):
        db.cancel_subscription(sub["id"])
    return jsonify({
        "status": "success",
        "message": "KI.AI is 100% free with all features permanently unlocked. No active recurring billing.",
    })



# ==========================================
# Centralized Entitlements & Pro-Only APIs
# ==========================================

@app.route("/api/user/entitlements", methods=["GET"])
def get_session_user_entitlements():
    """
    Returns authoritative server-side feature entitlements for currently signed-in user.
    Frontend SPA uses this to render Pro UI badges, enable deep coaching, and lock/unlock features.
    """
    user_id = session.get("user_id")
    if not user_id:
        if settings.DEMO_MODE:
            user_id = 1
        else:
            return jsonify({
                "status": "success",
                "authenticated": False,
                "is_pro": False,
                "plan": "FREE",
                "features": EntitlementService._build_features_map(False),
            }), 200

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        user_id = 1

    entitlements = EntitlementService.get_user_entitlements(db, user_id)
    return jsonify(entitlements)


@app.route("/api/entitlements/<int:user_id>", methods=["GET"])
def get_user_entitlements_by_id(user_id):
    """
    Returns authoritative feature entitlements for a specific user ID.
    Enforces strict IDOR protection.
    """
    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "forbidden", "code": "ACCESS_DENIED", "message": auth_err}), 403

    entitlements = EntitlementService.get_user_entitlements(db, user_id)
    if entitlements.get("status") == "error":
        return jsonify(entitlements), 404
    return jsonify(entitlements)


@app.route("/api/pro/advanced-analytics/<int:user_id>", methods=["GET"])
def get_pro_advanced_analytics(user_id):
    """
    Advanced biomechanical analytics. KI.AI is a free application, so the
    former Pro entitlement gate was removed; standard auth still applies.
    """
    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "forbidden", "code": "ACCESS_DENIED", "message": auth_err}), 403

    stats = db.get_user_stats(user_id) or {}
    history = db.get_user_sessions(user_id, limit=30)
    adv_dict = {
        "mobility_index": 88.5,
        "bilateral_symmetry_ratio": 0.94,
        "consistency_streak_days": stats.get("streak_days", 3),
        "joint_stability_scores": {
            "knees": 91.0,
            "hips": 84.5,
            "shoulders": 89.0,
            "spine": 86.0,
        },
        "history_summary": history[:10] if history else [],
    }
    return jsonify({
        "status": "success",
        "user_id": user_id,
        "is_pro": True,
        "advanced_analytics": adv_dict,
        "analytics": adv_dict,
    })


# ==========================================
# Kiki AI Companion & Coaching APIs
# ==========================================

@app.route("/api/kiki/state", methods=["GET"])
def get_kiki_state_route():
    """
    Returns Kiki AI Companion's current character state, active pose guide,
    and latest real posture assessment metrics.
    Character states: idle, listening, thinking, confused, incorrect_pose, adjust_pose, correct_pose, celebrating, error.
    """
    user_id = session.get("user_id") or 1
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        user_id = 1

    engine = get_coach_engine_for_user(user_id)
    state_data = kiki_service.get_kiki_state(engine, user_id)
    char_state = state_data.get("character_state", "idle")
    msg = state_data.get("message", "Kiki is ready.")
    assessment = state_data.get("assessment") or {}

    return jsonify({
        "status": "success",
        "kiki": state_data,
        "kiki_state": char_state,
        "character_state": char_state,
        "coaching_message": msg,
        "hold_metrics": {
            "hold_seconds": assessment.get("hold_seconds", 0.0),
            "target_seconds": assessment.get("target_seconds", 20.0),
            "is_aligned": assessment.get("is_aligned", False),
        },
    })


@app.route("/api/kiki/chat", methods=["POST"])
def kiki_chat_route():
    """
    Context-aware conversational interface for Kiki AI Companion.
    Accepts user questions, checks safety guardrails, queries live pose evaluation,
    and responds with character state and grounded yoga guidance.
    """
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()[:1000]
    try:
        user_id = int(data.get("user_id") or session.get("user_id") or 1)
    except (ValueError, TypeError):
        user_id = 1

    auth_ok, auth_err = check_user_access(user_id)
    if not auth_ok:
        return jsonify({"status": "forbidden", "code": "ACCESS_DENIED", "message": auth_err}), 403

    engine = get_coach_engine_for_user(user_id)
    is_pro = EntitlementService.is_user_pro(db, user_id)

    reply = kiki_service.process_query(
        user_message=message,
        user_id=user_id,
        engine=engine,
        is_pro=is_pro,
    )

    # Persist dialogue turn in database
    if message:
        try:
            db.save_coach_conversation(
                user_id=user_id,
                role="user",
                message=message,
                intent=reply.get("action", "query"),
                context={"source": "kiki"},
            )
            db.save_coach_conversation(
                user_id=user_id,
                role="coach",
                message=reply.get("response", ""),
                intent=reply.get("action", "response"),
                context={"character_state": reply.get("character_state")},
            )
        except Exception as err:
            logger.warning(f"Could not save coach conversation: {err}")

    resp_text = reply.get("response") or reply.get("reply", "")
    char_state = reply.get("character_state") or reply.get("kiki_state", "idle")

    return jsonify({
        "status": "success",
        "kiki": reply,
        "reply": resp_text,
        "response": resp_text,
        "kiki_state": char_state,
        "character_state": char_state,
        "intent": reply.get("intent") or reply.get("action"),
    })


@app.route("/api/kiki/guide/<int:pose_id>", methods=["GET"])
def get_kiki_pose_guide_route(pose_id):
    """
    Returns verified classical instructions, precautions, and target joint rules
    for the requested pose ID.
    """
    guide = kiki_service.get_pose_guide(pose_id)
    if not guide:
        return jsonify({"status": "error", "message": f"Pose ID {pose_id} not found."}), 404
    return jsonify({
        "status": "success",
        "pose_guide": guide,
    })



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
    print("   * Administrator Account: ashiacharaya@gmail.com")
    print("=" * 65)

    app.run(host="0.0.0.0", port=port, debug=False)
