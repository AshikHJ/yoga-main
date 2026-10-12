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

#### `GET /api/auth/google`
Initiates Google OAuth 2.0 authorization code flow.
- **Auth:** Public.
- **Behavior:** Generates a cryptographically random CSRF `state` parameter, persists it in the Flask session, and redirects browser to `https://accounts.google.com/o/oauth2/v2/auth`.
- **Error Response (503):** If `GOOGLE_CLIENT_ID` is not configured on the server, returns setup instructions.

#### `GET /api/auth/google/callback`
Handles OAuth 2.0 redirect callback from Google.
- **Auth:** Public with CSRF validation.
- **Query Parameters:** `code` (authorization code), `state` (CSRF token).
- **Behavior:**
  1. Validates `state` against `session['oauth_state']` to prevent CSRF.
  2. Exchanges `code` for Google access tokens via `https://oauth2.googleapis.com/token`.
  3. Fetches user profile from `https://www.googleapis.com/oauth2/v3/userinfo`.
  4. Links existing account or provisions a new user in SQLite via `db.get_or_create_google_user`.
  5. Sets server-side session `session['user_id'] = user['id']`.
  6. Redirects browser to `/?google_auth=success` (or `/?auth_error=...` on failure).

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

#### `GET /api/session/current`
Retrieves live state snapshot of active practice session (re-synchronizing browser after page reload or camera re-connection).
- **Auth:** Public / Session (`?user_id=1`).
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "active": true,
    "step_index": 0,
    "session": {
      "session_id": "104",
      "session_state": "HOLDING",
      "is_paused": false,
      "camera_active": true,
      "current_pose": {
        "id": 1,
        "name": "Mountain Pose (Tadasana)",
        "hold_seconds": 4.5,
        "remaining_seconds": 15.5,
        "target_seconds": 20.0
      },
      "next_pose": {
        "id": 2,
        "name": "Tree Pose (Vrikshasana)"
      },
      "sequence_progress": {
        "current_index": 0,
        "total_poses": 5,
        "completed_poses": 0,
        "percent_complete": 0.0
      }
    }
  }
  ```

#### `POST /api/session/next` | `POST /api/session/skip`
Advances the practice sequence to the next scheduled asana.
- **Auth:** Public / Session.
- **Request Body (JSON):** `{"user_id": 1}`.
- **Success Response (200):** Updated session snapshot with `step_index` advanced.

#### `POST /api/session/pause` | `POST /api/session/resume`
Freezes or resumes the hold timer countdown without discarding accumulated hold seconds.
- **Auth:** Public / Session.
- **Request Body (JSON):** `{"user_id": 1, "reason": "Water break"}`.
- **Success Response (200):** Updated session snapshot with `is_paused: true/false`.

#### `POST /api/session/camera_error`
Notifies the backend that the webcam stream was lost or disconnected, safely freezing the hold countdown with a tracking warning.
- **Auth:** Public / Session.
- **Request Body (JSON):** `{"user_id": 1, "error": "Camera frame timeout"}`.
- **Success Response (200):** `{"status": "success", "tracking_warning": "Camera frame timeout"}`.

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

### 2.8 Kiki AI Companion & Conversational Intelligence

#### `POST /api/kiki/chat`
Conversational dialogue with Kiki, grounded in live posture assessment, joint deviations, and classical yoga wisdom. Integrates Google Gemini LLM via REST with seamless fallback to verified classical database knowledge base.
- **Auth:** Public / Session.
- **Request Body (JSON):**
  ```json
  {
    "user_id": 1,
    "message": "Why is my posture score low?",
    "history": [
      { "role": "user", "message": "I am in Warrior II" },
      { "role": "model", "message": "Keep your front knee stacked over your ankle." }
    ]
  }
  ```
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "reply": "Your current posture accuracy is 68%. The main adjustment is your front knee, currently at 135° instead of 90°. Bend your front knee deeper toward 90 degrees.",
    "speak_text": "Your main adjustment is your front knee, off by 45 degrees. Follow the visual cue to align it.",
    "voice_gender": "female",
    "character_state": "adjust_pose",
    "kiki_state": "adjust_pose",
    "safety_alert": false,
    "action": "EXPLAIN_SCORE",
    "intent": "score_explanation"
  }
  ```

