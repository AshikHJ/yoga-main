"""
Corrective Feedback Engine for AI Yoga Assistant.
Generates natural language, joint-specific corrective cues and provides
thread-safe, rate-limited voice announcements via pyttsx3.
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from config import settings

logger = logging.getLogger(__name__)


from voice.voice_manager import Priority, get_voice_manager


class VoiceFeedbackWorker:
    """Thread-safe background speech controller delegating to centralized VoiceManager."""

    def __init__(self):
        self.voice_manager = get_voice_manager()
        self._enabled = settings.VOICE_FEEDBACK_ENABLED
        if not self._enabled:
            self.voice_manager.mute()

    def speak(self, text: str, force: bool = False, event_key: str = "", priority: Priority = Priority.NORMAL) -> bool:
        """Speaks the text through the centralized VoiceManager."""
        if not self._enabled:
            return False
        
        clean = (text or "").strip()
        if not clean:
            return False

        key = event_key or f"fb:{clean[:25]}"
        prio = Priority.CRITICAL if force else priority
        return self.voice_manager.speak(text=clean, priority=prio, event_key=key)

    def stop(self) -> None:
        """Immediately interrupts active speech and flushes queue."""
        self.voice_manager.stop()

    def set_enabled(self, enabled: bool) -> None:
        """Toggles voice feedback on or off."""
        self._enabled = enabled
        if enabled:
            self.voice_manager.unmute()
        else:
            self.voice_manager.mute()

    def is_enabled(self) -> bool:
        """Returns whether voice feedback is currently active and unmuted."""
        return self._enabled and not self.voice_manager.is_muted and not self.voice_manager.is_stopped


class FeedbackEngine:
    """Generates detailed, actionable joint-specific corrective cues."""

    def __init__(self):
        self.voice = VoiceFeedbackWorker()

    @staticmethod
    def format_joint_name(name: str) -> str:
        """Formats joint name from 'left_knee' to 'Left Knee'."""
        return name.replace("_", " ").title()

    @classmethod
    def generate_correction_message(
        cls,
        joint_name: str,
        actual_angle: float,
        target_angle: float,
        custom_rule_msg: Optional[str] = None
    ) -> str:
        """
        Generates specific, directional corrective instructions.
        
        Examples:
            - "Bend your left knee more (115° -> 90°)"
            - "Straighten your right elbow"
            - "Raise your left arm to shoulder level"
        """
        diff = actual_angle - target_angle
        abs_diff = abs(diff)
        joint_fmt = cls.format_joint_name(joint_name)

        if "knee" in joint_name:
            if target_angle > 150.0:
                return f"Straighten your {joint_fmt}"
            elif diff > 0:
                return f"Bend your {joint_fmt} deeper by about {int(abs_diff)}°"
            else:
                return f"Straighten your {joint_fmt} slightly by about {int(abs_diff)}°"

        elif "elbow" in joint_name:
            if target_angle > 150.0:
                return f"Straighten your {joint_fmt}"
            elif diff > 0:
                return f"Bend your {joint_fmt} more"
            else:
                return f"Extend your {joint_fmt} more"

        elif "shoulder" in joint_name:
            if diff < 0:
                return f"Raise your {joint_fmt} higher (target {int(target_angle)}°)"
            else:
                return f"Lower your {joint_fmt} slightly (target {int(target_angle)}°)"

        elif "hip" in joint_name:
            if diff < 0:
                return f"Open your {joint_fmt} more"
            else:
                return f"Hinge your {joint_fmt} deeper"

        elif "torso" in joint_name:
            if abs_diff > 10.0:
                return "Keep your torso centered and upright"

        # Fallback to custom rule message or generic
        if custom_rule_msg:
            return custom_rule_msg
        return f"Adjust your {joint_fmt}"

    def produce_primary_feedback(
        self,
        joint_results: List[Dict[str, Any]],
        overall_score: float,
        is_body_visible: bool = True,
        visibility_message: str = ""
    ) -> Tuple[str, List[str], List[Dict[str, Any]]]:
        """
        Determines primary cue, text list, and structured cue objects with dot badges.
        
        Returns:
            Tuple of:
                - primary_message (str)
                - all_correction_messages (List[str])
                - structured_feedback (List[Dict[str, Any]])
        """
        if not is_body_visible:
            msg = visibility_message or "Please adjust position so your full body is visible."
            item = {"dot": "⚪", "color": "#94A3B8", "message": msg}
            return msg, [msg], [item]

        if overall_score >= settings.SCORE_EXCELLENT_THRESHOLD:
            msg = "Excellent posture! Hold steady."
            item = {"dot": "🟢", "color": "#10B981", "message": msg}
            return msg, [], [item]

        corrections: List[Tuple[float, str, Dict[str, Any]]] = []

        for res in joint_results:
            status_code = res.get("status_code", "CORRECT")
            if status_code != "CORRECT":
                deviation = abs(res.get("actual_angle", 0.0) - res.get("target_angle", 0.0))
                weight = res.get("weight", 10.0)
                priority = deviation * weight
                
                msg = res.get("feedback_message") or self.generate_correction_message(
                    res.get("joint_name", ""),
                    res.get("actual_angle", 0.0),
                    res.get("target_angle", 0.0)
                )

                dot = res.get("status_dot", "🔴")
                color = res.get("status_color", "#EF4444")
                cue_obj = {
                    "dot": dot,
                    "color": color,
                    "message": msg,
                    "joint_name": res.get("formatted_name", ""),
                }
                corrections.append((priority, msg, cue_obj))

        if not corrections:
            if overall_score >= settings.SCORE_GOOD_THRESHOLD:
                msg = "Good posture. Refine alignment slightly."
                return msg, [], [{"dot": "🟢", "color": "#10B981", "message": msg}]
            msg = "Adjust posture to match the reference pose."
            return msg, [], [{"dot": "🟡", "color": "#F59E0B", "message": msg}]

        # Sort by priority descending
        corrections.sort(key=lambda x: x[0], reverse=True)
        all_msgs = [c[1] for c in corrections]
        structured = [c[2] for c in corrections]
        primary_msg = all_msgs[0]

        return primary_msg, all_msgs, structured

    def speak_cue(self, text: str) -> None:
        """Dispatches text cue to TTS."""
        self.voice.speak(text)
