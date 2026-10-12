"""
Practice Session Controller for KI.AI — Real-Time AI Yoga Teacher.
Coordinates multi-asana routines, hold timer tracking, automatic sequence transitions,
failure handling, duplicate event deduplication, and progress persistence.
"""

from enum import Enum
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SessionLifecycleState(str, Enum):
    IDLE = "IDLE"
    PREPARING = "PREPARING"
    DETECTING = "DETECTING"
    HOLDING = "HOLDING"
    PAUSED = "PAUSED"
    TRANSITIONING = "TRANSITIONING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class AsanaStep:
    """Represents a single posture within an active practice sequence."""

    def __init__(
        self,
        index: int,
        pose_id: int,
        name: str,
        sanskrit_name: str = "",
        target_hold_seconds: float = 20.0,
        breathing_cue: str = "",
        instructions: Optional[List[str]] = None,
    ):
        self.index = index
        self.pose_id = int(pose_id)
        self.name = str(name).strip()
        self.sanskrit_name = str(sanskrit_name).strip()
        self.target_hold_seconds = max(1.0, float(target_hold_seconds))
        self.hold_seconds = 0.0
        self.breathing_cue = breathing_cue or "Maintain steady diaphragmatic breath."
        self.instructions = instructions or []
        self.completed = False
        self.skipped = False
        self.best_score = 0.0
        self.last_score = 0.0
        self.samples_count = 0
        self.total_score_sum = 0.0
        self.halfway_announced = False

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, round(self.target_hold_seconds - self.hold_seconds, 1))

    @property
    def avg_score(self) -> float:
        if self.samples_count <= 0:
            return 0.0
        return round(self.total_score_sum / self.samples_count, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "id": self.pose_id,
            "pose_id": self.pose_id,
            "target_pose_id": self.pose_id,
            "name": self.name,
            "sanskrit_name": self.sanskrit_name,
            "target_seconds": self.target_hold_seconds,
            "target_hold_seconds": self.target_hold_seconds,
            "hold_seconds": round(self.hold_seconds, 1),
            "remaining_seconds": self.remaining_seconds,
            "completed": self.completed,
            "skipped": self.skipped,
            "best_score": round(self.best_score, 1),
            "avg_score": self.avg_score,
            "breathing_cue": self.breathing_cue,
        }


