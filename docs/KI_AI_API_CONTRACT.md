# KI.AI Backend API Specification & Contract Reference

**Version:** 2.0.0  
**Updated:** 2026-10-11  
**Architecture:** Flask Application (`web_app.py`) with SQLite Database (`database/database.py`), Computer Vision & Posture Checker (`analysis/`), Stateful AI Coach Engine (`coach/`), and Razorpay Payment Gateway (`payment/`).

---

## 1. Authentication & Security Architecture

### 1.1 Password Hashing & Safe Migration
- All newly created or updated passwords are cryptographically hashed using **Argon2id** (`argon2-cffi`, minimum 64MB memory, 3 iterations, 4 parallelism threads).
- Legacy SHA-256 hashes are automatically detected and rehashed to Argon2id on successful practitioner login without user friction.

### 1.2 Session Management & Cookies
- Server-side signed sessions are managed via Flask with `SECRET_KEY`.
- Session cookies are configured with:
  - `SESSION_COOKIE_HTTPONLY = True` (mitigating XSS theft)
  - `SESSION_COOKIE_SAMESITE = "Lax"` (mitigating CSRF)
  - `SESSION_COOKIE_SECURE = True` in production environments.

### 1.3 Authorization & IDOR Defense (`check_user_access`)
- Every endpoint accepting `user_id` verifies that the active session matches `target_user_id` or possesses administrative status (`is_admin = 1`).
- **Demo Mode Compatibility:** In non-production environments with `KI_AI_DEMO_MODE=true`, unauthenticated requests are permitted for seeded demo practitioners (`user_id = 1` Abhilash and `user_id = 2` Guest User) so frontend workflows and test clients function seamlessly. Any non-demo ID or authenticated cross-user access is strictly blocked with `403 Forbidden`.

### 1.4 Defense-in-Depth Security Headers
Every HTTP response includes:
- `Content-Security-Policy`: Restricts scripts, styles, fonts, frames, and connect endpoints.
- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`

---

## 2. API Endpoints Catalog

---

### 2.1 Authentication & Profile

#### `POST /api/register`
Creates a new practitioner profile.
- **Auth:** Public.
- **Request Body (JSON):**
  ```json
  {
    "name": "Arjun Sharma",
    "email": "arjun@example.com",
    "password": "StrongPassword123",
    "age": 28,
    "experience": "Beginner",
    "goal": "Flexibility"
  }
  ```
- **Validation:**
  - `name`, `email`, `password` required.
  - `password` length >= 6.
  - `email` must contain `@` and be unique.
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "message": "Account created successfully.",
    "user": {
      "id": 5,
      "name": "Arjun Sharma",
      "email": "arjun@example.com",
      "age": 28,
      "experience": "Beginner",
      "goal": "Flexibility",
      "is_admin": 0,
      "created_at": "2026-10-11 12:00:00"
    }
  }
  ```
- **Error Response (400):**
  ```json
  {
    "status": "error",
    "message": "An account with this email already exists."
  }
  ```

#### `POST /api/login`
Authenticates a practitioner, migrates legacy hash if needed, and establishes session.
- **Auth:** Public.
- **Request Body (JSON):**
  ```json
  {
    "email": "abhilash@ki.ai",
    "password": "password123"
  }
  ```
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "message": "Welcome back, Abhilash!",
    "user": {
      "id": 1,
      "name": "Abhilash",
      "email": "abhilash@ki.ai",
      "age": 25,
      "experience": "Intermediate",
      "goal": "Flexibility",
      "is_admin": 1
    }
  }
  ```
- **Error Response (401):**
  ```json
  {
    "status": "error",
    "message": "Invalid email or password."
  }
  ```

#### `POST /api/logout`
Destroys the current session.
- **Auth:** Public / Authenticated.
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "message": "Logged out successfully."
  }
  ```

