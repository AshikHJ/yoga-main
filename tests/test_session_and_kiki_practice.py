"""
Production test suite for KI.AI Practice Session Controller, Multi-Asana Sequences,
Tracking Confidence Separation, and Kiki AI Companion Conversational Delivery.
"""

import json
import time
import pytest
from coach.session_controller import PracticeSessionController, AsanaStep, SessionLifecycleState
from coach.kiki import KikiService, clean_spoken_text, KikiCharacterState
from web_app import app, db, get_session_controller_for_user, set_session_controller_for_user, clear_session_controller_for_user
from coach.state_machine import SessionState


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "practice_session_test_secret"
    with app.test_client() as c:
        yield c


# ============================================================================
# 1. PracticeSessionController Monotonic Timer & Transition Tests
# ============================================================================

class TestPracticeSessionController:
    """Verifies sequence management, monotonic hold timers, halfway milestones, and transitions."""

    def test_session_controller_multi_pose_sequence_initialization(self):
        exercises = [
            {"id": 1, "name": "Tadasana", "hold_seconds": 5.0},
            {"id": 2, "name": "Vrikshasana", "hold_seconds": 10.0},
            {"id": 3, "name": "Virabhadrasana II", "hold_seconds": 8.0},
        ]
        controller = PracticeSessionController(session_id="session_test_01", user_id=101, exercises=exercises)

        assert len(controller.steps) == 3
        assert controller.current_index == 0
        assert controller.current_step is not None
        assert controller.current_step.name == "Tadasana"
        assert controller.is_paused is False

    def test_monotonic_hold_timer_and_halfway_milestone(self):
        exercises = [
            {"id": 1, "name": "Tadasana", "hold_seconds": 4.0},
            {"id": 2, "name": "Vrikshasana", "hold_seconds": 6.0},
        ]
        controller = PracticeSessionController(session_id="session_test_02", user_id=102, exercises=exercises)

        # 1. Poor posture does not advance hold timer
        res1 = controller.tick_evaluation(is_valid_hold=False, score=40.0, dt=1.0)
        assert res1["current_pose"]["hold_seconds"] == 0.0

        # 2. Correct posture advances hold timer
        res2 = controller.tick_evaluation(is_valid_hold=True, score=85.0, dt=1.0)
        assert res2["current_pose"]["hold_seconds"] == 1.0

        # 3. Correct posture reaches halfway milestone (2.0s of 4.0s)
        res3 = controller.tick_evaluation(is_valid_hold=True, score=88.0, dt=1.0)
        assert res3["current_pose"]["hold_seconds"] == 2.0
        assert "speech_cue" in res3
        assert "Halfway" in res3["speech_cue"]

        # 4. Correct posture completes hold and automatically transitions to next pose
        controller.tick_evaluation(is_valid_hold=True, score=90.0, dt=1.0)
        res5 = controller.tick_evaluation(is_valid_hold=True, score=92.0, dt=1.0)
        assert res5["sequence_progress"]["current_index"] == 1
        assert res5["current_pose"]["name"] == "Vrikshasana"
        assert "Moving to Vrikshasana" in res5.get("speech_cue", "")

    def test_transition_cooldown_prevents_duplicate_transitions(self):
        """Verifies rapid frames arriving within cooldown window do not double-transition."""
        exercises = [
            {"id": 1, "name": "Pose A", "hold_seconds": 2.0},
            {"id": 2, "name": "Pose B", "hold_seconds": 5.0},
            {"id": 3, "name": "Pose C", "hold_seconds": 5.0},
        ]
        controller = PracticeSessionController(session_id="session_test_03", user_id=103, exercises=exercises)

        # Reach completion of Pose A
        controller.tick_evaluation(is_valid_hold=True, score=85.0, dt=1.0)
        res_trans = controller.tick_evaluation(is_valid_hold=True, score=90.0, dt=1.0)
        assert res_trans["sequence_progress"]["current_index"] == 1
        assert controller.current_step.name == "Pose B"

        # Rapid frame arriving immediately during cooldown window (0.1s dt) does not advance again
        res_rapid = controller.tick_evaluation(is_valid_hold=True, score=95.0, dt=0.1)
        assert res_rapid["sequence_progress"]["current_index"] == 1
        assert controller.current_step.name == "Pose B"

    def test_session_controller_pause_resume(self):
        exercises = [{"id": 1, "name": "Tadasana", "hold_seconds": 10.0}]
        controller = PracticeSessionController(session_id="session_test_04", user_id=104, exercises=exercises)

        controller.tick_evaluation(is_valid_hold=True, score=80.0, dt=1.0)
        controller.tick_evaluation(is_valid_hold=True, score=80.0, dt=1.0)
        assert controller.current_step.hold_seconds == 2.0

        # Pause freezes countdown
        controller.pause_session(reason="User drink water")
        assert controller.is_paused is True
        res_paused = controller.tick_evaluation(is_valid_hold=True, score=85.0, dt=1.0)
        assert res_paused["is_paused"] is True
        assert res_paused["current_pose"]["hold_seconds"] == 2.0

        # Resume allows timer to continue
        controller.resume_session()
        assert controller.is_paused is False
        res_resumed = controller.tick_evaluation(is_valid_hold=True, score=85.0, dt=1.0)
        assert res_resumed["current_pose"]["hold_seconds"] == 3.0

    def test_session_controller_camera_error_and_recovery(self):
        exercises = [{"id": 1, "name": "Utkatasana", "hold_seconds": 10.0}]
        controller = PracticeSessionController(session_id="session_test_05", user_id=105, exercises=exercises)

        controller.tick_evaluation(is_valid_hold=True, score=85.0, dt=1.0)
        assert controller.current_step.hold_seconds == 1.0

        # Camera error halts timer and records pause reason
        controller.handle_camera_error("Camera feed disconnected.")
        assert controller.camera_active is False
        assert controller.is_paused is True
        assert "Camera error" in controller.pause_reason

        # Restoring camera allows user to continue without loss of accumulated progress
        controller.handle_camera_restored()
        assert controller.camera_active is True
        assert controller.is_paused is False
        assert controller.current_step.hold_seconds == 1.0

    def test_session_controller_skip_and_finish(self):
        exercises = [
            {"id": 1, "name": "Pose 1", "hold_seconds": 5.0},
            {"id": 2, "name": "Pose 2", "hold_seconds": 5.0},
        ]
        controller = PracticeSessionController(session_id="session_test_06", user_id=106, exercises=exercises)

        skip_res = controller.skip_current_asana()
        assert skip_res["sequence_progress"]["current_index"] == 1
        assert skip_res["current_pose"]["name"] == "Pose 2"

        # Skip final pose completes session
        fin_res = controller.skip_current_asana()
        assert fin_res["session_state"] == SessionLifecycleState.COMPLETED.value
        assert "completed" in fin_res["speech_cue"].lower()


