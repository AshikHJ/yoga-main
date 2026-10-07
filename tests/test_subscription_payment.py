"""
Unit and integration tests for KI.AI Subscription and Razorpay Payment System.

Tests cover:
- RazorpayClient singleton, plans catalog, test mode order creation
- Cryptographic HMAC-SHA256 payment signature verification (valid vs tampered)
- Database subscription lifecycle: create, get_active, update_status, cancel, is_user_pro
- Database payment transactions: create, update_status, order lookup, history
- Flask API endpoints:
  - GET /api/payment/config (verifying zero secret leakage)
  - POST /api/payment/create-order (success & validation)
  - POST /api/payment/verify (cryptographic verification, Pro activation, rejection on invalid signature)
  - GET /api/subscription/<user_id> (status, history, entitlements)
  - POST /api/subscription/cancel (downgrade & cancellation)
  - Security headers (CSP, X-Frame-Options, X-Content-Type-Options)
  - GET /manifest.json (PWA Web Manifest verification)
"""

import hmac
import hashlib
import json
import pytest

from database.database import Database
from payment.razorpay_client import RazorpayClient, get_razorpay_client
from web_app import app, db


@pytest.fixture
def temp_db(tmp_path):
    """Isolated temporary SQLite database for unit tests."""
    db_file = tmp_path / "yoga_sub_test.db"
    return Database(db_path=db_file)


