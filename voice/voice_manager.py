"""
KI.AI Centralized Voice Manager.
Orchestrates speech synthesis requests, priority queuing, event deduplication,
cooldown enforcement, cancellation, and thread-safe engine lifecycle.
"""

import heapq
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    """Speech priority levels. Lower integer = higher priority."""
    CRITICAL = 1      # Safety warnings ("Stop movement immediately")
    HIGH = 2          # Major posture corrections ("Reset your position")
    NORMAL = 3        # Pose instructions / transitions ("Move into Vrikshasana")
    LOW = 4           # Encouragement / breathing ("Good stability", "Inhale deeply")


class VoiceState(Enum):
    """Explicit voice controller states."""
    IDLE = "IDLE"
    QUEUED = "QUEUED"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    MUTED = "MUTED"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


class CoachingEvent(Enum):
    """Standardized semantic coaching events."""
    SESSION_STARTED = "SESSION_STARTED"
    BREATHING_START = "BREATHING_START"
    POSE_INSTRUCTION = "POSE_INSTRUCTION"
    WRONG_POSE = "WRONG_POSE"
    POSE_DETECTED = "POSE_DETECTED"
    ALIGNMENT_BAD = "ALIGNMENT_BAD"
    ALIGNMENT_IMPROVED = "ALIGNMENT_IMPROVED"
    ALIGNMENT_GOOD = "ALIGNMENT_GOOD"
    HOLD_STARTED = "HOLD_STARTED"
    HOLD_PAUSED = "HOLD_PAUSED"
    HOLD_RESUMED = "HOLD_RESUMED"
    COUNTDOWN = "COUNTDOWN"
    POSE_COMPLETED = "POSE_COMPLETED"
    TRANSITION = "TRANSITION"
    SESSION_COMPLETED = "SESSION_COMPLETED"
    SAFETY_WARNING = "SAFETY_WARNING"


