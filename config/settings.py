"""
Centralized Configuration and Settings for KI.AI.
AI-Powered Yoga & Posture Intelligence.
Contains system paths, camera parameters, detection thresholds, scoring criteria,
centralized color themes, and user preferences.
"""

from pathlib import Path

# ==========================================
# Paths Configuration
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = BASE_DIR / "database"
MODELS_DIR = BASE_DIR / "models"
ASSETS_DIR = BASE_DIR / "assets"
DOCS_DIR = BASE_DIR / "docs"

REF_POSES_DIR = DATA_DIR / "reference_poses"
POSES_JSON_PATH = DATA_DIR / "poses.json"
SURYA_JSON_PATH = DATA_DIR / "surya_namaskar.json"
DB_PATH = DATABASE_DIR / "yoga.db"
SCHEMA_PATH = DATABASE_DIR / "schema.sql"

# Sub-asset directories
IMAGES_DIR = ASSETS_DIR / "images"
YOGA_IMAGES_DIR = IMAGES_DIR / "yoga"
SKELETONS_DIR = ASSETS_DIR / "reference_skeletons"
ICONS_DIR = ASSETS_DIR / "icons"

# Ensure essential runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
REF_POSES_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
YOGA_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
SKELETONS_DIR.mkdir(parents=True, exist_ok=True)
ICONS_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# Application Branding & Information
# ==========================================
APP_NAME = "KI.AI"
APP_SUBTITLE = "AI-Powered Yoga & Posture Intelligence"
APP_TAGLINE = "Practice smarter. Move better."
APP_VERSION = "2.0.0"
APP_AUTHOR = "KI.AI Engineering Team"
WINDOW_TITLE = "KI.AI — AI-Powered Yoga & Posture Intelligence"

SAFETY_DISCLAIMER = (
    "Disclaimer: This application provides general fitness guidance and is not a medical "
    "diagnostic system. Perform yoga poses within a comfortable range and stop immediately "
    "if you experience pain, dizziness, or physical discomfort."
)

PRIVACY_DISCLAIMER = (
    "Privacy: All camera processing and posture analysis is executed 100% locally on your "
    "machine. KI.AI never uploads or records your webcam footage."
)

# ==========================================
# Camera & Video Stream Settings
# ==========================================
DEFAULT_CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30
FRAME_UPDATE_INTERVAL_MS = 33  # ~30 FPS
MIRROR_WEBCAM = True

# ==========================================
# Pose Detection & MediaPipe Settings
# ==========================================
MIN_DETECTION_CONFIDENCE = 0.60
MIN_TRACKING_CONFIDENCE = 0.60
MIN_PRESENCE_CONFIDENCE = 0.60
POSE_LANDMARKER_MODEL_PATH = MODELS_DIR / "pose_landmarker.task"

# Minimum landmark visibility for analysis
MIN_LANDMARK_VISIBILITY = 0.40
LANDMARK_VISIBILITY_THRESHOLD = 0.40

# Key Landmarks monitored in Yoga Posture rules
CRITICAL_LANDMARKS = [
    "LEFT_SHOULDER", "RIGHT_SHOULDER",
    "LEFT_ELBOW", "RIGHT_ELBOW",
    "LEFT_WRIST", "RIGHT_WRIST",
    "LEFT_HIP", "RIGHT_HIP",
    "LEFT_KNEE", "RIGHT_KNEE",
    "LEFT_ANKLE", "RIGHT_ANKLE"
]

# Custom Pose Stability Parameters
CUSTOM_POSE_CAPTURE_FRAME_COUNT = 30
CAPTURE_STABILITY_STD_THRESHOLD = 8.0  # Max degree variance across frames for stability

# ==========================================
# Scoring & Posture Thresholds
# ==========================================
SCORE_EXCELLENT_THRESHOLD = 90.0
SCORE_GOOD_THRESHOLD = 80.0
SCORE_NEEDS_IMPROVEMENT_THRESHOLD = 70.0

DEFAULT_TOLERANCE_DEGREES = 15.0
DEFAULT_HOLD_DURATION_SECONDS = 20
HOLD_TIMER_ACTIVATION_SCORE = 80.0  # Score required for hold timer countdown