#### `GET /api/auth/me`
Retrieves currently authenticated session user info.
- **Auth:** Authenticated (or fallback in Demo Mode).
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "authenticated": true,
    "user": {
      "id": 1,
      "name": "Abhilash",
      "email": "abhilash@ki.ai",
      "is_admin": 1
    }
  }
  ```

---

### 2.2 Administrative Console

#### `GET /admin`
Renders administrative control interface (`admin.html`).
- **Auth:** Requires session `is_admin = 1` OR `Authorization: Bearer <ADMIN_TOKEN>` OR `X-Admin-Token: <ADMIN_TOKEN>`.
- **Success Response (200):** HTML document (`templates/admin.html`).
- **Error Response (403):**
  ```json
  {
    "status": "error",
    "message": "Access denied: Administrative privileges required."
  }
  ```

---

### 2.3 Pose Catalog & Surya Namaskar

#### `GET /api/poses`
Lists all active yoga poses with attached biomechanical joint angle rules. Cached in memory for sub-millisecond response.
- **Auth:** Public.
- **Success Response (200):** JSON array of pose objects containing `id`, `name`, `sanskrit_name`, `category`, `difficulty`, `goal`, `rules`, and figure SVG paths.

#### `GET /api/surya`
Lists 12-step Surya Namaskar sun salutation sequence with step progression instructions.
- **Auth:** Public.
- **Success Response (200):** JSON array of the 12 sequential Surya Namaskar steps.

---

### 2.4 AI Posture Evaluation & Single-Pose Analysis

#### `POST /api/analyze_posture`
Evaluates camera landmark coordinates against expected or auto-detected posture.
- **Auth:** Public.
- **Request Body (JSON):**
  ```json
  {
    "landmarks": {
      "NOSE": { "x": 0.5, "y": 0.2, "z": 0.0, "visibility": 0.95 },
      "LEFT_SHOULDER": { "x": 0.45, "y": 0.35, "z": 0.0, "visibility": 0.92 },
      "RIGHT_SHOULDER": { "x": 0.55, "y": 0.35, "z": 0.0, "visibility": 0.91 },
      "LEFT_HIP": { "x": 0.47, "y": 0.60, "z": 0.0, "visibility": 0.88 },
      "RIGHT_HIP": { "x": 0.53, "y": 0.60, "z": 0.0, "visibility": 0.89 },
      "LEFT_KNEE": { "x": 0.47, "y": 0.78, "z": 0.0, "visibility": 0.85 },
      "RIGHT_KNEE": { "x": 0.53, "y": 0.78, "z": 0.0, "visibility": 0.86 },
      "LEFT_ANKLE": { "x": 0.47, "y": 0.95, "z": 0.0, "visibility": 0.82 },
      "RIGHT_ANKLE": { "x": 0.53, "y": 0.95, "z": 0.0, "visibility": 0.83 }
    },
    "expected_pose_id": 1
  }
  ```
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "tracking_state": "GOOD_TRACKING",
    "is_body_visible": true,
    "detected_pose": "Tadasana (Mountain Pose)",
    "target_pose_name": "Tadasana (Mountain Pose)",
    "pose_matched": true,
    "match_score": 92.5,
    "overall_score": 88.0,
    "is_correct_pose": true,
    "is_hold_valid": true,
    "score_level": "GOOD",
    "joint_results": [ ... ],
    "incorrect_joints": [ ... ],
    "primary_feedback": "Stand tall, relax shoulders."
  }
  ```
- **Error Response (400):**
  ```json
  {
    "status": "error",
    "message": "No landmark data provided"
  }
  ```

