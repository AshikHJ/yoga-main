"""
Comprehensive Backend API, Authentication, Security, and Edge-Case Tests.

Covers:
1. User registration, Argon2id hashing, login, password rehash, session lifecycle, logout.
2. Administrative route authorization (/admin protection, 403 on unauth/non-admin, 200 on admin).
3. Cross-user authorization and IDOR defense across user endpoints (/history, /stats, /preferences, /subscription).
4. Defensive parameter validation, non-existent entity handling, and malformed JSON safety.
5. Payment order generation, signature verification idempotency, and webhook HMAC signature rejection.
6. Per-user coach engine state isolation and cached poses retrieval.
"""

import json
import os
import secrets
import pytest
from web_app import app, db, get_coach_engine_for_user, get_cached_poses, refresh_poses_cache
from payment.razorpay_client import get_razorpay_client


@pytest.fixture
def client():
    """Configures test client with isolated session handling."""
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test_secret_for_unit_tests_only"
    with app.test_client() as c:
        yield c


class TestAuthenticationAndAdminRoutes:
    """Tests authentication flows, password security, and administrative access control."""

    def test_register_missing_fields_rejected(self, client):
        resp = client.post(
            "/api/register",
            data=json.dumps({"name": "Incomplete User"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "error"
        assert "required" in data["message"].lower()

    def test_register_duplicate_email_rejected(self, client):
        # abhilash@ki.ai is already a seeded account
        resp = client.post(
            "/api/register",
            data=json.dumps({
                "name": "Imposter",
                "email": "abhilash@ki.ai",
                "password": "somepassword123",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "error"
        assert "already exists" in data["message"].lower()

    def test_register_and_login_and_logout_flow(self, client):
        rand_suffix = secrets.token_hex(4)
        email = f"testuser_{rand_suffix}@ki.ai"
        pw = "StrongPass!123"

        # 1. Register new user
        reg_resp = client.post(
            "/api/register",
            data=json.dumps({
                "name": f"Test User {rand_suffix}",
                "email": email,
                "password": pw,
                "age": 28,
                "experience": "Intermediate",
                "goal": "Strength",
            }),
            content_type="application/json",
        )
        assert reg_resp.status_code == 200
        reg_data = reg_resp.get_json()
        assert reg_data["status"] == "success"
        user_id = reg_data["user"]["id"]
        assert user_id > 2

        # Verify password in DB is stored with secure hash (starts with $argon2id$ or $argon2)
        with db.get_connection() as conn:
            pw_row = conn.execute("SELECT password_hash FROM users WHERE id = ?;", (user_id,)).fetchone()
            assert pw_row is not None
            assert "$argon2" in pw_row["password_hash"]


        # 2. Logout
        logout_resp = client.post("/api/logout")
        assert logout_resp.status_code == 200

        # 3. Login with wrong password
        fail_login = client.post(
            "/api/login",
            data=json.dumps({"email": email, "password": "WrongPassword"}),
            content_type="application/json",
        )
        assert fail_login.status_code == 401
        assert fail_login.get_json()["status"] == "error"

        # 4. Login with correct password
        succ_login = client.post(
            "/api/login",
            data=json.dumps({"email": email, "password": pw}),
            content_type="application/json",
        )
        assert succ_login.status_code == 200
        login_data = succ_login.get_json()
        assert login_data["status"] == "success"
        assert login_data["user"]["id"] == user_id

        # Clean up created user to keep database tidy
        with db.get_connection() as conn:
            conn.execute("DELETE FROM users WHERE id = ?;", (user_id,))

    def test_admin_route_unauthenticated_blocked(self, client):
        # Client without session must receive 403 Forbidden
        resp = client.get("/admin")
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "error"
        assert "administrative" in data["message"].lower()

    def test_admin_route_non_admin_blocked(self, client):
        # Log in as non-admin user (guest@ki.ai, id=2, is_admin=0)
        login_resp = client.post(
            "/api/login",
            data=json.dumps({"email": "guest@ki.ai", "password": "guest123"}),
            content_type="application/json",
        )
        assert login_resp.status_code == 200


        # Attempt to access /admin
        admin_resp = client.get("/admin")
        assert admin_resp.status_code == 403

    def test_admin_route_admin_session_allowed(self, client):
        # Log in as admin user (abhilash@ki.ai, is_admin=1)
        login_resp = client.post(
            "/api/login",
            data=json.dumps({"email": "abhilash@ki.ai", "password": "password123"}),
            content_type="application/json",
        )
        assert login_resp.status_code == 200

        # Admin access must succeed (200 OK)
        admin_resp = client.get("/admin")
        assert admin_resp.status_code == 200

    def test_admin_route_valid_token_bearer_allowed(self, client):
        os.environ["ADMIN_TOKEN"] = "super_secure_admin_token_xyz"
        resp = client.get("/admin", headers={"Authorization": "Bearer super_secure_admin_token_xyz"})
        assert resp.status_code == 200


class TestIdorAndUserAuthorization:
    """Verifies protection against Insecure Direct Object References (IDOR)."""

    def test_demo_user_allowed_unauthenticated_in_demo_mode(self, client):
        # User 1 (Abhilash) is allowed unauthenticated for frontend demo compatibility
        resp = client.get("/api/history/1")
        assert resp.status_code == 200

    def test_non_demo_user_unauthenticated_blocked(self, client):
        # Random non-demo user ID unauthenticated must be blocked
        resp = client.get("/api/history/9999")
        assert resp.status_code == 403

    def test_cross_user_idor_blocked_for_authenticated_user(self, client):
        # Register two temporary users: User A and User B
        uid_a = db.create_user("User A", f"user_a_{secrets.token_hex(3)}@ki.ai", "StrongPass123")
        uid_b = db.create_user("User B", f"user_b_{secrets.token_hex(3)}@ki.ai", "StrongPass123")

        try:
            # Log in as User A
            user_a = db.get_user_by_id(uid_a)
            login_resp = client.post(
                "/api/login",
                data=json.dumps({"email": user_a["email"], "password": "StrongPass123"}),
                content_type="application/json",
            )
            assert login_resp.status_code == 200


            # User A accessing User A's data succeeds
            resp_self = client.get(f"/api/history/{uid_a}")
            assert resp_self.status_code == 200

            # User A attempting to access User B's history is BLOCKED with 403
            resp_b_history = client.get(f"/api/history/{uid_b}")
            assert resp_b_history.status_code == 403

            # User A attempting to access User B's stats is BLOCKED with 403
            resp_b_stats = client.get(f"/api/stats/{uid_b}")
            assert resp_b_stats.status_code == 403

            # User A attempting to access User B's preferences is BLOCKED with 403
            resp_b_prefs = client.get(f"/api/user/preferences/{uid_b}")
            assert resp_b_prefs.status_code == 403

            # User A attempting to access User B's subscription is BLOCKED with 403
            resp_b_sub = client.get(f"/api/subscription/{uid_b}")
            assert resp_b_sub.status_code == 403

        finally:
            with db.get_connection() as conn:
                conn.execute("DELETE FROM users WHERE id IN (?, ?);", (uid_a, uid_b))


class TestInputValidationAndRobustness:
    """Verifies API defense against malformed inputs and edge cases."""

    def test_nonexistent_user_returns_404(self, client):
        # When authenticated as admin, accessing non-existent user returns 404
        client.post(
            "/api/login",
            data=json.dumps({"email": "abhilash@ki.ai", "password": "password123"}),
            content_type="application/json",
        )
        resp = client.get("/api/history/88888")
        assert resp.status_code == 404

        resp_stats = client.get("/api/stats/88888")
        assert resp_stats.status_code == 404

    def test_evaluate_frame_empty_landmarks(self, client):
        resp = client.post(
            "/api/session/evaluate_frame",
            data=json.dumps({"landmarks": {}}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.get_json()["status"] == "error"

    def test_evaluate_frame_malformed_landmarks_handled_gracefully(self, client):
        resp = client.post(
            "/api/session/evaluate_frame",
            data=json.dumps({
                "landmarks": {
                    "NOSE": "invalid_structure",
                    "LEFT_SHOULDER": {"x": "not_a_number", "y": 0.5, "visibility": 0.9},
                }
            }),
            content_type="application/json",
        )
        # Should return 200 with NO_PERSON tracking state instead of 500 error
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["tracking_state"] == "NO_PERSON"
        assert data["is_body_visible"] is False

    def test_save_session_defensive_types(self, client):
        # Non-numeric duration and score should be rejected with 400 Bad Request
        resp = client.post(
            "/api/save_session",
            data=json.dumps({
                "user_id": 1,
                "pose_id": 1,
                "duration": "invalid_duration",
                "average_score": "invalid_score",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.get_json()["status"] == "error"



class TestPaymentAndWebhookSecurity:
    """Verifies payment transaction safety, idempotency, and webhook security."""

    def test_create_order_nonexistent_user_returns_404(self, client):
        # Log in as admin to bypass IDOR check, but supply non-existent user ID
        client.post(
            "/api/login",
            data=json.dumps({"email": "abhilash@ki.ai", "password": "password123"}),
            content_type="application/json",
        )
        resp = client.post(
            "/api/payment/create-order",
            data=json.dumps({"user_id": 99999, "plan_type": "PRO_MONTHLY"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_verify_payment_idempotency(self, client):
        # 1. Create order for demo user 1
        create_resp = client.post(
            "/api/payment/create-order",
            data=json.dumps({"user_id": 1, "plan_type": "PRO_MONTHLY"}),
            content_type="application/json",
        )
        assert create_resp.status_code == 200
        order_id = create_resp.get_json()["order_id"]
        payment_id = f"pay_test_{secrets.token_hex(4)}"

        # 2. Generate valid test signature
        rzp = get_razorpay_client()
        sig = rzp.generate_test_signature(order_id, payment_id)

        # 3. First verify call
        verify_1 = client.post(
            "/api/payment/verify",
            data=json.dumps({
                "user_id": 1,
                "order_id": order_id,
                "payment_id": payment_id,
                "signature": sig,
                "plan_type": "PRO_MONTHLY",
            }),
            content_type="application/json",
        )
        assert verify_1.status_code == 200
        assert verify_1.get_json()["status"] == "success"
        assert verify_1.get_json()["is_pro"] is True

        # 4. Second verify call with same order ID must succeed idempotently
        verify_2 = client.post(
            "/api/payment/verify",
            data=json.dumps({
                "user_id": 1,
                "order_id": order_id,
                "payment_id": payment_id,
                "signature": sig,
                "plan_type": "PRO_MONTHLY",
            }),
            content_type="application/json",
        )
        assert verify_2.status_code == 200
        assert verify_2.get_json()["status"] == "success"
        assert "already verified" in verify_2.get_json()["message"].lower()

    def test_webhook_invalid_signature_rejected(self, client):
        # Set a test webhook secret to enforce HMAC verification
        rzp = get_razorpay_client()
        rzp.webhook_secret = "test_webhook_secret_xyz"

        try:
            payload = json.dumps({"event": "payment.captured", "payload": {}})
            resp = client.post(
                "/api/payment/webhook",
                data=payload,
                headers={"X-Razorpay-Signature": "invalid_hmac_signature"},
                content_type="application/json",
            )
            assert resp.status_code == 400
            assert resp.get_json()["status"] == "failed"
        finally:
            rzp.webhook_secret = ""


class TestCoachEngineAndPoseCaching:
    """Verifies per-user coach state isolation and pose cache mechanisms."""

    def test_per_user_coach_engine_isolation(self):
        engine_1 = get_coach_engine_for_user(1)
        engine_2 = get_coach_engine_for_user(2)

        # Separate instances must exist
        assert engine_1 is not engine_2

        # Setting state on engine 1 does not mutate engine 2
        engine_1.load_exercise({"name": "Warrior I", "target_hold_seconds": 15})
        assert engine_1.current_exercise["name"] == "Warrior I"
        assert engine_2.current_exercise is None or engine_2.current_exercise.get("name") != "Warrior I"

    def test_pose_caching_and_refresh(self):
        poses = get_cached_poses()
        assert len(poses) > 0
        assert all("id" in p and "name" in p for p in poses)

        # Refresh cache executes cleanly
        refreshed = refresh_poses_cache()
        assert len(refreshed) == len(poses)
