"""
Unit and regression tests for KI.AI Voice Architecture.
Tests VoiceManager, priority queuing, deduplication, cooldowns,
preemption, state transitions, context pruning, and API routes.
"""

import json
import time
import pytest
from voice.voice_manager import (
    VoiceManager,
    Priority,
    VoiceState,
    CoachingEvent,
    SpeechRequest,
)
from coach.coach_engine import CoachEngine
from web_app import app


class TestVoiceManagerCore:
    """Tests the centralized VoiceManager architecture."""

    def test_initial_state(self):
        vm = VoiceManager()
        assert vm.state == VoiceState.IDLE
        assert vm.is_muted is False
        assert vm.is_stopped is False
        assert vm.get_queue_size() == 0
        assert vm.active_request is None

    def test_single_speech_request(self):
        vm = VoiceManager()
        accepted = vm.speak("Stand tall and align your spine.", priority=Priority.NORMAL, event_key="test_align")
        assert accepted is True
        assert vm.state == VoiceState.SPEAKING
        assert vm.active_request is not None
        assert vm.active_request.text == "Stand tall and align your spine."
        assert vm.active_request.priority == Priority.NORMAL
        assert vm.active_request.event_key == "test_align"

    def test_100_identical_frames_produce_only_one_event_in_cooldown(self):
        """
        Verify that 100 rapid identical frames from camera feed produce
        only 1 spoken event, suppressing the other 99 requests.
        """
        vm = VoiceManager()
        results = []
        for _ in range(100):
            res = vm.speak(
                text="Straighten your left knee slightly.",
                priority=Priority.NORMAL,
                event_key="left_knee_correction",
                pose_id="tadasana"
            )
            results.append(res)

        successful_requests = [r for r in results if r is True]
        assert len(successful_requests) == 1, (
            f"Expected exactly 1 request to succeed out of 100, but {len(successful_requests)} succeeded."
        )

    def test_cooldown_window_resets_after_elapsed_time(self):
        """Verify that after cooldown expires, speech can occur again."""
        vm = VoiceManager()
        vm.event_cooldowns["test_event"] = 0.05

        accepted1 = vm.speak("Lift your chest.", priority=Priority.NORMAL, event_key="test_event")
        assert accepted1 is True

        # Immediate follow-up within cooldown should be blocked
        accepted2 = vm.speak("Lift your chest.", priority=Priority.NORMAL, event_key="test_event")
        assert accepted2 is False

        # Wait for cooldown to expire
        time.sleep(0.06)

        # Finish current speech so engine returns to IDLE
        vm.on_speech_finished()

        accepted3 = vm.speak("Lift your chest again.", priority=Priority.NORMAL, event_key="test_event")
        assert accepted3 is True
        assert vm.active_request.text == "Lift your chest again."

    def test_stop_immediately_cancels_and_clears_queue(self):
        """Verify that calling stop() immediately clears queue and transitions to STOPPED."""
        vm = VoiceManager()
        vm.speak("First instruction", priority=Priority.LOW, event_key="cue_1", interruptible=False)
        vm.speak("Second instruction", priority=Priority.NORMAL, event_key="cue_2")

        assert vm.state in (VoiceState.SPEAKING, VoiceState.QUEUED)
        
        vm.stop()
        assert vm.state == VoiceState.STOPPED
        assert vm.get_queue_size() == 0
        assert vm.active_request is None
        assert vm.is_stopped is True

    def test_resume_after_stop(self):
        """Verify that calling resume() allows speech again."""
        vm = VoiceManager()
        vm.stop()
        assert vm.is_stopped is True

        vm.resume()
        assert vm.is_stopped is False
        assert vm.state == VoiceState.IDLE

        accepted = vm.speak("Welcome back.", priority=Priority.NORMAL, event_key="welcome")
        assert accepted is True

    def test_pose_change_invalidates_obsolete_pose_speech(self):
        """
        Verify that changing pose via set_context() purges queued requests
        intended for the previous pose.
        """
        vm = VoiceManager()
        vm.set_context(session_id="sess_1", pose_id="tadasana")

        # Start speaking a tadasana cue (non-interruptible so it holds state)
        vm.speak("Stand tall in Mountain pose.", priority=Priority.LOW, event_key="cue_tadasana_1", pose_id="tadasana", interruptible=False)
        # Enqueue another tadasana cue
        vm.speak("Relax your shoulders in Mountain pose.", priority=Priority.NORMAL, event_key="cue_tadasana_2", pose_id="tadasana")

        assert vm.get_queue_size() == 1

        # Now change pose to vrikshasana (Tree Pose)
        vm.set_context(session_id="sess_1", pose_id="vrikshasana")

        # The queued tadasana cue should be pruned!
        assert vm.get_queue_size() == 0

    def test_session_complete_clears_queue_and_plays_completion(self):
        """
        Verify that session completion cancels all prior speech and
        enqueues only the session complete message.
        """
        vm = VoiceManager()
        vm.speak("Check your foot placement.", priority=Priority.NORMAL, event_key="pose_check", pose_id="tadasana", interruptible=False)
        vm.speak("Keep breathing.", priority=Priority.LOW, event_key="breathe_cue", pose_id="tadasana")

        vm.on_session_completed()
        assert vm.get_queue_size() == 0
        assert vm.active_request is None

        accepted = vm.speak(
            "Practice complete! Outstanding dedication to your body.",
            priority=Priority.HIGH,
            event_key="session_complete"
        )
        assert accepted is True
        assert "complete" in vm.active_request.text.lower()

    def test_priority_preemption_and_interruption(self):
        """
        Verify that CRITICAL or HIGH priority preempts and interrupts an active
        interruptible speech of lower priority.
        """
        vm = VoiceManager()
        accepted_low = vm.speak(
            "Gently breathe in and out.",
            priority=Priority.LOW,
            event_key="breathe",
            interruptible=True
        )
        assert accepted_low is True
        assert vm.active_request.priority == Priority.LOW

        # Submit a CRITICAL safety alert
        accepted_crit = vm.speak(
            "Safety pause! Stop if you feel sharp pain.",
            priority=Priority.CRITICAL,
            event_key="safety_alert",
            interruptible=False
        )
        assert accepted_crit is True
        # The critical request should have preempted the low priority request
        assert vm.active_request.priority == Priority.CRITICAL
        assert "Safety pause" in vm.active_request.text

    def test_priority_queue_size_capping(self):
        """Verify that queue drops lower priority item when maxQueueSize is exceeded."""
        vm = VoiceManager()
        # Keep engine in SPEAKING state with a non-interruptible request
        vm.speak("Playing main intro.", priority=Priority.HIGH, event_key="intro", interruptible=False)

        # Enqueue 3 items (max queue size is 3)
        vm.speak("Low item 1", priority=Priority.LOW, event_key="low1")
        vm.speak("Normal item 2", priority=Priority.NORMAL, event_key="norm2")
        vm.speak("Normal item 3", priority=Priority.NORMAL, event_key="norm3")

        assert vm.get_queue_size() == 3

        # Add a HIGH priority item. It should displace the LOW priority item!
        success = vm.speak("High priority instruction", priority=Priority.HIGH, event_key="high4")
        assert success is True
        assert vm.get_queue_size() == 3

        # Verify that 'Low item 1' was discarded and 'High priority instruction' is in queue
        queue_texts = [r.text for r in vm.queue]
        assert "Low item 1" not in queue_texts
        assert "High priority instruction" in queue_texts

    def test_mute_suppresses_speech_except_critical(self):
        """Verify that mute suppresses normal speech but allows critical safety alerts."""
        vm = VoiceManager()
        vm.mute()
        assert vm.is_muted is True
        assert vm.state == VoiceState.MUTED

        # Normal speech rejected
        accepted_normal = vm.speak("Lift arms overhead.", priority=Priority.NORMAL, event_key="arms")
        assert accepted_normal is False

        # High speech rejected
        accepted_high = vm.speak("Hold steady.", priority=Priority.HIGH, event_key="hold")
        assert accepted_high is False

        # CRITICAL safety alert allowed
        accepted_crit = vm.speak("Sharp knee pain detected. Stop immediately.", priority=Priority.CRITICAL, event_key="safety")
        assert accepted_crit is True

        # Unmute restores normal speech
        vm.unmute()
        assert vm.is_muted is False
        accepted_after = vm.speak("Resume gentle posture.", priority=Priority.NORMAL, event_key="resume")
        assert accepted_after is True

    def test_interrupt_for_listening(self):
        """Verify user talk/mic interrupt silences TTS and sets LISTENING state."""
        vm = VoiceManager()
        vm.speak("This is an explanation of Tadasana.", priority=Priority.NORMAL, event_key="explain")
        assert vm.state == VoiceState.SPEAKING

        vm.interrupt_for_listening()
        assert vm.state == VoiceState.LISTENING
        assert vm.active_request is None
        assert vm.get_queue_size() == 0