#### `POST /api/save_session`
Records a single-pose practice attempt into the database.
- **Auth:** IDOR protected (`check_user_access`).
- **Request Body (JSON):**
  ```json
  {
    "user_id": 1,
    "pose_id": 1,
    "duration": 60,
    "average_score": 85.5,
    "final_score": 90.0,
    "hold_duration": 25,
    "corrections_count": 2
  }
  ```
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "session_id": 104
  }
  ```

---

### 2.5 History, Statistics, Recommendations, & Learning Programs

#### `GET /api/history/<int:user_id>`
Retrieves chronological practice logs for practitioner.
- **Auth:** IDOR protected.
- **Query Parameters:** `?pose=Tadasana&min_score=75.0` (optional filters).
- **Success Response (200):** Array of historical practice sessions.
- **Error Response (403):** Access denied.
- **Error Response (404):** User ID not found.

#### `GET /api/stats/<int:user_id>`
Retrieves aggregate practice metrics, day streak, and score progression.
- **Auth:** IDOR protected.
- **Success Response (200):**
  ```json
  {
    "stats": {
      "total_sessions": 14,
      "total_duration_minutes": 185.0,
      "average_score": 84.2,
      "current_streak": 3,
      "total_poses_practiced": 8
    },
    "progression": [ ... ],
    "pose_breakdown": [ ... ]
  }
  ```

#### `GET /api/recommendations/<int:user_id>`
Retrieves AI-curated posture recommendations targeting practitioner goals and weak joints.
- **Auth:** IDOR protected.
- **Success Response (200):** List of recommended pose items with rationale and relevance score.

#### `GET /api/programs`
Retrieves the 3 tiered learning tracks (Foundation, Progress, Mastery) with dynamic unlock status based on practitioner readiness.
- **Auth:** IDOR protected (`?user_id=1`).
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "programs": [ ... ],
    "unlock_info": {
      "foundation_unlocked": true,
      "progress_unlocked": true,
      "mastery_unlocked": false,
      "avg_score": 82.0,
      "completed_sessions": 8
    }
  }
  ```

---

### 2.6 Multi-Exercise Guided AI Sessions

#### `POST /api/session/start`
Initializes a multi-exercise guided session plan with per-user isolated coach engine state.
- **Auth:** IDOR protected (`check_user_access`).
- **Request Body (JSON):**
  ```json
  {
    "user_id": 1,
    "duration": 20,
    "goal": "Flexibility",
    "level": "Beginner",
    "focus": "Spinal Mobility"
  }
  ```
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "session_id": "plan_1_1728639200",
    "session_plan": {
      "id": "plan_1_1728639200",
      "exercises": [ ... ]
    }
  }
  ```

#### `POST /api/session/evaluate_frame`
Real-time frame evaluation for active guided exercise. Evaluates landmarks against loaded exercise, advances hold countdown only on stable alignment, and pauses on tracking loss or poor posture.
- **Auth:** Public / Session (`user_id` optional, defaults to 1).
- **Request Body (JSON):**
  ```json
  {
    "user_id": 1,
    "landmarks": { ... },
    "exercise": {
      "name": "Tadasana",
      "target_pose_id": 1,
      "hold_seconds": 20
    }
  }
  ```
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "evaluation": {
      "state": "HOLDING",
      "score": 88.5,
      "is_aligned": true,
      "hold_seconds": 6.5,
      "target_seconds": 20.0,
      "speech_cue": null,
      "status_label": "Holding Posture",
      "status_code": "HOLD_TICKING"
    },
    "tracking_state": "GOOD_TRACKING",
    "is_body_visible": true,
    "is_hold_valid": true,
    "match_score": 91.0
  }
  ```

#### `POST /api/session/complete`
Finalizes and logs a completed multi-exercise guided session.
- **Auth:** IDOR protected.
- **Request Body (JSON):**
  ```json
  {
    "user_id": 1,
    "session_plan_id": "plan_1_1728639200",
    "program_level": "Beginner",
    "total_duration_seconds": 1200,
    "average_accuracy": 86.5,
    "completed_exercises": 8,
    "total_exercises": 8,
    "best_pose": "Warrior I",
    "weakest_joint": "left_knee"
  }
  ```
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "message": "AI Session Successfully Completed!",
    "summary": { ... }
  }
  ```

---

### 2.7 Interactive Conversational Coach & Voice Cues

#### `POST /api/coach/message`
Submits practitioner voice or chat message to conversational AI coach. Handles intents like skip pose, shorten session, pain/safety warnings, and score clarification.
- **Auth:** IDOR protected.
- **Request Body (JSON):**
  ```json
  {
    "user_id": 1,
    "message": "My right knee is hurting",
    "context": { "current_pose": "Warrior I" }
  }
  ```
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "coach": {
      "response": "Please ease out of the posture immediately. Never push through joint pain.",
      "intent": "safety_alert",
      "action": "pause_or_skip"
    }
  }
  ```