#### `GET /api/kiki/state`
Returns Kiki's active 9-state character enum (`idle`, `listening`, `thinking`, `confused`, `incorrect_pose`, `adjust_pose`, `correct_pose`, `celebrating`, `error`) alongside current pose guide and live speech cues.
- **Auth:** Public / Session (`?user_id=1`).
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "character_state": "correct_pose",
    "kiki_state": "correct_pose",
    "has_active_pose": true,
    "pose_name": "Warrior II",
    "speech_cue": "Halfway there. Maintain steady breath."
  }
  ```

#### `GET /api/kiki/guide/<int:pose_id>`
Retrieves verified classical alignment rules, benefits, precautions, and target joint angle tolerances for a specific asana.
- **Auth:** Public.
- **Success Response (200):** Comprehensive pose rule dictionary with target angles and tolerances.

---

### 2.9 100% Free Access Model & Entitlements

KI.AI is an open, completely free yoga intelligence application. All features (all 24 classical asanas, Surya Namaskar, personalized sequences, deep Kiki companion coaching, and advanced biomechanical analytics) are fully unlocked for all authenticated practitioners without paywalls or subscription restrictions.

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

---

### 8. Beta Programs & Waitlist

#### `POST /api/beta/signup`
Enrolls interest in upcoming specialized AI modules (e.g., Karate AI / Martial Arts) without altering core user tables.
- **Auth:** Public / Anonymous.
- **Request Body (JSON):**
  ```json
  {
    "email": "practitioner@example.com",
    "program": "karate"
  }
  ```
- **Success Response (201):**
  ```json
  {
    "status": "success",
    "message": "Successfully joined the karate beta waitlist!"
  }
  ```
- **Error Response (400):** Invalid email format.

---

### 9. Centralized Entitlements & Pro Feature Gates

#### `GET /api/user/entitlements`
Returns authoritative feature entitlements for currently authenticated session user.
- **Auth:** Active session (or default demo user in demo mode).
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "user_id": 1,
    "is_pro": true,
    "is_admin": true,
    "plan": "PRO",
    "subscription_status": "ACTIVE",
    "expires_at": "2027-10-11 10:47:30",
    "subscription_id": 83,
    "features": {
      "basic_poses": true,
      "standard_session": true,
      "general_kiki": true,
      "pro_poses": true,
      "advanced_analytics": true,
      "kiki_deep_coaching": true,
      "unlimited_sessions": true,
      "custom_routines": true,
      "posture_breakdown": true
    }
  }
  ```

#### `GET /api/entitlements/<int:user_id>`
Returns authoritative feature entitlements for specified user ID.
- **Auth:** IDOR protected (requires self or admin).
- **Success Response (200):** Returns same payload shape as above.
- **Error Response (403):** Access denied.
- **Error Response (404):** Target user not found.