@pytest.fixture
def client():
    """Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ============================================================================
# 1. RazorpayClient Unit Tests
# ============================================================================

class TestRazorpayClient:
    def test_singleton_instance(self):
        client1 = get_razorpay_client()
        client2 = get_razorpay_client()
        assert client1 is client2

    def test_plans_pricing_catalog(self):
        client = get_razorpay_client()
        pricing = client.PLAN_PRICING
        assert "PRO_MONTHLY" in pricing
        assert "PRO_ANNUAL" in pricing

        monthly = pricing["PRO_MONTHLY"]
        assert monthly["amount_paise"] == 79900  # ₹799 in paise
        assert monthly["duration_days"] == 30
        assert monthly["currency"] == "INR"

        annual = pricing["PRO_ANNUAL"]
        assert annual["amount_paise"] == 799900  # ₹7,999 in paise
        assert annual["duration_days"] == 365
        assert annual["currency"] == "INR"

    def test_public_config_does_not_leak_secret(self):
        client = get_razorpay_client()
        config = client.get_public_config()
        assert "key_id" in config
        assert "plans" in config
        assert "currency" in config
        assert "PRO_MONTHLY" in config["plans"]
        assert "PRO_ANNUAL" in config["plans"]
        # CRITICAL SECURITY CHECK: secret key must NEVER be in public config
        assert "key_secret" not in config
        assert "secret" not in config
        assert "webhook_secret" not in config

    def test_create_order_test_mode(self):
        client = get_razorpay_client()
        order = client.create_order(plan_type="PRO_MONTHLY", user_id=1)
        assert order["status"] == "success"
        assert order["amount"] == 79900
        assert order["currency"] == "INR"
        assert order["order_id"].startswith("order_test_")
        assert order["plan_type"] == "PRO_MONTHLY"
        assert order["is_test_mode"] is True

    def test_signature_verification_valid_hmac(self):
        client = get_razorpay_client()
        order_id = "order_test_12345678"
        payment_id = "pay_test_87654321"

        # Calculate genuine HMAC-SHA256
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        valid_sig = hmac.new(
            client.key_secret.encode("utf-8"),
            msg,
            hashlib.sha256,
        ).hexdigest()

        # Verify should succeed
        assert client.verify_payment_signature(order_id, payment_id, valid_sig) is True

    def test_signature_verification_tampered_signature_fails(self):
        client = get_razorpay_client()
        order_id = "order_test_12345678"
        payment_id = "pay_test_87654321"
        tampered_sig = "deadbeef1234567890abcdefdeadbeef1234567890abcdef"

        assert client.verify_payment_signature(order_id, payment_id, tampered_sig) is False

    def test_signature_verification_tampered_payload_fails(self):
        client = get_razorpay_client()
        order_id = "order_test_12345678"
        payment_id = "pay_test_87654321"

        msg = f"{order_id}|{payment_id}".encode("utf-8")
        valid_sig = hmac.new(
            client.key_secret.encode("utf-8"),
            msg,
            hashlib.sha256,
        ).hexdigest()

        # Tamper order_id with otherwise valid signature
        assert client.verify_payment_signature("order_test_OTHER", payment_id, valid_sig) is False
        assert client.verify_payment_signature(order_id, "pay_test_OTHER", valid_sig) is False

    def test_signature_verification_missing_args_fails(self):
        client = get_razorpay_client()
        assert client.verify_payment_signature("", "pay_1", "sig_1") is False
        assert client.verify_payment_signature("order_1", "", "sig_1") is False
        assert client.verify_payment_signature("order_1", "pay_1", "") is False


# ============================================================================
# 2. Database Subscription & Payment Lifecycle Tests
# ============================================================================

class TestDatabaseSubscriptionAndPayment:
    def test_subscription_creation_and_retrieval(self, temp_db):
        user_id = temp_db.create_user("SubUser", 28, "Intermediate", "Strength")

        sub_id = temp_db.create_subscription(
            user_id=user_id,
            plan="PRO",
            status="ACTIVE",
            provider="razorpay",
            provider_customer_id="cust_sub_1",
            provider_subscription_id="sub_test_01",
            duration_days=30,
        )
        assert sub_id > 0

        active_sub = temp_db.get_active_subscription(user_id)
        assert active_sub is not None
        assert active_sub["id"] == sub_id
        assert active_sub["plan"] == "PRO"
        assert active_sub["status"] == "ACTIVE"
        assert active_sub["user_id"] == user_id

        # Entitlement check
        assert temp_db.is_user_pro(user_id) is True

    def test_non_pro_user_entitlement(self, temp_db):
        user_id = temp_db.create_user("FreeUser", 24, "Beginner", "General")
        assert temp_db.is_user_pro(user_id) is False
        fallback_sub = temp_db.get_active_subscription(user_id)
        assert fallback_sub["plan"] == "FREE"
        assert fallback_sub["id"] is None

    def test_subscription_cancellation(self, temp_db):
        user_id = temp_db.create_user("CancelUser", 30, "Beginner", "Balance")

        sub_id = temp_db.create_subscription(
            user_id=user_id,
            plan="PRO",
            status="ACTIVE",
            duration_days=30,
        )
        assert temp_db.is_user_pro(user_id) is True

        res = temp_db.cancel_subscription(sub_id)
        assert res is True
        assert temp_db.is_user_pro(user_id) is False

    def test_payment_recording_and_status_update(self, temp_db):
        user_id = temp_db.create_user("PayUser", 29, "Beginner", "Strength")

        payment_id = temp_db.create_payment(
            user_id=user_id,
            order_id="order_test_999",
            amount=799900,
            currency="INR",
            provider="razorpay",
        )
        assert payment_id > 0

        # Retrieve by order ID
        payment = temp_db.get_payment_by_order_id("order_test_999")
        assert payment is not None
        assert payment["status"] == "created"
        assert payment["amount"] == 799900

        # Update status upon payment success
        temp_db.update_payment_status(
            order_id="order_test_999",
            status="captured",
            payment_id="pay_test_999_captured",
            signature="sig_test_valid",
        )

        updated = temp_db.get_payment_by_order_id("order_test_999")
        assert updated["status"] == "captured"
        assert updated["payment_id"] == "pay_test_999_captured"
        assert updated["signature"] == "sig_test_valid"

        # User payments list
        user_payments = temp_db.get_user_payments(user_id)
        assert len(user_payments) == 1
        assert user_payments[0]["order_id"] == "order_test_999"


# ============================================================================
# 3. Flask API Integration Tests
# ============================================================================

class TestPaymentAPIEndpoints:
    def test_payment_config_endpoint(self, client):
        resp = client.get("/api/payment/config")
        assert resp.status_code == 200
        data = resp.get_json()

        assert data["status"] == "success"
        assert "config" in data
        cfg = data["config"]
        assert "key_id" in cfg
        assert "plans" in cfg
        assert "PRO_MONTHLY" in cfg["plans"]
        assert "PRO_ANNUAL" in cfg["plans"]
        # Absolute secret safety verification
        assert "key_secret" not in cfg
        assert "secret" not in cfg

    def test_create_order_endpoint_success(self, client):
        resp = client.post(
            "/api/payment/create-order",
            data=json.dumps({"plan_type": "PRO_MONTHLY", "user_id": 1}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["order_id"].startswith("order_test_")
        assert data["amount"] == 79900
        assert data["currency"] == "INR"

        # Verify payment was tracked in DB
        db_payment = db.get_payment_by_order_id(data["order_id"])
        assert db_payment is not None
        assert db_payment["user_id"] == 1
        assert db_payment["amount"] == 79900

    def test_verify_endpoint_valid_signature_activates_pro(self, client):
        # 1. Create order
        create_resp = client.post(
            "/api/payment/create-order",
            data=json.dumps({"plan_type": "PRO_MONTHLY", "user_id": 1}),
            content_type="application/json",
        )
        order = create_resp.get_json()
        order_id = order["order_id"]
        payment_id = f"pay_test_{order_id.split('_')[-1]}"

        # 2. Compute authentic signature using configured secret
        rzp = get_razorpay_client()
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        valid_signature = hmac.new(rzp.key_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

        # 3. Call verify
        verify_resp = client.post(
            "/api/payment/verify",
            data=json.dumps({
                "order_id": order_id,
                "payment_id": payment_id,
                "signature": valid_signature,
                "plan_type": "PRO_MONTHLY",
                "user_id": 1,
            }),
            content_type="application/json",
        )
        assert verify_resp.status_code == 200
        data = verify_resp.get_json()
        assert data["status"] == "success"
        assert data["is_pro"] is True
        assert "subscription" in data

        # 4. Check user is now Pro in DB
        assert db.is_user_pro(1) is True

    def test_verify_endpoint_invalid_signature_rejected(self, client):
        # 1. Create order
        create_resp = client.post(
            "/api/payment/create-order",
            data=json.dumps({"plan_type": "PRO_MONTHLY", "user_id": 2}),
            content_type="application/json",
        )
        order = create_resp.get_json()
        order_id = order["order_id"]

        # 2. Tampered signature
        tampered_signature = "badf00d" * 8

        # 3. Call verify
        verify_resp = client.post(
            "/api/payment/verify",
            data=json.dumps({
                "order_id": order_id,
                "payment_id": "pay_test_fraud",
                "signature": tampered_signature,
                "plan_type": "PRO_MONTHLY",
                "user_id": 2,
            }),
            content_type="application/json",
        )
        assert verify_resp.status_code == 400
        data = verify_resp.get_json()
        assert data["status"] == "failed"
        assert "failed" in data["message"].lower()

    def test_subscription_status_and_cancel_endpoints(self, client):
        # Ensure user 1 has an active subscription
        temp_order = client.post(
            "/api/payment/create-order",
            data=json.dumps({"plan_type": "PRO_ANNUAL", "user_id": 1}),
            content_type="application/json",
        ).get_json()

        rzp = get_razorpay_client()
        pay_id = "pay_test_ann_1"
        sig = hmac.new(rzp.key_secret.encode("utf-8"), f"{temp_order['order_id']}|{pay_id}".encode("utf-8"), hashlib.sha256).hexdigest()

        client.post(
            "/api/payment/verify",
            data=json.dumps({
                "order_id": temp_order["order_id"],
                "payment_id": pay_id,
                "signature": sig,
                "plan_type": "PRO_ANNUAL",
                "user_id": 1,
            }),
            content_type="application/json",
        )

        # GET subscription
        sub_resp = client.get("/api/subscription/1")
        assert sub_resp.status_code == 200
        sub_data = sub_resp.get_json()
        assert sub_data["status"] == "success"
        assert sub_data["is_pro"] is True
        assert sub_data["subscription"] is not None

        # POST cancel
        cancel_resp = client.post(
            "/api/subscription/cancel",
            data=json.dumps({"user_id": 1}),
            content_type="application/json",
        )
        assert cancel_resp.status_code == 200
        cancel_data = cancel_resp.get_json()
        assert cancel_data["status"] == "success"

        # Re-check user 1 is no longer Pro
        sub_resp2 = client.get("/api/subscription/1")
        assert sub_resp2.get_json()["is_pro"] is False


# ============================================================================
# 4. Security Headers & PWA Manifest Tests
# ============================================================================

class TestSecurityHeadersAndPWA:
    def test_security_headers_present(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

        # CSP check
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "checkout.razorpay.com" in csp
        assert "cdn.jsdelivr.net" in csp

        # Framing and MIME sniffing
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_pwa_web_manifest(self, client):
        resp = client.get("/manifest.json")
        assert resp.status_code == 200
        manifest = resp.get_json()

        assert manifest["name"] == "KI.AI — Personal AI Yoga Teacher"
        assert manifest["short_name"] == "KI.AI"
        assert manifest["start_url"] == "/"
        assert manifest["display"] == "standalone"
        assert manifest["theme_color"] == "#F8F4EC"
        assert manifest["background_color"] == "#F8F4EC"
        assert len(manifest["icons"]) >= 2