# Score Level Categories with consistent Status Colors
SCORE_LEVELS = {
    "EXCELLENT": {
        "label": "EXCELLENT",
        "min_score": 90.0,
        "color": "#10B981",  # Emerald Green
        "bg_color": "rgba(16, 185, 129, 0.18)",
        "border_color": "#10B981",
        "dot": "🟢",
        "icon": "✓"
    },
    "GOOD": {
        "label": "GOOD",
        "min_score": 80.0,
        "color": "#10B981",  # Emerald Green
        "bg_color": "rgba(16, 185, 129, 0.18)",
        "border_color": "#10B981",
        "dot": "🟢",
        "icon": "✓"
    },
    "NEEDS_IMPROVEMENT": {
        "label": "NEEDS IMPROVEMENT",
        "min_score": 70.0,
        "color": "#F59E0B",  # Amber / Yellow
        "bg_color": "rgba(245, 158, 11, 0.18)",
        "border_color": "#F59E0B",
        "dot": "🟡",
        "icon": "!"
    },
    "INCORRECT": {
        "label": "NEEDS CORRECTION",
        "min_score": 0.0,
        "color": "#EF4444",  # Red / Coral
        "bg_color": "rgba(239, 68, 68, 0.18)",
        "border_color": "#EF4444",
        "dot": "🔴",
        "icon": "✗"
    }
}

# ==========================================
# Universal Status Dot System
# ==========================================
STATUS_DOTS = {
    "CORRECT": {
        "dot": "🟢",
        "label": "Correct",
        "color": "#10B981",
        "bg_color": "rgba(16, 185, 129, 0.18)",
        "border": "#10B981",
        "desc": "Body part correctly positioned within tolerance."
    },
    "WARNING": {
        "dot": "🟡",
        "label": "Adjust Slightly",
        "color": "#F59E0B",
        "bg_color": "rgba(245, 158, 11, 0.18)",
        "border": "#F59E0B",
        "desc": "Joint is close to tolerance limit or transition."
    },
    "INCORRECT": {
        "dot": "🔴",
        "label": "Needs Correction",
        "color": "#EF4444",
        "bg_color": "rgba(239, 68, 68, 0.18)",
        "border": "#EF4444",
        "desc": "Body part outside allowed tolerance range."
    },
    "NOT_DETECTED": {
        "dot": "⚪",
        "label": "Not Detected",
        "color": "#94A3B8",
        "bg_color": "rgba(148, 163, 184, 0.15)",
        "border": "#64748B",
        "desc": "Required landmark is occluded or not detected."
    }
}

# ==========================================
# Feedback & Voice Settings
# ==========================================
VOICE_FEEDBACK_ENABLED = True
VOICE_COOLDOWN_SECONDS = 4.0  # Delay between repeated voice announcements
VOICE_SPEECH_RATE = 155  # Words per minute for pyttsx3

# ==========================================
# User Goals & Difficulty Enums
# ==========================================
GOALS = [
    "Flexibility",
    "Strength",
    "Balance",
    "Relaxation",
    "General Fitness"
]

DIFFICULTY_LEVELS = [
    "Beginner",
    "Intermediate",
    "Advanced"
]

CATEGORIES = [
    "All",
    "Standing",
    "Sitting",
    "Balance",
    "Strength",
    "Flexibility",
    "Relaxation",
    "Surya Namaskar",
    "Custom"
]

# ==========================================
# UI Theme Colors (KI.AI Emerald Dark Theme)
# ==========================================
THEME = {
    "background": "#0B1120",       # Deep Obsidian
    "background_alt": "#0F172A",   # Slate Base
    "surface": "#0F172A",          # Surface Slate
    "surface_card": "#1E293B",     # Elevated Slate Card
    "surface_light": "#334155",    # Slate 700
    "primary": "#10B981",          # Emerald Green Primary
    "primary_hover": "#059669",    # Dark Emerald Hover
    "primary_deep": "#064E3B",     # Deep Forest Green
    "primary_light": "rgba(16, 185, 129, 0.15)",
    "primary_glow": "rgba(16, 185, 129, 0.25)",
    "secondary": "#06B6D4",        # Cyan Secondary
    "accent": "#34D399",           # Soft Mint Accent
    "text_primary": "#F8FAFC",     # Crisp White
    "text_secondary": "#94A3B8",   # Light Slate
    "text_muted": "#64748B",       # Muted Gray
    "border": "#1E293B",           # Subtle Border
    "border_card": "#334155",      # Card Border
    "border_highlight": "#10B981", # Active Emerald Border
    "success": "#10B981",          # Emerald Green 🟢
    "warning": "#F59E0B",          # Amber Yellow 🟡
    "danger": "#EF4444",           # Coral Red 🔴
    "gray": "#94A3B8",             # Neutral Slate ⚪
    "info": "#38BDF8",             # Sky Blue
    "font_family": "Segoe UI, -apple-system, Roboto, Ubuntu, sans-serif",
}