#### `GET /api/voice/status`
Returns real-time voice controller state (speech queue size, active request, muted state, stopped state).

#### `POST /api/voice/stop` | `POST /api/voice/resume`
Immediately cancels active speech queue or resumes playback.

#### `POST /api/voice/mute` | `POST /api/voice/unmute`
Mutes/unmutes voice feedback while preserving critical safety announcements.

---

### 2.8 Subscription & Payment Processing (Razorpay)

#### `GET /api/payment/config`
Retrieves public gateway configuration. **Strictly never exposes secret key.**
- **Auth:** Public.
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "config": {
      "key_id": "rzp_test_ki_ai_preview",
      "is_test_mode": true,
      "currency": "INR",
      "plans": {
        "PRO_MONTHLY": {
          "name": "KI.AI Pro Monthly",
          "amount_rupees": 799,
          "duration_days": 30
        },
        "PRO_ANNUAL": {
          "name": "KI.AI Pro Annual",
          "amount_rupees": 7999,
          "duration_days": 365
        }
      }
    }
  }
  ```

#### `POST /api/payment/create-order`
Generates authorized payment order.
- **Auth:** IDOR protected (`check_user_access`).
- **Request Body (JSON):**
  ```json
  {
    "user_id": 1,
    "plan_type": "PRO_MONTHLY"
  }
  ```
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "order_id": "order_test_a1b2c3d4",
    "amount": 79900,
    "currency": "INR",
    "key_id": "rzp_test_ki_ai_preview",
    "plan_type": "PRO_MONTHLY",
    "is_test_mode": true
  }
  ```

#### `POST /api/payment/verify`
Server-side cryptographic verification of Razorpay payment signature using HMAC-SHA256 (`HMAC-SHA256(order_id + "|" + payment_id, secret)`). Activates Pro subscription upon successful match. Idempotent against duplicate calls.
- **Auth:** IDOR protected.
- **Request Body (JSON):**
  ```json
  {
    "user_id": 1,
    "order_id": "order_test_a1b2c3d4",
    "payment_id": "pay_test_999",
    "signature": "valid_hmac_hex_signature",
    "plan_type": "PRO_MONTHLY"
  }
  ```
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "message": "Payment verified and Pro subscription activated!",
    "is_pro": true,
    "subscription": {
      "plan": "PRO",
      "status": "ACTIVE",
      "expires_at": "2026-11-10 12:00:00"
    }
  }
  ```
- **Error Response (400):** Signature verification mismatch or missing required arguments.

#### `POST /api/payment/webhook`
Asynchronous notification listener for Razorpay gateway events. Validates `X-Razorpay-Signature` header via HMAC-SHA256 against `RAZORPAY_WEBHOOK_SECRET`.
- **Auth:** Cryptographic signature header.
- **Success Response (200):** `{"status": "received"}`.
- **Error Response (400):** `{"status": "failed", "message": "Invalid webhook signature"}`.

#### `GET /api/subscription/<int:user_id>`
Retrieves current subscription status and Pro feature entitlement.
- **Auth:** IDOR protected.
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "is_pro": true,
    "subscription": {
      "id": 1,
      "plan": "PRO",
      "status": "ACTIVE",
      "expires_at": "2026-11-10 12:00:00"
    }
  }
  ```

#### `POST /api/subscription/cancel`
Cancels active auto-renewing Pro subscription.
- **Auth:** IDOR protected.
- **Request Body (JSON):** `{"user_id": 1}`.
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "message": "Subscription cancelled. Your Pro access remains active until the end of your billing cycle."
  }
  ```