class TestCoachEngineIntegration:
    """Tests CoachEngine integration with VoiceManager."""

    def test_coach_engine_debounces_repeated_evaluation_frames(self):
        engine = CoachEngine(voice_cooldown_seconds=4.0)
        engine.load_exercise({"name": "Tadasana", "hold_seconds": 15})

        # 30 frames of good posture
        voice_events = []
        for _ in range(30):
            res = engine.evaluate_frame(
                detected_pose_name="Tadasana",
                match_score=88.0,
                posture_eval={"is_correct": True, "feedback": "Knees and hips aligned."}
            )
            if res.get("coach_event"):
                voice_events.append(res["coach_event"])

        # Should only emit state transition event at beginning, not on all 30 frames
        assert len(voice_events) <= 2


class TestVoiceAPIEndpoints:
    """Tests the Flask HTTP API endpoints for voice management."""

    @pytest.fixture
    def client(self):
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_voice_status_endpoint(self, client):
        res = client.get("/api/voice/status")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["status"] == "success"
        assert "voice" in data
        assert "state" in data["voice"]
        assert "is_muted" in data["voice"]

    def test_voice_stop_and_resume_endpoint(self, client):
        res_stop = client.post("/api/voice/stop")
        assert res_stop.status_code == 200
        data_stop = json.loads(res_stop.data)
        assert data_stop["status"] == "success"
        assert data_stop["voice"]["state"] == "STOPPED"

        res_resume = client.post("/api/voice/resume")
        assert res_resume.status_code == 200
        data_resume = json.loads(res_resume.data)
        assert data_resume["status"] == "success"
        assert data_resume["voice"]["state"] == "IDLE"

    def test_voice_mute_and_unmute_endpoint(self, client):
        res_mute = client.post("/api/voice/mute")
        assert res_mute.status_code == 200
        data_mute = json.loads(res_mute.data)
        assert data_mute["voice"]["is_muted"] is True

        res_unmute = client.post("/api/voice/unmute")
        assert res_unmute.status_code == 200
        data_unmute = json.loads(res_unmute.data)
        assert data_unmute["voice"]["is_muted"] is False

    def test_voice_interrupt_endpoint(self, client):
        res = client.post("/api/voice/interrupt")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["voice"]["state"] == "LISTENING"

    def test_voice_speak_endpoint_with_deduplication(self, client):
        # Unmute and resume first
        client.post("/api/voice/unmute")
        client.post("/api/voice/resume")

        # First speak request
        payload = {
            "text": "Keep your back straight and breathe.",
            "priority": "normal",
            "event_key": "api_test_cue",
            "pose_id": "tadasana"
        }
        res1 = client.post("/api/voice/speak", json=payload)
        assert res1.status_code == 200
        data1 = json.loads(res1.data)
        assert data1["status"] == "success"

        # Immediate second identical request should be rejected by deduplication/cooldown
        res2 = client.post("/api/voice/speak", json=payload)
        assert res2.status_code == 200
        data2 = json.loads(res2.data)
        assert data2["status"] == "rejected"