#### `GET /api/pro/advanced-analytics/<int:user_id>`
Pro-tier endpoint returning in-depth biomechanical stability scores, mobility index, bilateral symmetry ratios, and practice streaks.
- **Auth:** Server-side Pro entitlement gate (`@require_pro`).
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "user_id": 1,
    "is_pro": true,
    "advanced_analytics": {
      "mobility_index": 88.5,
      "bilateral_symmetry_ratio": 0.94,
      "consistency_streak_days": 3,
      "joint_stability_scores": {
        "knees": 91.0,
        "hips": 84.5,
        "shoulders": 89.0,
        "spine": 86.0
      },
      "history_summary": [...]
    }
  }
  ```
- **Error Response (403):**
  ```json
  {
    "status": "forbidden",
    "code": "PRO_ENTITLEMENT_REQUIRED",
    "message": "This feature requires an active KI.AI Pro subscription.",
    "feature": "advanced_analytics",
    "upgrade_url": "/#pricing",
    "current_plan": "FREE"
  }
  ```

---

### 10. Kiki AI Companion & Real-Time Coaching

#### `GET /api/kiki/state?user_id=<int:user_id>`
Retrieves Kiki AI Companion's real-time character state, active pose guide, and latest verified biomechanical assessment.
- **Auth:** Public / Practitioner session.
- **Character States (9 Canonical States):**
  - `idle`: Camera resting or practitioner out of frame.
  - `listening`: Actively listening for voice commands or questions.
  - `thinking`: Processing user inquiry or generating tailored alignment cue.
  - `confused`: Body partially occluded, out-of-frame limbs, or low landmark confidence (< 0.35 visibility).
  - `incorrect_pose`: Mismatched pose detected or major alignment deviation.
  - `adjust_pose`: Minor joint adjustments needed to achieve target angle range.
  - `correct_pose`: Proper alignment confirmed (holding posture).
  - `celebrating`: Target hold duration achieved or session completed.
  - `error`: Vision pipeline or camera hardware exception.
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "kiki_state": "adjust_pose",
    "character_state": "adjust_pose",
    "coaching_message": "Bend your front knee deeper toward 90 degrees.",
    "hold_metrics": {
      "hold_seconds": 6.2,
      "target_seconds": 20.0,
      "is_aligned": false
    },
    "kiki": {
      "character_state": "adjust_pose",
      "has_active_pose": true,
      "pose_name": "Warrior II",
      "assessment": {
        "overall_score": 72.0,
        "status_state": "adjust",
        "is_aligned": false,
        "hold_seconds": 6.2,
        "target_seconds": 20.0,
        "measured_joints": [
          {
            "joint_name": "left_knee",
            "actual_angle": 125.0,
            "target_angle": 90.0,
            "deviation": 35.0,
            "status_code": "WARNING",
            "feedback_message": "Bend your front knee deeper toward 90 degrees"
          }
        ]
      }
    }
  }
  ```

#### `POST /api/kiki/chat`
Conversational dialogue interface with grounded biomechanical session context, safety guardrails, and persistent history logging.
- **Auth:** IDOR protected.
- **Request Body (JSON):**
  ```json
  {
    "user_id": 1,
    "message": "Why is my posture score low?"
  }
  ```
- **Safety Guardrail Behavior:**
  - Queries mentioning pain, injury, strain, tears, sharp aches, or sprains trigger an immediate safety alert:
  ```json
  {
    "status": "success",
    "kiki_state": "confused",
    "reply": "Please stop the movement immediately. If you are experiencing pain or sharp discomfort, release the pose gently and rest in Child's pose (Balasana). KI.AI provides computer-vision fitness guidance and is not a substitute for medical advice from a doctor or healthcare professional.",
    "action": "PAUSE_AND_REST"
  }
  ```
- **Biomechanical Explanation Behavior:**
  - Explains scores truthfully using actual measured joint angles and deviations from live session data without hallucinating models.

#### `GET /api/kiki/guide/<int:pose_id>`
Retrieves verified classical pose rules, instructions, target angles, benefits, and anatomical precautions.
- **Auth:** Public.
- **Success Response (200):**
  ```json
  {
    "status": "success",
    "id": 1,
    "name": "Tadasana",
    "sanskrit_name": "Mountain Pose",
    "category": "Standing",
    "difficulty": "Beginner",
    "rules": [
      {
        "joint_name": "torso_vertical",
        "target_angle": 90.0,
        "tolerance": 15.0,
        "feedback": "Keep torso aligned vertically over hips"
      }
    ],
    "benefits": ["Improves posture", "Strengthens thighs and ankles"],
    "precautions": "Avoid if experiencing dizziness or low blood pressure."
  }
  ```
- **Error Response (404):** Pose ID not found.
