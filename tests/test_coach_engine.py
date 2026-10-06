"""
Unit and integration tests for KI.AI Coach Engine, State Machine,
Conversational AI Coach, and API Endpoints.
"""

import json
import pytest
from coach.state_machine import SessionState, SessionStateMachine
from coach.coach_engine import CoachEngine
from coach.conversation import ConversationalCoach
from database.database import Database
from web_app import app


class TestSessionStateMachine:
    """Verifies state machine transitions and hold timer mechanics."""

    def test_initial_state(self):
        sm = SessionStateMachine()
        assert sm.current_state == SessionState.IDLE
        assert sm.current_hold_seconds == 0.0
        assert sm.target_hold_seconds == 20.0

    def test_valid_transitions(self):
        sm = SessionStateMachine()
        assert sm.transition_to(SessionState.PREPARING)
        assert sm.current_state == SessionState.PREPARING

        assert sm.transition_to(SessionState.DETECTING)
        assert sm.current_state == SessionState.DETECTING

        assert sm.transition_to(SessionState.HOLDING)
        assert sm.current_state == SessionState.HOLDING

        # Pause and resume
        assert sm.transition_to(SessionState.PAUSED)
        assert sm.current_state == SessionState.PAUSED

        assert sm.transition_to(SessionState.HOLDING)
        assert sm.current_state == SessionState.HOLDING

        # Complete pose
        assert sm.transition_to(SessionState.COMPLETING_POSE)
        assert sm.current_state == SessionState.COMPLETING_POSE

        # Transition to next pose
        assert sm.transition_to(SessionState.TRANSITION)
        assert sm.current_state == SessionState.TRANSITION

    def test_invalid_transition_rejected(self):
        sm = SessionStateMachine()
        # Direct jump from IDLE to COMPLETING_POSE is disallowed
        assert not sm.transition_to(SessionState.COMPLETING_POSE)
        assert sm.current_state == SessionState.IDLE

    def test_hold_timer_progression_and_pause(self):
        sm = SessionStateMachine()
        sm.set_target_hold(5.0)
        sm.transition_to(SessionState.PREPARING)
        sm.transition_to(SessionState.DETECTING)

        # Tick while valid
        is_complete, state = sm.tick_hold_timer(delta_seconds=2.0, is_valid_frame=True)
        assert not is_complete
        assert state == SessionState.HOLDING
        assert pytest.approx(sm.current_hold_seconds, 0.1) == 2.0

        # Tick with invalid frame (breaks hold, transitions to PAUSED)
        is_complete, state = sm.tick_hold_timer(delta_seconds=1.0, is_valid_frame=False)
        assert not is_complete
        assert state == SessionState.PAUSED
        # Timer should not have increased
        assert pytest.approx(sm.current_hold_seconds, 0.1) == 2.0

        # Resume valid frames until completion
        is_complete, state = sm.tick_hold_timer(delta_seconds=2.0, is_valid_frame=True)
        assert not is_complete
        assert state == SessionState.HOLDING

        is_complete, state = sm.tick_hold_timer(delta_seconds=1.5, is_valid_frame=True)
        assert is_complete
        assert state == SessionState.COMPLETING_POSE
        assert sm.is_hold_completed()


class TestCoachEngine:
    """Verifies CoachEngine evaluation and speech throttling."""

    def test_load_exercise(self):
        engine = CoachEngine(voice_cooldown_seconds=3.0)
        exercise = {
            "name": "Vrikshasana (Tree Pose)",
            "hold_seconds": 15,
            "target_pose_id": 2,
        }
        engine.load_exercise(exercise)
        assert engine.current_exercise["name"] == "Vrikshasana (Tree Pose)"
        assert engine.state_machine.target_hold_seconds == 15.0

    def test_body_not_visible(self):
        engine = CoachEngine()
        engine.load_exercise({"name": "Tadasana", "hold_seconds": 10})
        res = engine.evaluate_frame(
            detected_pose_name="Tadasana",
            match_score=90.0,
            posture_eval={"overall_score": 90.0},
            is_body_visible=False,
        )
        assert res["status_code"] == "NOT_VISIBLE"
        assert "visible" in (res["speech_cue"] or "").lower()

    def test_aligned_pose_advances_hold(self):
        engine = CoachEngine(voice_cooldown_seconds=0.1)
        engine.load_exercise({"name": "Tadasana", "hold_seconds": 5})
        engine.state_machine.transition_to(SessionState.DETECTING)

        # 3 stable frames to enter hold, then tick
        for _ in range(4):
            res = engine.evaluate_frame(
                detected_pose_name="Tadasana",
                match_score=95.0,
                posture_eval={"overall_score": 90.0, "primary_feedback": "Great alignment"},
                is_body_visible=True,
                dt=1.0,
            )

        assert engine.state_machine.current_hold_seconds > 0.0


