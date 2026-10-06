"""
Conversational AI Yoga Coach Assistant for KI.AI.
Processes user dialogue, answers technique questions using real biomechanical session context,
enforces the safety health layer, and provides session adaptation actions (skip, shorten, modify).
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ConversationalCoach:
    """Handles bidirectional dialogue with the practitioner using real session context."""

    PAIN_KEYWORDS = ["hurt", "hurts", "pain", "injury", "injured", "sore", "strain", "tear", "sharp", "sprain", "discomfort"]

    def __init__(self, db=None):
        self.db = db

    def process_message(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: int = 1,
    ) -> Dict[str, Any]:
        """
        Processes practitioner message and generates caring, expert yoga coaching response with action triggers.
        
        Args:
            user_message: Transcribed or typed user query.
            context: Live context dict containing:
                - current_pose_name
                - current_score
                - joint_results (with deviations)
                - session_level
                - session_goal
                - completed_poses_count
                - remaining_duration
            user_id: User integer ID for database lookups.
            
        Returns:
            Dictionary with response text, speech audio string, suggested action, and safety flag.
        """
        msg_clean = (user_message or "").strip().lower()
        ctx = context or {}
        current_pose = ctx.get("current_pose_name", "your current pose")
        current_score = ctx.get("current_score", 0)
        joint_results = ctx.get("joint_results", [])

        # ==========================================
        # 1. CRITICAL SAFETY LAYER FIRST
        # ==========================================
        for kw in self.PAIN_KEYWORDS:
            if kw in msg_clean:
                response_text = (
                    "Please stop the movement immediately. If you are experiencing pain or sharp discomfort, "
                    "do not push through it. Release the posture, rest in Child's pose (Balasana) or sit comfortably. "
                    "Remember that KI.AI provides computer-vision fitness guidance and is not a substitute for professional medical care."
                )
                return {
                    "response": response_text,
                    "speak_text": "Please stop the movement immediately. If you feel pain, do not continue. Rest comfortably in Child's pose.",
                    "action": "PAUSE_AND_REST",
                    "intent": "safety_pain_alert",
                    "safety_alert": True,
                }

        # ==========================================
        # 2. ADAPTATION: CANNOT DO / TOO DIFFICULT
        # ==========================================
        if any(p in msg_clean for p in ["can't do", "cannot do", "too hard", "too difficult", "struggling", "impossible", "hard"]):
            response_text = (
                f"That's completely okay. Yoga is about honoring where your body is today. "
                f"For {current_pose}, you can soften the intensity by keeping your support foot grounded "
                f"or using a wall for balance. Would you like me to switch to an easier variation or skip to the next movement?"
            )
            return {
                "response": response_text,
                "speak_text": f"That is completely fine. For {current_pose}, take a gentle variation or wall support.",
                "action": "OFFER_VARIATION",
                "intent": "modify_pose",
                "safety_alert": False,
            }

        # ==========================================
        # 3. ACTION: SKIP CURRENT POSE
        # ==========================================
        if any(p in msg_clean for p in ["skip", "next pose", "skip this", "move on", "don't want to do"]):
            response_text = f"Understood. Skipping {current_pose}. Let's seamlessly transition into the next exercise in your roadmap."
            return {
                "response": response_text,
                "speak_text": f"Skipping {current_pose}. Let's move to the next exercise.",
                "action": "SKIP_POSE",
                "intent": "skip_pose",
                "safety_alert": False,
            }

        # ==========================================
        # 4. ACTION: SHORTEN SESSION
        # ==========================================
        if any(p in msg_clean for p in ["shorten", "10 min", "ten min", "15 min", "less time", "hurry", "quick session", "only have ten", "only have 10"]):
            response_text = "I've streamlined your roadmap to a focused 10-minute session while keeping today's core alignment focus."
            return {
                "response": response_text,
                "speak_text": "I have adjusted today's roadmap to a focused ten minute practice.",
                "action": "SHORTEN_SESSION",
                "target_duration_minutes": 10,
                "intent": "shorten_session",
                "safety_alert": False,
            }

        # ==========================================
        # 5. EXPLANATION: WHY IS SCORE LOW?
        # ==========================================
        if any(p in msg_clean for p in ["why is my score", "score low", "why low", "why did i get", "improve my score", "what is wrong"]):
            # Look at actual joint deviations from current evaluation
            worst_joint = None
            max_dev = 0.0
            for j in joint_results:
                raw_dev = j.get("deviation")
                if raw_dev is not None:
                    dev = float(raw_dev)
                else:
                    user_a = float(j.get("user_angle", j.get("actual_angle", 0.0)))
                    t_a = float(j.get("target_angle", 0.0))
                    dev = abs(user_a - t_a)
                if dev > max_dev:
                    max_dev = dev
                    worst_joint = j

            if worst_joint:
                j_name = worst_joint.get("formatted_name") or worst_joint.get("joint_name", "joint")
                actual_a = round(float(worst_joint.get("actual_angle") or worst_joint.get("user_angle", 0)))
                target_a = round(float(worst_joint.get("target_angle", 0)))
                diff = round(max_dev)
                response_text = (
                    f"Your current accuracy score is {current_score}%. The primary factor is your {j_name}, "
                    f"currently at {actual_a}° instead of target {target_a}° (deviation of {diff}°). "
                    f"{worst_joint.get('feedback_message', 'Adjust this joint to increase score.')}"
                )
                speak_text = f"Your main alignment factor is your {j_name}, off by {diff} degrees. Adjust this joint to boost your score."
            else:
                response_text = f"Your current accuracy is {current_score}%. Ensure your full body is visible and joints are within natural target angles."
                speak_text = f"Your score is {current_score} percent. Step into full camera view to align your posture."

            return {
                "response": response_text,
                "speak_text": speak_text,
                "action": "EXPLAIN_SCORE",
                "intent": "explain_score",
                "safety_alert": False,
            }

        # ==========================================
        # 6. PROGRESS: HOW AM I IMPROVING?
        # ==========================================
        if any(p in msg_clean for p in ["how am i improving", "my progress", "improving", "am i better", "how is my practice"]):
            if self.db:
                stats = self.db.get_user_stats(user_id) or {}
                avg_score = stats.get("avg_score", 85.0)
                sessions = stats.get("total_sessions", 0)
                fav = stats.get("favorite_pose", "Warrior II")
                response_text = (
                    f"You have completed {sessions} practice sessions with an overall average accuracy of {avg_score}%. "
                    f"Your strongest consistency is in {fav}. Continue regular practice to unlock the Progress and Mastery levels!"
                )
                speak_text = f"You have completed {sessions} sessions with an average accuracy of {avg_score} percent. Your consistency is improving steadily."
            else:
                response_text = "Your posture stability and hold duration have been steadily climbing over your recent sessions."
                speak_text = "Your posture stability and hold duration are showing steady improvement."

            return {
                "response": response_text,
                "speak_text": speak_text,
                "action": "SHOW_PROGRESS",
                "intent": "progress_inquiry",
                "safety_alert": False,
            }

        # ==========================================
        # 7. GENERAL YOGA INSTRUCTION & ENCOURAGEMENT
        # ==========================================
        default_resp = (
            f"I'm here with you. During {current_pose}, focus on lengthening your spine, "
            f"relaxing your shoulders down your back, and taking slow, deliberate breaths. "
            f"Let me know if you want to skip or need an easier variation."
        )
        return {
            "response": default_resp,
            "speak_text": f"Focus on slow, steady breaths and grounding your stance in {current_pose}.",
            "action": "COACH_ENCOURAGEMENT",
            "intent": "general_guidance",
            "safety_alert": False,
        }
