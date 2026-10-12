"""
Production verification test suite for:
1. Centralized Pro Entitlement Service and server-side feature gates.
2. Kiki AI Companion 9 character states, biomechanical reasoning, and safety guardrails.
3. Accurate joint angle calculations, landmark confidence filtering, and posture states.
"""

import json
import math
import pytest
from config import settings
from web_app import app, db, get_coach_engine_for_user
from coach.state_machine import SessionState
from coach.kiki import (
    KikiCharacterState,
    determine_kiki_state,
    KikiService,
)
from payment.entitlements import (
    EntitlementService,
    FEATURE_PRO_POSES,
    FEATURE_ADVANCED_ANALYTICS,
    FEATURE_KIKI_DEEP_COACHING,
    FEATURE_UNLIMITED_SESSIONS,
    FEATURE_CUSTOM_ROUTINES,
    FEATURE_POSTURE_BREAKDOWN,
)
from analysis.angle_calculator import AngleCalculator
from analysis.posture_checker import PostureChecker


@pytest.fixture
def client():
    """Configures isolated test client with test secret."""
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test_kiki_entitlements_secret"
    with app.test_client() as c:
        yield c


# ============================================================================
# 1. Centralized Server-Side Entitlements & Pro Feature Gates
# ============================================================================

class TestCentralizedEntitlements:
    """Verifies that Pro entitlements are authoritatively determined and cannot be spoofed."""

    @pytest.fixture
    def test_users(self):
        """Creates a Free user and a Pro user for testing."""
        free_uid = db.create_user("Free Yogini", 24, "Beginner", "Flexibility")
        pro_uid = db.create_user("Pro Yogi", 32, "Advanced", "Strength")
        
        # Give pro_uid an active Pro subscription
        db.create_subscription(
            user_id=pro_uid,
            plan="PRO",
            status="ACTIVE",
            provider="razorpay",
            provider_customer_id=f"cust_{pro_uid}",
            provider_subscription_id="pay_pro_test_1",
            duration_days=30,
        )

        yield {"free_id": free_uid, "pro_id": pro_uid}

        # Cleanup
        with db.get_connection() as conn:
            conn.execute("DELETE FROM subscriptions WHERE user_id IN (?, ?);", (free_uid, pro_uid))
            conn.execute("DELETE FROM users WHERE id IN (?, ?);", (free_uid, pro_uid))

    def test_entitlements_payload_structure_all_unlocked(self, test_users):
        free_ent = EntitlementService.get_user_entitlements(db, test_users["free_id"])
        assert free_ent["status"] == "success"
        assert free_ent["user_id"] == test_users["free_id"]
        assert free_ent["is_pro"] is True
        assert free_ent["features"][FEATURE_ADVANCED_ANALYTICS] is True
        assert free_ent["features"][FEATURE_PRO_POSES] is True
        assert free_ent["features"][FEATURE_KIKI_DEEP_COACHING] is True
        assert free_ent["features"][FEATURE_UNLIMITED_SESSIONS] is True

        pro_ent = EntitlementService.get_user_entitlements(db, test_users["pro_id"])
        assert pro_ent["status"] == "success"
        assert pro_ent["user_id"] == test_users["pro_id"]
        assert pro_ent["is_pro"] is True
        assert pro_ent["features"][FEATURE_ADVANCED_ANALYTICS] is True

    def test_all_authenticated_practitioners_access_advanced_analytics(self, client, test_users):
        free_id = test_users["free_id"]
        with client.session_transaction() as sess:
            sess["user_id"] = free_id

        # In free KI.AI, all authenticated users have access to advanced analytics without paywall
        resp = client.get(f"/api/pro/advanced-analytics/{free_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert "analytics" in data
        assert data["user_id"] == free_id

    def test_pro_endpoint_grants_access_to_pro_subscriber(self, client, test_users):
        pro_id = test_users["pro_id"]
        with client.session_transaction() as sess:
            sess["user_id"] = pro_id

        resp = client.get(f"/api/pro/advanced-analytics/{pro_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert "analytics" in data
        assert data["user_id"] == pro_id

    def test_unauthenticated_pro_endpoint_returns_401(self, client, monkeypatch):
        # Ensure DEMO_MODE does not auto-populate session
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        resp = client.get("/api/pro/advanced-analytics/9999")
        assert resp.status_code in {401, 403}

    def test_entitlements_idor_protection(self, client, test_users):
        free_id = test_users["free_id"]
        pro_id = test_users["pro_id"]

        with client.session_transaction() as sess:
            sess["user_id"] = free_id

        # Free user attempting to read Pro user's entitlements directly by ID is blocked
        resp = client.get(f"/api/entitlements/{pro_id}")
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "forbidden"
        assert data["code"] == "ACCESS_DENIED"


# ============================================================================
# 2. Kiki AI Companion Character States & Conversational Coaching
# ============================================================================

class TestKikiAICompanion:
    """Verifies all 9 character states and truthful context-aware coaching."""

    def test_kiki_all_9_character_states_determinism(self):
        # 1. IDLE: Not tracking or body not visible
        assert determine_kiki_state(is_body_visible=False) == KikiCharacterState.IDLE

        # 2. CONFUSED: Body partially occluded or insufficient key landmarks
        assert determine_kiki_state(
            tracking_state="PARTIAL_BODY",
            is_body_visible=True,
        ) == KikiCharacterState.CONFUSED

        assert determine_kiki_state(
            posture_eval={"status_state": "insufficient_data"},
            is_body_visible=True,
        ) == KikiCharacterState.CONFUSED

        # 3. INCORRECT_POSE: Wrong pose detected or very low accuracy
        assert determine_kiki_state(
            tracking_state="WRONG_POSE",
            match_score=40.0,
            posture_eval={"status_state": "incorrect"},
            is_body_visible=True,
        ) == KikiCharacterState.INCORRECT_POSE

        assert determine_kiki_state(
            match_score=45.0,
            posture_eval={"status_state": "incorrect"},
            is_body_visible=True,
        ) == KikiCharacterState.INCORRECT_POSE

        # 4. ADJUST_POSE: Borderline accuracy needing minor corrections
        assert determine_kiki_state(
            match_score=72.0,
            posture_eval={"status_state": "adjust"},
            is_body_visible=True,
        ) == KikiCharacterState.ADJUST_POSE

        # 5. CORRECT_POSE: Proper alignment and target hold in progress
        assert determine_kiki_state(
            match_score=88.0,
            posture_eval={"status_state": "correct"},
            session_state=SessionState.HOLDING,
            is_body_visible=True,
        ) == KikiCharacterState.CORRECT_POSE

        # 6. CELEBRATING: Pose hold completed or session finished
        assert determine_kiki_state(
            session_state=SessionState.COMPLETING_POSE,
            is_body_visible=True,
        ) == KikiCharacterState.CELEBRATING

        # 7. LISTENING: Explicit voice input trigger
        assert determine_kiki_state(
            is_listening=True,
            is_body_visible=True,
        ) == KikiCharacterState.LISTENING

        # 8. THINKING: Query processing trigger
        assert determine_kiki_state(
            is_thinking=True,
            is_body_visible=True,
        ) == KikiCharacterState.THINKING

        # 9. ERROR: Vision pipeline failure or camera occlusion exception
        assert determine_kiki_state(
            has_error=True,
            is_body_visible=True,
        ) == KikiCharacterState.ERROR

    def test_kiki_service_safety_guardrail_on_pain_query(self):
        engine = get_coach_engine_for_user(999)
        kiki = KikiService(db, engine)

        res = kiki.process_query(user_id=999, message="I feel sharp pain in my lower back and knee!")
        assert res["intent"] == "pain_safety_alert"
        assert res["kiki_state"] == KikiCharacterState.CONFUSED.value
        reply = res["reply"].lower()
        assert "stop" in reply or "ease" in reply
        assert "pain" in reply
        assert "medical" in reply or "doctor" in reply or "healthcare" in reply

    def test_kiki_service_score_explanation_from_real_joint_deviations(self):
        engine = get_coach_engine_for_user(999)
        engine.current_exercise = {"name": "Warrior II"}
        engine.latest_assessment = {
            "overall_score": 68.0,
            "detected_pose_name": "Warrior II",
            "eval_details": {
                "incorrect_joints": [
                    {
                        "joint_name": "left_knee",
                        "actual_angle": 135.0,
                        "target_angle": 90.0,
                        "deviation": 45.0,
                        "feedback_message": "Bend your front knee deeper toward 90 degrees",
                    }
                ]
            }
        }
        kiki = KikiService(db, engine)

        res = kiki.process_query(user_id=999, message="Why did I only score 68?")
        assert res["intent"] == "score_explanation"
        reply = res["reply"]
        assert "68" in reply or "Warrior II" in reply
        assert "left knee" in reply.lower() or "knee" in reply.lower()
        assert "45" in reply or "Bend" in reply

    def test_kiki_get_pose_guide_verified_rules(self):
        engine = get_coach_engine_for_user(1)
        kiki = KikiService(db, engine)

        guide = kiki.get_pose_guide(1)
        assert guide["status"] == "success"
        pose = guide["pose"]
        assert "id" in pose and pose["id"] == 1
        assert "name" in pose
        assert "rules" in guide
        assert len(guide["rules"]) > 0
        rule0 = guide["rules"][0]
        assert "joint_name" in rule0
        assert "target_angle" in rule0
        assert "tolerance" in rule0

    def test_kiki_chat_api_endpoint(self, client):
        resp = client.post(
            "/api/kiki/chat",
            data=json.dumps({
                "user_id": 1,
                "message": "Can you give me a gentle alignment tip for Tadasana?",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert "reply" in data
        assert len(data["reply"]) > 10
        assert data["kiki_state"] in [s.value for s in KikiCharacterState]

    def test_kiki_state_endpoint(self, client):
        resp = client.get("/api/kiki/state?user_id=1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert "kiki_state" in data
        assert "coaching_message" in data
        assert "hold_metrics" in data

    def test_kiki_guide_endpoint_nonexistent_returns_404(self, client):
        resp = client.get("/api/kiki/guide/99999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["status"] == "error"


# ============================================================================
# 3. Biomechanical Landmark Confidence & Posture State Verification
# ============================================================================

class TestBiomechanicalAngleIntegrity:
    """Verifies math safety, landmark confidence filtering, and posture state truthfulness."""

    def test_landmark_visibility_threshold_enforcement(self):
        # A landmark with visibility < 0.35 must be omitted by extract_all_angles
        landmarks = {
            "LEFT_SHOULDER": {"x": 0.5, "y": 0.2, "z": 0.0, "visibility": 0.9},
            "LEFT_ELBOW": {"x": 0.5, "y": 0.4, "z": 0.0, "visibility": 0.2},  # < 0.35
            "LEFT_WRIST": {"x": 0.5, "y": 0.6, "z": 0.0, "visibility": 0.9},
        }
        angles = AngleCalculator.extract_all_angles(landmarks)
        assert "left_elbow" not in angles

        # When visibility >= 0.35, the angle is computed
        landmarks["LEFT_ELBOW"]["visibility"] = 0.85
        angles = AngleCalculator.extract_all_angles(landmarks)
        assert "left_elbow" in angles

    def test_non_finite_coordinates_filtered_out(self):
        landmarks = {
            "LEFT_SHOULDER": {"x": float("nan"), "y": 0.2, "z": 0.0, "visibility": 0.9},
            "LEFT_ELBOW": {"x": 0.5, "y": 0.4, "z": 0.0, "visibility": 0.9},
            "LEFT_WRIST": {"x": 0.5, "y": 0.6, "z": 0.0, "visibility": 0.9},
        }
        angles = AngleCalculator.extract_all_angles(landmarks)
        assert "left_elbow" not in angles

        landmarks["LEFT_SHOULDER"]["x"] = float("inf")
        angles = AngleCalculator.extract_all_angles(landmarks)
        assert "left_elbow" not in angles

    def test_zero_length_vector_safe_angle_calculation(self):
        # Point A and B are identical -> zero length vector -> must return 0.0 without crash
        pt_a = [0.5, 0.5]
        pt_b = [0.5, 0.5]
        pt_c = [0.8, 0.8]

        angle = AngleCalculator.calculate_angle(pt_a, pt_b, pt_c)
        assert angle == 0.0

    def test_truthful_right_angle_calculation(self):
        # Triangle with 90 degree angle at vertex B
        pt_a = [0.0, 1.0]
        pt_b = [0.0, 0.0]
        pt_c = [1.0, 0.0]

        angle = AngleCalculator.calculate_angle(pt_a, pt_b, pt_c)
        assert math.isclose(angle, 90.0, abs_tol=0.1)

    def test_posture_checker_all_four_status_states(self):
        checker = PostureChecker()
        tadasana_pose = db.get_pose_by_name("Tadasana")
        assert tadasana_pose is not None

        # 1. "insufficient_data": Empty landmarks
        eval_empty = checker.check_posture(tadasana_pose, {})
        assert eval_empty["status_state"] == "insufficient_data"
        assert eval_empty["overall_score"] == 0.0

        # 2. "correct": Perfectly aligned Tadasana
        aligned_angles = {
            "left_knee": 180.0,
            "right_knee": 180.0,
            "left_hip": 180.0,
            "right_hip": 180.0,
            "left_elbow": 180.0,
            "right_elbow": 180.0,
            "torso_vertical": 90.0,
        }
        eval_correct = checker.check_posture(tadasana_pose, aligned_angles)
        assert eval_correct["status_state"] == "correct"
        assert eval_correct["overall_score"] >= 85.0

        # 3. "adjust": Minor knee bend
        adjust_angles = dict(aligned_angles)
        adjust_angles["left_knee"] = 155.0  # slight bend producing warning
        eval_adjust = checker.check_posture(tadasana_pose, adjust_angles)
        assert eval_adjust["status_state"] == "adjust"

        # 4. "incorrect": Major misalignment across multiple joints
        incorrect_angles = {
            "left_knee": 90.0,
            "right_knee": 90.0,
            "left_hip": 90.0,
            "right_hip": 90.0,
            "left_elbow": 90.0,
            "right_elbow": 90.0,
            "torso_vertical": 40.0,
        }
        eval_inc = checker.check_posture(tadasana_pose, incorrect_angles)
        assert eval_inc["status_state"] == "incorrect"
        assert eval_inc["overall_score"] < 60.0