class TestConversationalCoach:
    """Verifies conversational coach intents, safety alerts, and suggestions."""

    def test_safety_pain_alert(self):
        coach = ConversationalCoach()
        queries = [
            "My right knee hurts really bad",
            "I feel sharp pain in my lower back",
            "This causes shoulder discomfort",
            "I have an injury here",
        ]
        for q in queries:
            result = coach.process_message(q)
            assert result["safety_alert"] is True
            assert result["action"] == "PAUSE_AND_REST"
            assert "stop" in result["response"].lower()

    def test_skip_pose_intent(self):
        coach = ConversationalCoach()
        result = coach.process_message(
            "Can we skip this pose?",
            context={"current_pose_name": "Trikonasana"},
        )
        assert result["action"] == "SKIP_POSE"
        assert "skipping" in result["response"].lower()
        assert "trikonasana" in result["response"].lower()

    def test_shorten_session_intent(self):
        coach = ConversationalCoach()
        result = coach.process_message("I only have ten minutes to practice today")
        assert result["action"] == "SHORTEN_SESSION"

    def test_score_explanation(self):
        coach = ConversationalCoach()
        result = coach.process_message(
            "Why is my score low?",
            context={
                "current_pose_name": "Virabhadrasana II",
                "current_score": 68.0,
                "joint_results": [
                    {"joint_name": "Front Knee Angle", "user_angle": 130.0, "target_angle": 90.0, "status": "Needs Adjustment"}
                ],
            },
        )
        assert result["action"] in {"EXPLAIN_SCORE", "EXPLAIN_TECHNIQUE"}
        assert "front knee" in result["response"].lower()


class TestCoachAPIEndpoints:
    """Verifies web endpoints using Flask test client."""

    @pytest.fixture
    def client(self):
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_user_preferences_get_and_post(self, client):
        # Update preferences
        resp = client.post(
            "/api/user/preferences",
            json={
                "user_id": 1,
                "goal": "Flexibility",
                "level": "Intermediate",
                "duration_minutes": 25,
                "focus_area": "Hips",
                "voice_enabled": 1,
                "voice_speed": 1.0,
                "onboarding_completed": 1,
            },
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "success"
        assert data["preferences"]["goal"] == "Flexibility"

        # Read back
        get_resp = client.get("/api/user/preferences/1")
        assert get_resp.status_code == 200
        get_data = json.loads(get_resp.data)
        assert get_data["preferences"]["level"] == "Intermediate"

    def test_coach_message_endpoint(self, client):
        resp = client.post(
            "/api/coach/message",
            json={
                "user_id": 1,
                "message": "My knee hurts during this stretch",
                "context": {"current_pose_name": "Warrior II"},
            },
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "success"
        assert data["coach"]["safety_alert"] is True
        assert data["coach"]["action"] == "PAUSE_AND_REST"

    def test_session_start_and_complete(self, client):
        start_resp = client.post(
            "/api/session/start",
            json={
                "user_id": 1,
                "duration": 20,
                "goal": "Mobility",
                "level": "Beginner",
            },
        )
        assert start_resp.status_code == 200
        start_data = json.loads(start_resp.data)
        assert "session_plan" in start_data
        session_id = start_data["session_id"]
        exercises = start_data["session_plan"]["exercises"]
        assert len(exercises) >= 5

        # Complete session
        complete_resp = client.post(
            "/api/session/complete",
            json={
                "user_id": 1,
                "session_plan_id": session_id,
                "total_duration_seconds": 1200,
                "average_accuracy": 91.5,
                "completed_exercises": len(exercises),
                "total_exercises": len(exercises),
                "program_level": "Beginner",
                "best_pose": "Tadasana",
                "weakest_joint": "Right Knee",
            },
        )
        assert complete_resp.status_code == 200
        comp_data = json.loads(complete_resp.data)
        assert comp_data["status"] == "success"
        assert comp_data["summary"]["completed_exercises"] == len(exercises)
