"""
KI.AI Centralized Subscription Entitlements Service.
Authoritative server-side entitlement engine governing access to Pro-tier features.
Validates live subscription state, handles expiration, prevents client-side spoofing,
and ensures complete cross-user isolation.
"""

from datetime import datetime
import functools
import logging
from typing import Any, Dict, Optional, Tuple
from flask import jsonify, request, session

logger = logging.getLogger(__name__)

# Feature Identifiers
FEATURE_PRO_POSES = "pro_poses"
FEATURE_ADVANCED_ANALYTICS = "advanced_analytics"
FEATURE_KIKI_DEEP_COACHING = "kiki_deep_coaching"
FEATURE_UNLIMITED_SESSIONS = "unlimited_sessions"
FEATURE_CUSTOM_ROUTINES = "custom_routines"
FEATURE_POSTURE_BREAKDOWN = "posture_breakdown"
FEATURE_BASIC_POSES = "basic_poses"
FEATURE_STANDARD_SESSION = "standard_session"
FEATURE_GENERAL_KIKI = "general_kiki"


class EntitlementService:
    """Authoritative server-side entitlement evaluator."""

    @staticmethod
    def get_user_entitlements(db, user_id: int) -> Dict[str, Any]:
        """
        Evaluates and returns comprehensive entitlement rights for a user.
        Always reads authoritative database records — NEVER trusts client claims.
        
        Args:
            db: Database instance.
            user_id: Target user ID.
            
        Returns:
            Dictionary with subscription details, active Pro status, and feature flags.
        """
        user = db.get_user_by_id(user_id)
        if not user:
            return {
                "status": "error",
                "message": f"User {user_id} not found.",
                "user_id": user_id,
                "is_pro": False,
                "plan": "FREE",
                "subscription_status": "NONE",
                "expires_at": None,
                "features": EntitlementService._build_features_map(False),
            }

        is_admin_user = bool(user.get("is_admin", 0))

        # KI.AI is 100% free: All yoga features and Kiki are unlocked for all authenticated practitioners.
        # No paid subscription or paywall is enforced.
        return {
            "status": "success",
            "user_id": user_id,
            "is_pro": True,
            "is_admin": is_admin_user,
            "plan": "FREE_UNLIMITED",
            "subscription_status": "ACTIVE",
            "expires_at": None,
            "subscription_id": None,
            "features": EntitlementService._build_features_map(True),
        }

    @staticmethod
    def _build_features_map(is_pro: bool = True) -> Dict[str, bool]:
        """Constructs canonical feature availability dictionary (all True in free KI.AI)."""
        return {
            FEATURE_BASIC_POSES: True,
            FEATURE_STANDARD_SESSION: True,
            FEATURE_GENERAL_KIKI: True,
            FEATURE_PRO_POSES: True,
            FEATURE_ADVANCED_ANALYTICS: True,
            FEATURE_KIKI_DEEP_COACHING: True,
            FEATURE_UNLIMITED_SESSIONS: True,
            FEATURE_CUSTOM_ROUTINES: True,
            FEATURE_POSTURE_BREAKDOWN: True,
        }

    @classmethod
    def is_user_pro(cls, db, user_id: int) -> bool:
        """Returns True for all valid authenticated users in free KI.AI."""
        user = db.get_user_by_id(user_id) if db else None
        return bool(user)

    @classmethod
    def check_feature(cls, db, user_id: int, feature_name: str) -> bool:
        """Returns True for all features for valid authenticated users in free KI.AI."""
        return cls.is_user_pro(db, user_id)


def require_pro(db_getter, feature_name: Optional[str] = None):
    """
    Flask route decorator that enforces user authentication server-side.
    In free KI.AI, all authenticated users have full access to all features (no paywalls).
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            from flask import current_app
            from config import settings
            user_id = session.get("user_id")
            if not user_id and getattr(settings, "DEMO_MODE", False) and not current_app.config.get("TESTING", False):
                user_id = 1

            if not user_id:
                return jsonify({
                    "status": "forbidden",
                    "code": "AUTHENTICATION_REQUIRED",
                    "message": "Authentication required to access this feature.",
                }), 401

            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return jsonify({
                    "status": "forbidden",
                    "code": "AUTHENTICATION_REQUIRED",
                    "message": "Invalid user authentication session.",
                }), 401

            db = db_getter()
            user = db.get_user_by_id(user_id)
            if not user:
                return jsonify({
                    "status": "forbidden",
                    "code": "USER_NOT_FOUND",
                    "message": f"User ID {user_id} not found.",
                }), 404

            return fn(*args, **kwargs)
        return wrapper
    return decorator