# ============================================================================
# 2. Flask Practice Session Lifecycle API Integration Tests
# ============================================================================

class TestPracticeSessionAPI:
    """Verifies API endpoints for full-screen camera practice and session lifecycle."""

    def test_api_session_lifecycle_flow(self, client):
        user_id = 1
        with client.session_transaction() as sess:
            sess["user_id"] = user_id

        # 1. Start multi-pose practice session
        start_resp = client.post(
            "/api/session/start",
            data=json.dumps({
                "user_id": user_id,
                "sequence_name": "Morning Flow",
                "target_duration_seconds": 120,
                "poses": [
                    {"id": 1, "name": "Mountain Pose (Tadasana)", "hold_duration": 5},
                    {"id": 2, "name": "Tree Pose (Vrikshasana)", "hold_duration": 8},
                ],
            }),
            content_type="application/json",
        )
        assert start_resp.status_code == 200
        start_data = start_resp.get_json()
        assert start_data["status"] == "success"
        assert "session_id" in start_data

        # 2. Query current session state
        curr_resp = client.get(f"/api/session/current?user_id={user_id}")
        assert curr_resp.status_code == 200
        curr_data = curr_resp.get_json()
        assert curr_data["status"] == "success"
        assert curr_data["active"] is True
        assert curr_data["step_index"] == 0

        # 3. Pause session
        pause_resp = client.post(
            "/api/session/pause",
            data=json.dumps({"user_id": user_id}),
            content_type="application/json",
        )
        assert pause_resp.status_code == 200
        assert pause_resp.get_json()["is_paused"] is True

        # 4. Resume session
        res_resp = client.post(
            "/api/session/resume",
            data=json.dumps({"user_id": user_id}),
            content_type="application/json",
        )
        assert res_resp.status_code == 200
        assert res_resp.get_json()["is_paused"] is False

        # 5. Skip to next pose
        skip_resp = client.post(
            "/api/session/skip",
            data=json.dumps({"user_id": user_id}),
            content_type="application/json",
        )
        assert skip_resp.status_code == 200
        skip_data = skip_resp.get_json()
        assert skip_data["step_index"] == 1

        # 6. Report camera error
        cam_resp = client.post(
            "/api/session/camera_error",
            data=json.dumps({"user_id": user_id, "error": "Camera frame timeout"}),
            content_type="application/json",
        )
        assert cam_resp.status_code == 200
        assert cam_resp.get_json()["tracking_warning"] == "Camera frame timeout"

    def test_tracking_confidence_vs_posture_score_separation(self, client):
        """Verifies clear separation of landmark tracking confidence and posture correctness."""
        user_id = 1
        with client.session_transaction() as sess:
            sess["user_id"] = user_id

        # Missing lower body landmarks: partial tracking confidence
        partial_landmarks = [
            {"name": "NOSE", "x": 0.5, "y": 0.2, "visibility": 0.9},
            {"name": "LEFT_SHOULDER", "x": 0.45, "y": 0.35, "visibility": 0.8},
            {"name": "RIGHT_SHOULDER", "x": 0.55, "y": 0.35, "visibility": 0.8},
            {"name": "LEFT_HIP", "x": 0.47, "y": 0.55, "visibility": 0.7},
            {"name": "RIGHT_HIP", "x": 0.53, "y": 0.55, "visibility": 0.7},
            # Missing knees, ankles, feet
        ]

        resp = client.post(
            "/api/session/evaluate_frame",
            data=json.dumps({
                "user_id": user_id,
                "landmarks": partial_landmarks,
                "timestamp": 12.5,
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()

        # Tracking confidence must be reported distinctly
        assert "tracking_confidence" in data
        assert "overall_score" in data
        assert "is_body_visible" in data
        # In partial tracking, accuracy is marked invalid to prevent misleading score
        assert data["accuracy_valid"] is False
        assert data["tracking_state"] in ("PARTIAL_BODY", "NO_PERSON")


# ============================================================================
# 3. Kiki Multi-Turn Dialogue & Spoken Text Formatting
# ============================================================================

class TestKikiDialogueAndSpeech:
    """Verifies Kiki conversation history support and clean spoken text delivery."""

    def test_clean_spoken_text_strips_markdown_and_formatting(self):
        raw_text = (
            "**Warrior II** (Virabhadrasana II):\n"
            "- *Key alignment:* Bend your front knee to 90 degrees!\n"
            "- Keep arms parallel [level with shoulders].\n"
            "# Remember: smooth breathing."
        )
        cleaned = clean_spoken_text(raw_text)
        assert "**" not in cleaned
        assert "*" not in cleaned
        assert "#" not in cleaned
        assert "[" not in cleaned
        assert "]" not in cleaned
        assert "Warrior II" in cleaned
        assert "Bend your front knee to 90 degrees" in cleaned

    def test_kiki_multi_turn_history_preservation(self):
        kiki = KikiService(db)
        history = [
            {"role": "user", "message": "What is Mountain Pose?"},
            {"role": "model", "message": "Mountain pose or Tadasana is the foundational standing posture."},
        ]
        res = kiki.process_query(
            user_message="What are its benefits?",
            user_id=1,
            history=history,
        )
        assert res["reply"] is not None
        assert res["speak_text"] is not None
        assert res["voice_gender"] == "female"
