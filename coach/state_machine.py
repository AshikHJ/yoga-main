"""
Session State Machine for KI.AI — AI Yoga Teacher.
Implements the explicit state lifecycle:
IDLE -> INTRO -> BREATHING -> PREPARING -> DETECTING -> CORRECTING -> READY -> HOLDING -> PAUSED -> COMPLETING_POSE -> TRANSITION -> NEXT_POSE -> SESSION_COMPLETE (and ERROR).
"""

import time
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    IDLE = "IDLE"
    INTRO = "INTRO"
    BREATHING = "BREATHING"
    PREPARING = "PREPARING"
    DETECTING = "DETECTING"
    CORRECTING = "CORRECTING"
    READY = "READY"
    HOLDING = "HOLDING"
    PAUSED = "PAUSED"
    COMPLETING_POSE = "COMPLETING_POSE"
    TRANSITION = "TRANSITION"
    NEXT_POSE = "NEXT_POSE"
    SESSION_COMPLETE = "SESSION_COMPLETE"
    ERROR = "ERROR"


class TimerTickResult(dict):
    """Holds timer evaluation result with dict indexing and tuple unpacking support."""
    def __iter__(self):
        yield self.get("completed", False)
        state_val = self.get("state", "idle")
        yield SessionState(state_val) if isinstance(state_val, str) else state_val


