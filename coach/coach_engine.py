"""
Coach Engine for KI.AI — Personal AI Yoga Teacher.
Orchestrates real-time feedback, throttled voice coaching, intelligent hold validation,
and seamless exercise state progression.
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple
from coach.state_machine import SessionState, SessionStateMachine
from voice.voice_manager import Priority, get_voice_manager

logger = logging.getLogger(__name__)


class CoachEngine:
    """Intelligent yoga instructor evaluation and speech orchestrator."""

    def __init__(self, voice_cooldown_seconds: float = 4.0):
        self.state_machine = SessionStateMachine()
        self.voice_manager = get_voice_manager()
        self.voice_cooldown_seconds = voice_cooldown_seconds
        self.last_spoken_time = 0.0
        self.last_spoken_text = ""
        self.current_exercise: Optional[Dict[str, Any]] = None
        self.stability_frames_count = 0
        self.consecutive_invalid_frames = 0

    def load_exercise(self, exercise: Dict[str, Any]):
        """Initializes state machine for a new roadmap exercise."""
        self.current_exercise = exercise
        hold_target = float(exercise.get("hold_seconds", 20))
        self.state_machine.set_target_hold(hold_target)
        self.state_machine.reset_hold_timer()
        self.stability_frames_count = 0
        self.consecutive_invalid_frames = 0
        
        # Transition to preparing/detecting
        if self.state_machine.current_state in {SessionState.IDLE, SessionState.INTRO, SessionState.TRANSITION, SessionState.NEXT_POSE}:
            self.state_machine.transition_to(SessionState.PREPARING, reason=f"Loaded exercise: {exercise.get('name')}")
        self.voice_manager.on_pose_changed(exercise.get("name"))

    def evaluate_frame(
        self,
        detected_pose_name: str,
        match_score: float,
        posture_eval: Dict[str, Any],
        is_body_visible: bool = True,
        dt: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates one frame of computer vision landmarks against the expected exercise.
        
        Returns:
            Dictionary with current state, accuracy score, hold timer progress,
            visual status, and debounced voice coaching cue.
        """
        expected_name = (self.current_exercise.get("name") if self.current_exercise else "Yoga Pose").strip().lower()
        detected_clean = (detected_pose_name or "").strip().lower()

        overall_score = float(posture_eval.get("overall_score", 0.0))
        is_aligned = overall_score >= 78.0
        pose_matched = (expected_name in detected_clean) or (detected_clean in expected_name) or ("step" in expected_name and "surya" in detected_clean)

        speech_cue: Optional[str] = None
        curr_state = self.state_machine.current_state

        # Check body visibility
        if not is_body_visible:
            speech_cue = self._debounce_speech(
                "Please step back so your full body is visible to the camera.",
                event_key="body_not_visible",
                priority=Priority.NORMAL,
            )
            return {
                "state": curr_state.value,
                "score": 0.0,
                "is_aligned": False,
                "pose_matched": False,
                "hold_seconds": self.state_machine.current_hold_seconds,
                "target_seconds": self.state_machine.target_hold_seconds,
                "speech_cue": speech_cue,
                "status_label": "Body Not Fully Visible",
                "status_code": "NOT_VISIBLE",
            }

        # 1. State: PREPARING -> DETECTING
        if curr_state == SessionState.PREPARING:
            self.state_machine.transition_to(SessionState.DETECTING, reason="Camera feed active")
            speech_cue = self._debounce_speech(
                f"Let's move into {self.current_exercise.get('name', 'posture')}.",
                event_key=f"intro:{expected_name}",
                priority=Priority.NORMAL,
            )

        # 2. Check if user is in expected pose
        curr_state = self.state_machine.current_state
        if curr_state in {SessionState.DETECTING, SessionState.CORRECTING}:
            if not pose_matched and match_score > 40.0:
                self.state_machine.transition_to(SessionState.CORRECTING, reason="Wrong pose performed")
                speech_cue = self._debounce_speech(
                    f"That looks like {detected_pose_name}. Let's get into {self.current_exercise.get('name')}.",
                    event_key=f"wrong_pose:{detected_clean}",
                    priority=Priority.HIGH,
                )
                return {
                    "state": self.state_machine.current_state.value,
                    "score": round(overall_score, 1),
                    "is_aligned": False,
                    "pose_matched": False,
                    "hold_seconds": self.state_machine.current_hold_seconds,
                    "target_seconds": self.state_machine.target_hold_seconds,
                    "speech_cue": speech_cue,
                    "status_label": f"Expected: {self.current_exercise.get('name')}",
                    "status_code": "WRONG_POSE",
                }
            elif pose_matched and is_aligned:
                self.stability_frames_count += 1
                if self.stability_frames_count >= 3:
                    self.state_machine.transition_to(SessionState.HOLDING, reason="Pose verified and aligned")
                    speech_cue = self._debounce_speech(
                        "Good alignment. Hold steady.",
                        event_key=f"hold_started:{expected_name}",
                        priority=Priority.LOW,
                    )
            else:
                primary_feed = posture_eval.get("primary_feedback") or "Adjust your posture."
                speech_cue = self._debounce_speech(
                    primary_feed,
                    event_key=f"correction:{expected_name}:{primary_feed[:18]}",
                    priority=Priority.HIGH,
                )

        # 3. State: HOLDING / PAUSED
        curr_state = self.state_machine.current_state
        timer_result = self.state_machine.tick_hold_timer(is_valid_posture=(pose_matched and is_aligned), dt=dt)
        
        if timer_result.get("completed"):
            speech_cue = self._debounce_speech(
                "Hold complete. Outstanding work!",
                force=True,
                event_key=f"completed:{expected_name}",
                priority=Priority.NORMAL,
            )
            return {
                "state": self.state_machine.current_state.value,
                "score": round(overall_score, 1),
                "is_aligned": True,
                "pose_matched": True,
                "hold_seconds": self.state_machine.current_hold_seconds,
                "target_seconds": self.state_machine.target_hold_seconds,
                "speech_cue": speech_cue,
                "status_label": "Pose Completed! 🎉",
                "status_code": "COMPLETED",
            }

        # Handle speech cues during hold
        remaining = self.state_machine.target_hold_seconds - self.state_machine.current_hold_seconds
        if timer_result.get("status") == "HOLD_PAUSED":
            primary_feed = posture_eval.get("primary_feedback") or "Hold paused. Correct your posture."
            speech_cue = self._debounce_speech(
                primary_feed,
                event_key=f"hold_paused:{expected_name}",
                priority=Priority.HIGH,
            )
        elif timer_result.get("status") == "HOLD_RESUMED":
            speech_cue = self._debounce_speech(
                "Alignment restored. Timer resumed.",
                event_key=f"hold_resumed:{expected_name}",
                priority=Priority.NORMAL,
            )
        elif 2.8 <= remaining <= 3.2:
            speech_cue = self._debounce_speech(
                "Three seconds remaining.",
                event_key=f"countdown_3s:{expected_name}",
                priority=Priority.LOW,
            )
        elif not is_aligned and timer_result.get("status") == "HOLD_PAUSED_AWAITING_CORRECTION":
            primary_feed = posture_eval.get("primary_feedback") or "Adjust alignment."
            speech_cue = self._debounce_speech(
                primary_feed,
                event_key=f"correction:{expected_name}:{primary_feed[:18]}",
                priority=Priority.HIGH,
            )

        return {
            "state": self.state_machine.current_state.value,
            "score": round(overall_score, 1),
            "is_aligned": is_aligned,
            "pose_matched": pose_matched,
            "hold_seconds": self.state_machine.current_hold_seconds,
            "target_seconds": self.state_machine.target_hold_seconds,
            "speech_cue": speech_cue,
            "status_label": "Holding Posture" if timer_result.get("status") == "HOLD_TICKING" else ("Paused — Adjust" if timer_result.get("status") in {"HOLD_PAUSED", "HOLD_PAUSED_AWAITING_CORRECTION"} else "Detecting Pose"),
            "status_code": timer_result.get("status"),
        }

    def _debounce_speech(
        self,
        text: str,
        force: bool = False,
        event_key: str = "",
        priority: Priority = Priority.NORMAL,
    ) -> Optional[str]:
        """Throttles and deduplicates verbal voice cues through centralized VoiceManager."""
        if not text:
            return None
        
        pose_name = self.current_exercise.get("name") if self.current_exercise else None
        key = event_key or f"coach:{pose_name or 'gen'}:{text[:20]}"
        prio = Priority.CRITICAL if force else priority
        
        accepted = self.voice_manager.speak(
            text=text,
            priority=prio,
            event_key=key,
            pose_id=pose_name,
            interruptible=not force,
        )
        if accepted:
            self.last_spoken_time = time.time()
            self.last_spoken_text = text
            return text
        return None