class PracticeSessionController:
    """
    Stateful practice controller governing sequence progression, hold duration countdown,
    event deduplication, camera fault tolerance, and browser reload synchronization.
    """

    TRANSITION_COOLDOWN_SECONDS: float = 2.0  # Guard against duplicate transition events

    def __init__(
        self,
        session_id: str,
        user_id: int = 1,
        title: str = "AI Yoga Practice",
        level: str = "Beginner",
        goal: str = "General Fitness",
        exercises: Optional[List[Dict[str, Any]]] = None,
        db=None,
    ):
        self.session_id = str(session_id)
        self.user_id = int(user_id)
        self.title = str(title)
        self.level = str(level)
        self.goal = str(goal)
        self.db = db
        self.created_at = time.time()

        self.steps: List[AsanaStep] = []
        if exercises:
            for idx, ex in enumerate(exercises):
                p_id = ex.get("target_pose_id") or ex.get("pose_id") or ex.get("id") or (idx + 1)
                name = ex.get("name") or f"Asana {idx + 1}"
                sanskrit = ex.get("sanskrit_name") or ""
                dur = ex.get("hold_seconds") or ex.get("target_hold_seconds") or ex.get("duration") or 20.0
                cue = ex.get("breathing_cue") or ""
                instr = ex.get("instructions") or []
                self.steps.append(
                    AsanaStep(
                        index=idx,
                        pose_id=int(p_id),
                        name=name,
                        sanskrit_name=sanskrit,
                        target_hold_seconds=float(dur),
                        breathing_cue=cue,
                        instructions=instr,
                    )
                )

        self.current_index = 0
        self.state = SessionLifecycleState.PREPARING if self.steps else SessionLifecycleState.IDLE
        self.is_paused = False
        self.pause_reason = ""
        self.last_tick_time = time.monotonic()
        self.last_transition_time = 0.0

        # Hardware & network state tracking
        self.camera_active = True
        self.tracking_error_count = 0
        self.last_speech_cue: Optional[str] = None

    @property
    def current_step(self) -> Optional[AsanaStep]:
        if 0 <= self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    @property
    def next_step(self) -> Optional[AsanaStep]:
        next_idx = self.current_index + 1
        if 0 <= next_idx < len(self.steps):
            return self.steps[next_idx]
        return None

    def tick_evaluation(
        self,
        is_valid_hold: bool,
        score: float,
        dt: Optional[float] = None,
        pose_matched: bool = True,
        is_body_visible: bool = True,
    ) -> Dict[str, Any]:
        """
        Evaluates one landmark frame against current asana step.
        Advances hold timer strictly on verified form, triggers automated sequence
        transition upon duration completion, and prevents duplicate transitions.

        Returns:
            Snapshot dict with current/next asana details, remaining seconds,
            and any newly fired speech cue.
        """
        now = time.monotonic()
        speech_cue: Optional[str] = None
        transition_triggered = False

        if not self.steps:
            self.state = SessionLifecycleState.IDLE
            return self.get_snapshot()

        if self.state == SessionLifecycleState.COMPLETED:
            return self.get_snapshot()

        step = self.current_step
        if not step:
            self.state = SessionLifecycleState.COMPLETED
            return self.get_snapshot()

        # Step DT calculation with monotonic clamp
        if dt is not None:
            step_dt = max(0.0, float(dt))
        else:
            step_dt = min(max(0.0, now - self.last_tick_time), 1.0)
        self.last_tick_time = now

        # Guard against duplicate transition execution if within cooldown
        in_cooldown = (now - self.last_transition_time) < self.TRANSITION_COOLDOWN_SECONDS

        # Handle hardware or tracking failure
        if not self.camera_active:
            self.state = SessionLifecycleState.PAUSED
            self.pause_reason = "Camera video feed interrupted"
            return self.get_snapshot()

        if not is_body_visible:
            self.state = SessionLifecycleState.PAUSED
            self.pause_reason = "Step back so your full body is visible to the camera"
            return self.get_snapshot()

        if self.is_paused:
            return self.get_snapshot()

        # Record genuine scoring sample
        if score > 0:
            step.samples_count += 1
            step.total_score_sum += score
            step.last_score = score
            if score > step.best_score:
                step.best_score = score

        # Intelligent Hold Progression
        if is_valid_hold and pose_matched and not in_cooldown:
            self.state = SessionLifecycleState.HOLDING
            self.pause_reason = ""
            step.hold_seconds += step_dt

            # Halfway hold milestone event
            halfway_target = step.target_hold_seconds / 2.0
            if not step.halfway_announced and step.hold_seconds >= halfway_target:
                step.halfway_announced = True
                speech_cue = "Halfway there. Maintain steady breath."

            # Asana Hold Completion & Automated Transition
            if step.hold_seconds >= step.target_hold_seconds:
                step.completed = True
                step.hold_seconds = step.target_hold_seconds
                self.last_transition_time = now
                transition_triggered = True

                if self.current_index + 1 < len(self.steps):
                    # Automatic advance to next asana
                    self.current_index += 1
                    next_s = self.current_step
                    self.state = SessionLifecycleState.TRANSITIONING
                    speech_cue = f"Hold complete! Excellent work. Moving to {next_s.name}."
                    logger.info(
                        f"Session {self.session_id}: Transitioned to asana {self.current_index} ({next_s.name})"
                    )
                else:
                    # All asanas in sequence completed
                    self.state = SessionLifecycleState.COMPLETED
                    speech_cue = "Practice session complete! Outstanding dedication. Namaste."
                    logger.info(f"Session {self.session_id}: All {len(self.steps)} asanas completed successfully.")
        else:
            # Posture misalignment or paused hold
            if self.state == SessionLifecycleState.HOLDING:
                self.state = SessionLifecycleState.PAUSED
                if not pose_matched:
                    self.pause_reason = f"Adjust into {step.name} to continue timer"
                else:
                    self.pause_reason = "Alignment dropped below threshold; correct to resume"
            elif self.state not in {SessionLifecycleState.TRANSITIONING, SessionLifecycleState.COMPLETED}:
                self.state = SessionLifecycleState.DETECTING

        snapshot = self.get_snapshot()
        if speech_cue:
            snapshot["speech_cue"] = speech_cue
            self.last_speech_cue = speech_cue
        return snapshot

    def skip_current_asana(self) -> Dict[str, Any]:
        """Manually skips current posture and advances sequence."""
        step = self.current_step
        if not step or self.state == SessionLifecycleState.COMPLETED:
            return self.get_snapshot()

        step.skipped = True
        logger.info(f"Session {self.session_id}: Skipped asana {self.current_index} ({step.name})")

        if self.current_index + 1 < len(self.steps):
            self.current_index += 1
            self.state = SessionLifecycleState.PREPARING
            next_name = self.current_step.name
            cue = f"Skipping {step.name}. Next is {next_name}."
        else:
            self.state = SessionLifecycleState.COMPLETED
            cue = "All asanas completed. Session finished."

        snapshot = self.get_snapshot()
        snapshot["speech_cue"] = cue
        return snapshot

    def pause_session(self, reason: str = "Manual pause") -> Dict[str, Any]:
        """Pauses practice countdown and locks state."""
        self.is_paused = True
        self.pause_reason = reason
        self.state = SessionLifecycleState.PAUSED
        return self.get_snapshot()

    def resume_session(self) -> Dict[str, Any]:
        """Resumes active practice from current asana."""
        self.is_paused = False
        self.pause_reason = ""
        self.last_tick_time = time.monotonic()
        self.state = SessionLifecycleState.DETECTING
        return self.get_snapshot()

    def handle_camera_error(self, error_message: str = ""):
        """Safely pauses hold countdown without corrupting session progress."""
        self.camera_active = False
        self.pause_session(reason=f"Camera error: {error_message or 'Video feed offline'}")

    def handle_camera_restored(self):
        """Restores camera readiness."""
        self.camera_active = True
        if self.is_paused and "Camera error" in self.pause_reason:
            self.resume_session()

    def get_summary(self) -> Dict[str, Any]:
        """Computes authoritative session performance summary across all sequence steps."""
        completed_count = sum(1 for s in self.steps if s.completed)
        skipped_count = sum(1 for s in self.steps if s.skipped)
        total_count = len(self.steps)

        scored_steps = [s for s in self.steps if s.samples_count > 0]
        avg_score = (
            round(sum(s.avg_score for s in scored_steps) / len(scored_steps), 1)
            if scored_steps
            else 0.0
        )

        best_step = None
        best_val = -1.0
        for s in self.steps:
            if s.best_score > best_val:
                best_val = s.best_score
                best_step = s

        total_hold_time = sum(s.hold_seconds for s in self.steps)

        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "title": self.title,
            "level": self.level,
            "goal": self.goal,
            "total_exercises": total_count,
            "completed_exercises": completed_count,
            "skipped_exercises": skipped_count,
            "total_hold_seconds": round(total_hold_time, 1),
            "average_accuracy": avg_score,
            "best_pose": best_step.name if best_step else "",
            "best_score": round(best_val, 1) if best_val >= 0 else 0.0,
            "is_completed": self.state == SessionLifecycleState.COMPLETED,
        }

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Returns full, consistent API contract snapshot of the active session.
        Guarantees current pose, remaining time, next pose, and session state.
        """
        curr = self.current_step.to_dict() if self.current_step else None
        nxt = self.next_step.to_dict() if self.next_step else None

        completed_count = sum(1 for s in self.steps if s.completed)
        total_count = len(self.steps)
        progress_pct = round((completed_count / max(1, total_count)) * 100, 1)

        summary_data = self.get_summary() if self.state == SessionLifecycleState.COMPLETED else None

        return {
            "session_id": self.session_id,
            "session_state": self.state.value,
            "is_paused": self.is_paused,
            "pause_reason": self.pause_reason,
            "camera_active": self.camera_active,
            "current_pose": curr,
            "next_pose": nxt,
            "sequence_progress": {
                "current_index": self.current_index,
                "total_poses": total_count,
                "completed_poses": completed_count,
                "percent_complete": progress_pct,
                "is_last_pose": self.current_index >= (total_count - 1),
            },
            "summary": summary_data,
        }