class SessionStateMachine:
    """Manages practice session lifecycle, timers, and valid state transitions."""

    VALID_TRANSITIONS: Dict[SessionState, Set[SessionState]] = {
        SessionState.IDLE: {SessionState.INTRO, SessionState.BREATHING, SessionState.PREPARING, SessionState.ERROR},
        SessionState.INTRO: {SessionState.BREATHING, SessionState.PREPARING, SessionState.IDLE, SessionState.ERROR},
        SessionState.BREATHING: {SessionState.PREPARING, SessionState.DETECTING, SessionState.IDLE, SessionState.ERROR},
        SessionState.PREPARING: {SessionState.DETECTING, SessionState.IDLE, SessionState.ERROR},
        SessionState.DETECTING: {SessionState.CORRECTING, SessionState.READY, SessionState.HOLDING, SessionState.IDLE, SessionState.ERROR},
        SessionState.CORRECTING: {SessionState.DETECTING, SessionState.READY, SessionState.HOLDING, SessionState.PAUSED, SessionState.IDLE, SessionState.ERROR},
        SessionState.READY: {SessionState.HOLDING, SessionState.CORRECTING, SessionState.DETECTING, SessionState.IDLE, SessionState.ERROR},
        SessionState.HOLDING: {SessionState.PAUSED, SessionState.COMPLETING_POSE, SessionState.CORRECTING, SessionState.IDLE, SessionState.ERROR},
        SessionState.PAUSED: {SessionState.HOLDING, SessionState.CORRECTING, SessionState.DETECTING, SessionState.IDLE, SessionState.ERROR},
        SessionState.COMPLETING_POSE: {SessionState.TRANSITION, SessionState.NEXT_POSE, SessionState.SESSION_COMPLETE, SessionState.IDLE, SessionState.ERROR},
        SessionState.TRANSITION: {SessionState.NEXT_POSE, SessionState.PREPARING, SessionState.DETECTING, SessionState.SESSION_COMPLETE, SessionState.IDLE, SessionState.ERROR},
        SessionState.NEXT_POSE: {SessionState.PREPARING, SessionState.DETECTING, SessionState.BREATHING, SessionState.SESSION_COMPLETE, SessionState.IDLE, SessionState.ERROR},
        SessionState.SESSION_COMPLETE: {SessionState.IDLE, SessionState.INTRO},
        SessionState.ERROR: {SessionState.IDLE, SessionState.PREPARING, SessionState.INTRO},
    }

    def __init__(self, initial_state: SessionState = SessionState.IDLE):
        self._state = initial_state
        self._state_start_time = time.time()
        self._current_hold_seconds = 0.0
        self._target_hold_seconds = 20.0
        self._last_tick_time = time.time()
        self._history: List[Dict[str, Any]] = []
        self._payload: Dict[str, Any] = {}

    @property
    def current_state(self) -> SessionState:
        return self._state

    @property
    def current_hold_seconds(self) -> float:
        return round(self._current_hold_seconds, 1)

    @property
    def target_hold_seconds(self) -> float:
        return self._target_hold_seconds

    def set_target_hold(self, seconds: float):
        self._target_hold_seconds = max(5.0, float(seconds))

    def reset_hold_timer(self):
        self._current_hold_seconds = 0.0
        self._last_tick_time = time.time()

    def can_transition_to(self, new_state: SessionState) -> bool:
        """Checks if transition from current state to new_state is permissible."""
        allowed = self.VALID_TRANSITIONS.get(self._state, set())
        return new_state in allowed

    def transition_to(self, new_state: SessionState, reason: str = "", payload: Optional[Dict[str, Any]] = None) -> bool:
        """Performs state transition if valid, logs transition and updates timestamps."""
        if not self.can_transition_to(new_state):
            logger.warning(f"Invalid state transition attempted: {self._state.value} -> {new_state.value} ({reason})")
            return False

        now = time.time()
        old_state = self._state
        self._history.append({
            "from_state": old_state.value,
            "to_state": new_state.value,
            "timestamp": now,
            "duration_in_prev_state": now - self._state_start_time,
            "reason": reason,
        })

        self._state = new_state
        self._state_start_time = now
        self._last_tick_time = now
        if payload is not None:
            self._payload.update(payload)

        logger.debug(f"State transition: {old_state.value} -> {new_state.value} | Reason: {reason}")
        return True

    def is_hold_completed(self) -> bool:
        """Checks if target hold time has elapsed."""
        return self._current_hold_seconds >= self._target_hold_seconds or self._state == SessionState.COMPLETING_POSE

    def tick_hold_timer(
        self,
        is_valid_posture: Optional[bool] = None,
        dt: Optional[float] = None,
        is_valid_frame: Optional[bool] = None,
        delta_seconds: Optional[float] = None,
    ) -> TimerTickResult:
        """
        Intelligent Hold Timer:
        ONLY advances elapsed hold time if in HOLDING state and posture is valid (score >= threshold).
        Automatically requests PAUSED state if posture degrades, or resumes if in PAUSED state and corrected.
        """
        valid = is_valid_frame if is_valid_frame is not None else (is_valid_posture if is_valid_posture is not None else False)
        now = time.time()
        step_dt = delta_seconds if delta_seconds is not None else (dt if dt is not None else max(0.0, now - self._last_tick_time))
        self._last_tick_time = now

        if self._state in {SessionState.DETECTING, SessionState.READY}:
            if valid:
                self.transition_to(SessionState.HOLDING, reason="Valid posture confirmed")

        if self._state == SessionState.HOLDING:
            if valid:
                self._current_hold_seconds += step_dt
                if self._current_hold_seconds >= self._target_hold_seconds:
                    self.transition_to(SessionState.COMPLETING_POSE, reason="Target hold duration reached")
                    return TimerTickResult({
                        "state": self._state.value,
                        "hold_seconds": self.current_hold_seconds,
                        "target_seconds": self._target_hold_seconds,
                        "completed": True,
                        "status": "HOLD_COMPLETED",
                    })
                return TimerTickResult({
                    "state": self._state.value,
                    "hold_seconds": self.current_hold_seconds,
                    "target_seconds": self._target_hold_seconds,
                    "completed": False,
                    "status": "HOLD_TICKING",
                })
            else:
                # Posture degraded during holding -> PAUSE
                self.transition_to(SessionState.PAUSED, reason="Posture alignment dropped below threshold")
                return TimerTickResult({
                    "state": self._state.value,
                    "hold_seconds": self.current_hold_seconds,
                    "target_seconds": self._target_hold_seconds,
                    "completed": False,
                    "status": "HOLD_PAUSED",
                })

        elif self._state == SessionState.PAUSED:
            if valid:
                # Posture restored -> RESUME HOLDING
                self.transition_to(SessionState.HOLDING, reason="Posture alignment restored to target threshold")
                self._current_hold_seconds += step_dt
                return TimerTickResult({
                    "state": self._state.value,
                    "hold_seconds": self.current_hold_seconds,
                    "target_seconds": self._target_hold_seconds,
                    "completed": False,
                    "status": "HOLD_RESUMED",
                })
            return TimerTickResult({
                "state": self._state.value,
                "hold_seconds": self.current_hold_seconds,
                "target_seconds": self._target_hold_seconds,
                "completed": False,
                "status": "HOLD_PAUSED_AWAITING_CORRECTION",
            })

        return TimerTickResult({
            "state": self._state.value,
            "hold_seconds": self.current_hold_seconds,
            "target_seconds": self._target_hold_seconds,
            "completed": False,
            "status": "TIMER_INACTIVE",
        })

    def get_snapshot(self) -> Dict[str, Any]:
        """Returns full state machine snapshot."""
        return {
            "state": self._state.value,
            "hold_seconds": self.current_hold_seconds,
            "target_seconds": self._target_hold_seconds,
            "progress_ratio": min(1.0, self._current_hold_seconds / max(1.0, self._target_hold_seconds)),
            "time_in_state": time.time() - self._state_start_time,
            "payload": self._payload,
        }