@dataclass
class SpeechRequest:
    """Structured representation of a single speech utterance request."""
    text: str
    priority: Priority = Priority.NORMAL
    event_key: str = ""
    pose_id: Optional[Any] = None
    session_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    interruptible: bool = True
    expires_after_seconds: float = 6.0

    def is_expired(self, now: Optional[float] = None) -> bool:
        """Checks if this speech request has exceeded its relevancy expiration."""
        current_time = now if now is not None else time.time()
        return (current_time - self.created_at) > self.expires_after_seconds

    def is_valid_for_context(self, current_session_id: Optional[str], current_pose_id: Optional[Any]) -> bool:
        """Verifies if the speech request is still relevant to the active exercise/session."""
        if self.session_id and current_session_id and str(self.session_id) != str(current_session_id):
            return False
        if self.pose_id and current_pose_id and str(self.pose_id) != str(current_pose_id):
            return False
        return True

    def __lt__(self, other: "SpeechRequest") -> bool:
        """Ordering for priority queue: lower priority value first, then earliest created."""
        if self.priority != other.priority:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class VoiceManager:
    """
    Centralized, thread-safe speech controller for KI.AI.
    Enforces cooldowns, deduplication, priority preemption, queue limits,
    obsolete message discarding, and manual stop/mute controls.
    """

    MAX_QUEUE_SIZE: int = 3
    DEFAULT_COOLDOWN: float = 4.0
    CORRECTION_COOLDOWN: float = 4.0
    ENCOURAGEMENT_COOLDOWN: float = 8.0
    POSE_INSTRUCTION_COOLDOWN: float = 10.0

    def __init__(self, backend_tts_enabled: bool = False):
        self.backend_tts_enabled = backend_tts_enabled
        self._state = VoiceState.IDLE
        self._is_muted = False
        self._is_stopped = False
        self._lock = threading.RLock()
        
        # Priority queue storage
        self._queue: List[SpeechRequest] = []
        self._current_request: Optional[SpeechRequest] = None
        
        # Event deduplication cache: event_key -> last_spoken_timestamp
        self._recent_events: Dict[str, float] = {}
        self.event_cooldowns: Dict[str, float] = {}
        
        # Active session context
        self.active_session_id: Optional[str] = None
        self.active_pose_id: Optional[Any] = None
        
        # Audio playback engine state (for offline pyttsx3 if active)
        self._tts_engine = None
        self._tts_worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._speech_event = threading.Event()
        
        # Listeners for frontend sync or telemetry
        self._state_listeners: List[Callable[[VoiceState, Optional[SpeechRequest]], None]] = []

    # ==========================================
    # State & Context Management
    # ==========================================

    @property
    def state(self) -> VoiceState:
        with self._lock:
            return self._state

    @property
    def is_muted(self) -> bool:
        with self._lock:
            return self._is_muted

    @property
    def is_stopped(self) -> bool:
        with self._lock:
            return self._is_stopped

    @property
    def queue_size(self) -> int:
        with self._lock:
            return len(self._queue)

    def get_queue_size(self) -> int:
        return self.queue_size

    @property
    def queue(self) -> List[SpeechRequest]:
        with self._lock:
            return list(self._queue)

    @property
    def active_request(self) -> Optional[SpeechRequest]:
        with self._lock:
            return self._current_request

    def set_context(self, session_id: Optional[str] = None, pose_id: Optional[Any] = None) -> None:
        """Updates active session and exercise context, pruning any now-obsolete queued speech."""
        with self._lock:
            if session_id is not None:
                self.active_session_id = str(session_id)
            if pose_id is not None:
                self.active_pose_id = str(pose_id)
            self._prune_obsolete_requests()

    def on_pose_changed(self, new_pose_id: Any) -> None:
        """Fired when practitioner transitions to a new posture in roadmap."""
        with self._lock:
            old_pose = self.active_pose_id
            self.active_pose_id = str(new_pose_id) if new_pose_id is not None else None
            
            # If current speech was tied to old pose and is interruptible, stop it
            if self._current_request and self._current_request.pose_id:
                if str(self._current_request.pose_id) != str(self.active_pose_id):
                    logger.info(f"Interrupting speech '{self._current_request.text}' due to pose transition")
                    self._stop_current_speech(reason="pose_transition")

            # Prune obsolete messages for old pose
            self._prune_obsolete_requests()

    def on_session_completed(self) -> None:
        """Fired when practice session ends: stops speech, clears all queues."""
        with self._lock:
            self._stop_current_speech(reason="session_complete")
            self._queue.clear()
            self.active_session_id = None
            self.active_pose_id = None
            self._transition_state(VoiceState.IDLE)

    def on_navigation_away(self) -> None:
        """Fired when practitioner leaves Practice Studio (navigates to Home, Library, etc.)."""
        with self._lock:
            self.stop()

    def on_camera_stopped(self) -> None:
        """Fired when webcam is turned off or unmounted."""
        with self._lock:
            self.stop()

    # ==========================================
    # Speech Request Intake & Deduplication
    # ==========================================

    def get_cooldown_for_event(self, event_key: str, priority: Priority) -> float:
        """Returns the appropriate cooldown threshold based on event type."""
        if priority == Priority.CRITICAL:
            return 0.0  # Critical safety alerts NEVER wait on cooldown
        
        if event_key in self.event_cooldowns:
            return self.event_cooldowns[event_key]
        
        lower_key = event_key.lower()
        if "correction" in lower_key or "adjust" in lower_key or "bad" in lower_key:
            return self.CORRECTION_COOLDOWN
        if "good" in lower_key or "encourage" in lower_key or "stable" in lower_key:
            return self.ENCOURAGEMENT_COOLDOWN
        if "instruction" in lower_key or "intro" in lower_key:
            return self.POSE_INSTRUCTION_COOLDOWN
        return self.DEFAULT_COOLDOWN

    def is_event_throttled(self, event_key: str, priority: Priority) -> bool:
        """Checks if the same event condition was already announced within its cooldown period."""
        if not event_key or priority == Priority.CRITICAL:
            return False
            
        now = time.time()
        last_time = self._recent_events.get(event_key, 0.0)
        cooldown = self.get_cooldown_for_event(event_key, priority)
        return (now - last_time) < cooldown

    def speak(
        self,
        text: str,
        priority: Priority = Priority.NORMAL,
        event_key: str = "",
        pose_id: Optional[Any] = None,
        session_id: Optional[str] = None,
        interruptible: bool = True,
        expires_after_seconds: float = 6.0,
    ) -> bool:
        """
        Submits a speech request to the voice engine.
        
        Returns:
            True if accepted and queued/spoken, False if suppressed, muted, stopped, or discarded.
        """
        clean_text = (text or "").strip()
        if not clean_text:
            return False

        with self._lock:
            if self._is_stopped:
                logger.debug(f"Speech suppressed (stopped): {clean_text}")
                return False
            if self._is_muted and priority != Priority.CRITICAL:
                logger.debug(f"Speech suppressed (muted): {clean_text}")
                return False

            # Check event key deduplication & cooldown
            if event_key and self.is_event_throttled(event_key, priority):
                logger.debug(f"Duplicate speech event suppressed by cooldown '{event_key}': {clean_text}")
                return False

            now = time.time()
            req = SpeechRequest(
                text=clean_text,
                priority=priority,
                event_key=event_key,
                pose_id=str(pose_id) if pose_id is not None else self.active_pose_id,
                session_id=str(session_id) if session_id is not None else self.active_session_id,
                created_at=now,
                interruptible=interruptible,
                expires_after_seconds=expires_after_seconds,
            )

            # Record event timestamp for cooldown
            if event_key:
                self._recent_events[event_key] = now

            # Priority Preemption:
            # If CRITICAL or HIGH arrives while currently speaking a lower-priority message
            if priority in {Priority.CRITICAL, Priority.HIGH}:
                if self._current_request and self._current_request.priority > priority and self._current_request.interruptible:
                    logger.info(f"Preempting current speech '{self._current_request.text}' for higher priority '{clean_text}'")
                    self._stop_current_speech(reason="priority_preemption")
                    # Clear out lower priority messages from queue
                    self._queue = [q for q in self._queue if q.priority <= priority]
                    self._state = VoiceState.IDLE

            # Add to priority queue
            self._enqueue_request(req)
            self._dispatch_next()
            return True

    def _enqueue_request(self, request: SpeechRequest) -> None:
        """Adds request to queue, enforcing MAX_QUEUE_SIZE by dropping lowest priority/oldest."""
        heapq.heappush(self._queue, request)
        if len(self._queue) > self.MAX_QUEUE_SIZE:
            # Reconstruct queue keeping highest priority items
            sorted_items = sorted(self._queue)
            dropped = sorted_items.pop()
            self._queue = sorted_items
            heapq.heapify(self._queue)
            logger.debug(f"Queue size exceeded limit ({self.MAX_QUEUE_SIZE}). Dropped: '{dropped.text}'")

    def _prune_obsolete_requests(self) -> None:
        """Removes expired or context-invalid speech requests from queue."""
        now = time.time()
        valid_items = []
        for req in self._queue:
            if req.is_expired(now):
                logger.debug(f"Pruning expired speech: '{req.text}'")
                continue
            if not req.is_valid_for_context(self.active_session_id, self.active_pose_id):
                logger.debug(f"Pruning context-invalid speech: '{req.text}'")
                continue
            valid_items.append(req)
        
        self._queue = valid_items
        heapq.heapify(self._queue)

    def _dispatch_next(self) -> None:
        """Pulls the next highest priority request and dispatches execution."""
        if self._state == VoiceState.SPEAKING:
            return

        self._prune_obsolete_requests()
        if not self._queue:
            self._transition_state(VoiceState.IDLE)
            return

        next_req = heapq.heappop(self._queue)
        self._current_request = next_req
        self._transition_state(VoiceState.SPEAKING, next_req)

        # If backend pyttsx3 is active, notify backend worker
        if self.backend_tts_enabled:
            self._speech_event.set()

    # ==========================================
    # Stop & Interruption Controls
    # ==========================================

    def stop(self) -> None:
        """
        Manually and immediately stops speech.
        Cancels active speech, flushes queue, sets state to STOPPED.
        """
        with self._lock:
            logger.info("VoiceManager.stop() invoked: stopping speech and clearing queue")
            self._is_stopped = True
            self._stop_current_speech(reason="manual_stop")
            self._queue.clear()
            self._transition_state(VoiceState.STOPPED)

    def resume(self) -> None:
        """Resets stopped flag, allowing speech requests to resume."""
        with self._lock:
            self._is_stopped = False
            self._transition_state(VoiceState.IDLE)

    def mute(self) -> None:
        """Mutes voice output and flushes pending speech requests."""
        with self._lock:
            self._is_muted = True
            self._stop_current_speech(reason="mute")
            self._queue.clear()
            self._transition_state(VoiceState.MUTED)

    def unmute(self) -> None:
        """Unmutes voice output."""
        with self._lock:
            self._is_muted = False
            self._transition_state(VoiceState.IDLE)

    def toggle_mute(self) -> bool:
        """Toggles muted state and returns new value."""
        with self._lock:
            if self._is_muted:
                self.unmute()
            else:
                self.mute()
            return self._is_muted

    def interrupt_for_listening(self) -> None:
        """
        Called when user activates microphone to speak to KI.AI.
        Immediately silences any active TTS and sets state to LISTENING.
        """
        with self._lock:
            logger.info("VoiceManager.interrupt_for_listening() invoked: silencing TTS for user query")
            self._stop_current_speech(reason="microphone_interrupt")
            self._queue.clear()
            self._transition_state(VoiceState.LISTENING)

    def on_speech_finished(self, request: Optional[SpeechRequest] = None) -> None:
        """Invoked by speech engine callback when an utterance finishes playing."""
        with self._lock:
            if self._current_request and (request is None or request == self._current_request):
                self._current_request = None
            if self._state == VoiceState.SPEAKING:
                self._transition_state(VoiceState.IDLE)
            self._dispatch_next()

    def _stop_current_speech(self, reason: str = "") -> None:
        """Internal worker to interrupt active speech audio."""
        if self.backend_tts_enabled and self._tts_engine:
            try:
                self._tts_engine.stop()
            except Exception as e:
                logger.debug(f"Error stopping backend TTS engine: {e}")
        self._current_request = None

    def _transition_state(self, new_state: VoiceState, req: Optional[SpeechRequest] = None) -> None:
        """Transitions state and triggers registered listeners."""
        self._state = new_state
        for listener in self._state_listeners:
            try:
                listener(new_state, req)
            except Exception as ex:
                logger.debug(f"Error in VoiceManager listener: {ex}")

    def add_listener(self, callback: Callable[[VoiceState, Optional[SpeechRequest]], None]) -> None:
        """Registers a state change listener."""
        with self._lock:
            self._state_listeners.append(callback)

    def get_status(self) -> Dict[str, Any]:
        """Returns JSON snapshot of current voice controller state."""
        with self._lock:
            return {
                "state": self._state.value,
                "is_muted": self._is_muted,
                "is_stopped": self._is_stopped,
                "queue_size": len(self._queue),
                "current_text": self._current_request.text if self._current_request else None,
                "active_pose_id": self.active_pose_id,
                "active_session_id": self.active_session_id,
            }


# Global singleton instance
_global_voice_manager: Optional[VoiceManager] = None
_instance_lock = threading.Lock()


def get_voice_manager() -> VoiceManager:
    """Returns the shared VoiceManager singleton instance."""
    global _global_voice_manager
    with _instance_lock:
        if _global_voice_manager is None:
            _global_voice_manager = VoiceManager()
        return _global_voice_manager
