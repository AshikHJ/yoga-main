"""
Kiki AI Yoga Companion & Conversational Intelligence Service for KI.AI.
Integrates live biomechanical pose assessment, verified classical yoga instructions,
rule-based and Gemini LLM-grounded guidance, safety guardrails, and character state modeling.

Supported Character States:
- idle: No active pose or frame evaluation.
- listening: Frontend transient state (capturing practitioner speech).
- thinking: Frontend/backend transient state (generating response).
- confused: Insufficient landmark visibility, occluded joints, or tracking loss.
- incorrect_pose: Mismatched pose or significant alignment errors.
- adjust_pose: Minor joint angle adjustment required.
- correct_pose: Posture is aligned and hold countdown is active.
- celebrating: Pose hold completed or practice milestone reached.
- error: Request or system processing failure.
"""

from enum import Enum
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import requests

from config import settings

logger = logging.getLogger(__name__)


class KikiCharacterState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    CONFUSED = "confused"
    INCORRECT_POSE = "incorrect_pose"
    ADJUST_POSE = "adjust_pose"
    CORRECT_POSE = "correct_pose"
    CELEBRATING = "celebrating"
    ERROR = "error"


def determine_kiki_state(
    frame_eval: Optional[Dict[str, Any]] = None,
    posture_result: Optional[Dict[str, Any]] = None,
    is_body_visible: bool = True,
    pose_matched: bool = True,
    tracking_state: Optional[str] = None,
    match_score: Optional[float] = None,
    session_state: Optional[Any] = None,
    is_listening: bool = False,
    is_thinking: bool = False,
    has_error: bool = False,
    posture_eval: Optional[Dict[str, Any]] = None,
) -> KikiCharacterState:
    """
    Deterministically computes Kiki's character state across all 9 canonical states
    from real computer-vision metrics, audio events, and user interaction states.
    """
    if posture_eval and not posture_result:
        posture_result = posture_eval
    frame_eval = frame_eval or {}
    posture_result = posture_result or {}

    # 1. Error state (vision/hardware pipeline error)
    if has_error:
        return KikiCharacterState.ERROR

    # 2. Voice listening active
    if is_listening:
        return KikiCharacterState.LISTENING

    # 3. Query reasoning / thinking state
    if is_thinking:
        return KikiCharacterState.THINKING

    # 4. Pose hold or session completed celebration
    state_str = str(getattr(session_state, "value", session_state) or "").upper()
    if (
        state_str in {"COMPLETING_POSE", "COMPLETED"}
        or frame_eval.get("status_code") == "COMPLETED"
        or frame_eval.get("state") in {"COMPLETING_POSE", "COMPLETED"}
    ):
        return KikiCharacterState.CELEBRATING

    # 5. Confused: Body partially occluded or insufficient keypoints
    status_state = posture_result.get("status_state")
    if tracking_state == "PARTIAL_BODY" or status_state == "insufficient_data":
        return KikiCharacterState.CONFUSED

    # 6. Idle: Practitioner not visible or no person tracking
    if not is_body_visible or tracking_state == "NO_PERSON":
        return KikiCharacterState.IDLE

    # No active evaluation data
    if not frame_eval and not posture_result and match_score is None:
        return KikiCharacterState.IDLE

    # 7. Incorrect pose: Wrong pose detected or low score
    if not pose_matched or tracking_state == "WRONG_POSE" or frame_eval.get("status_code") == "WRONG_POSE":
        return KikiCharacterState.INCORRECT_POSE

    overall_score = float(match_score if match_score is not None else posture_result.get("overall_score", 0.0))
    is_aligned = frame_eval.get("is_aligned", False)

    # 8. Correct pose: Proper alignment
    if status_state == "correct" or (overall_score >= 80.0 and (is_aligned or match_score is not None)):
        return KikiCharacterState.CORRECT_POSE

    # 9. Adjust pose: Borderline alignment needing adjustment
    if status_state == "adjust" or (60.0 <= overall_score < 80.0):
        return KikiCharacterState.ADJUST_POSE

    if status_state == "incorrect" or overall_score < 60.0:
        return KikiCharacterState.INCORRECT_POSE

    return KikiCharacterState.IDLE


def clean_spoken_text(text: str) -> str:
    """
    Cleans response text into a concise, natural utterance suitable for
    female spoken delivery (strips markdown, URLs, symbols, bullet points).
    """
    if not text:
        return ""
    # Strip markdown headers, bold, bullets, links
    clean = re.sub(r"https?://\S+", "", text)
    clean = re.sub(r"\[.*?\]\(.*?\)", " ", clean)
    clean = re.sub(r"[\*#_`~>\[\]]", " ", clean)
    clean = re.sub(r"^\s*[-•]\s*", "", clean, flags=re.MULTILINE)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Extract first 1 or 2 clean sentences for natural spoken cadence
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    if sentences:
        spoken = " ".join(sentences[:2]).strip()
        if len(spoken) > 220:
            spoken = spoken[:217].rsplit(" ", 1)[0] + "."
        return spoken
    return clean[:200]


class KikiService:
    """Centralized service for Kiki companion interactions and real-time state."""

    PAIN_KEYWORDS = [
        "hurt", "hurts", "pain", "injury", "injured", "sore", "strain",
        "tear", "sharp", "sprain", "discomfort", "burning", "pinch", "pinching"
    ]

    def __init__(self, db=None, engine=None):
        self.db = db
        self.engine = engine

    def get_kiki_state(
        self,
        engine,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Retrieves Kiki's current character state and the latest verified assessment.
        Omits fabricated measurements — returns only real landmark data.
        """
        if not engine:
            return {
                "character_state": KikiCharacterState.IDLE.value,
                "has_active_pose": False,
                "pose_id": None,
                "pose_name": None,
                "assessment": None,
                "message": "Kiki is resting. Select a pose to begin your session.",
            }

        latest_eval = getattr(engine, "latest_assessment", None)
        current_exercise = engine.current_exercise

        if not current_exercise and not latest_eval:
            return {
                "character_state": KikiCharacterState.IDLE.value,
                "has_active_pose": False,
                "pose_id": None,
                "pose_name": None,
                "assessment": None,
                "message": "Kiki is ready. Choose a pose or start your daily roadmap.",
            }

        pose_name = current_exercise.get("name") if current_exercise else None
        pose_id = current_exercise.get("target_pose_id") if current_exercise else None

        # Fetch verified pose guidance if pose_id is known
        pose_guide = None
        if pose_id and self.db:
            pose_guide = self.get_pose_guide(int(pose_id))

        if not latest_eval:
            return {
                "character_state": KikiCharacterState.IDLE.value,
                "has_active_pose": True,
                "pose_id": pose_id,
                "pose_name": pose_name,
                "assessment": None,
                "pose_guide": pose_guide,
                "message": f"Moving into {pose_name}. Position yourself in front of the camera.",
            }

        # Real assessment data from the latest processed frame
        frame_eval = latest_eval.get("frame_eval", {})
        posture_result = latest_eval.get("posture_result", {})
        is_body_visible = latest_eval.get("is_body_visible", True)
        pose_matched = latest_eval.get("pose_matched", True)

        char_state = determine_kiki_state(
            frame_eval=frame_eval,
            posture_result=posture_result,
            is_body_visible=is_body_visible,
            pose_matched=pose_matched,
        )

        # Extract only real measured angles and target angles
        measured_joints = []
        for j in posture_result.get("joint_results", []):
            if j.get("status_code") != "NOT_DETECTED":
                measured_joints.append({
                    "joint_name": j.get("joint_name"),
                    "formatted_name": j.get("formatted_name"),
                    "actual_angle": j.get("actual_angle"),
                    "target_angle": j.get("target_angle"),
                    "deviation": j.get("deviation"),
                    "status_code": j.get("status_code"),
                    "feedback_message": j.get("feedback_message"),
                })

        return {
            "character_state": char_state.value,
            "has_active_pose": True,
            "pose_id": pose_id or posture_result.get("pose_id"),
            "pose_name": pose_name or posture_result.get("pose_name"),
            "assessment": {
                "overall_score": posture_result.get("overall_score", 0.0),
                "score_level": posture_result.get("score_level"),
                "status_state": posture_result.get("status_state", "unknown"),
                "is_body_visible": is_body_visible,
                "is_aligned": frame_eval.get("is_aligned", False),
                "pose_matched": pose_matched,
                "hold_seconds": frame_eval.get("hold_seconds", 0.0),
                "target_seconds": frame_eval.get("target_seconds", 20.0),
                "measured_joints": measured_joints,
                "primary_feedback": posture_result.get("primary_feedback", ""),
                "speech_cue": frame_eval.get("speech_cue"),
            },
            "pose_guide": pose_guide,
            "message": frame_eval.get("speech_cue") or posture_result.get("primary_feedback") or "Maintain steady breath.",
        }

    def get_pose_guide(self, pose_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves verified classical instructions and rules from database."""
        if not self.db:
            return None
        pose = self.db.get_pose_by_id(pose_id)
        if not pose:
            return None
        rules = [
            {
                "joint_name": r.get("joint_name"),
                "target_angle": r.get("target_angle"),
                "tolerance": r.get("tolerance"),
                "feedback": r.get("feedback_message"),
            }
            for r in pose.get("rules", [])
        ]
        return {
            "status": "success",
            "pose": pose,
            "rules": rules,
            "id": pose.get("id"),
            "name": pose.get("name"),
            "sanskrit_name": pose.get("sanskrit_name"),
            "category": pose.get("category"),
            "difficulty": pose.get("difficulty"),
            "instructions": pose.get("instructions", []),
            "benefits": pose.get("benefits", []),
            "precautions": pose.get("precautions", ""),
            "target_joints": rules,
        }

    def call_gemini_api(
        self,
        user_message: str,
        context_prompt: str,
        history: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 6.0,
    ) -> Tuple[bool, str, str, Optional[str]]:
        """
        Sends dialogue query to Google Gemini API via REST.
        Returns:
            Tuple of (success: bool, provider: str, response_text: str, speak_text: Optional[str])
        """
        api_key = getattr(settings, "GEMINI_API_KEY", "").strip()
        if not api_key:
            return False, "unconfigured", "Gemini API key is not configured.", None

        model = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash").strip() or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        system_instruction = (
            "You are Kiki, an intelligent, empathetic female AI Yoga Teacher and companion for KI.AI. "
            "You communicate with warm encouragement, biomechanical precision, and classical yoga wisdom. "
            "STRICT RULES:\n"
            "1. Answer yoga postures, alignment, breathing (pranayama), and mindfulness questions accurately.\n"
            "2. Ground posture corrections strictly in the real session data provided in the prompt.\n"
            "3. If the context states that camera tracking is inactive or the user is not visible, be honest: "
            "state that you cannot see their posture right now, and give general alignment instructions without "
            "fabricating visual observations.\n"
            "4. Never make medical claims or diagnose injuries. If the user mentions pain, advise stopping immediately "
            "and resting in Balasana (Child's pose).\n"
            "5. Speak with a warm, supportive female coach cadence."
        )

        contents = []
        if history:
            for turn in history[-4:]:
                role = "user" if turn.get("role") == "user" else "model"
                txt = turn.get("message") or turn.get("text") or ""
                if txt:
                    contents.append({"role": role, "parts": [{"text": txt}]})

        user_content_text = f"{context_prompt}\n\nPractitioner Question:\n{user_message}"
        contents.append({"role": "user", "parts": [{"text": user_content_text}]})

        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 300,
                "topP": 0.85,
            },
        }

        try:
            resp = requests.post(url, json=payload, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        reply_text = parts[0]["text"].strip()
                        speak = clean_spoken_text(reply_text)
                        return True, "gemini", reply_text, speak
            logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text[:180]}")
            return False, "gemini_http_error", f"Gemini error HTTP {resp.status_code}", None
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}")
            return False, "gemini_network_error", str(e), None

    def answer_grounded_yoga_query(
        self,
        user_message: str,
        current_pose_name: str,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Grounded classical yoga knowledge retriever used when Gemini API is unconfigured or unavailable.
        Provides truthful instruction from the database catalog rather than dummy canned responses.
        """
        msg_clean = user_message.lower().strip()
        all_poses = self.db.get_all_poses() if self.db else []

        # Check for matching pose in supported library
        matched_pose = None
        for p in all_poses:
            p_name = p.get("name", "").lower()
            s_name = p.get("sanskrit_name", "").lower()
            p_slug = p_name.split("(")[0].strip()
            if p_slug in msg_clean or (s_name and s_name in msg_clean):
                matched_pose = p
                break

        if matched_pose:
            p_name = matched_pose.get("name")
            sanskrit = matched_pose.get("sanskrit_name", "")
            benefits = matched_pose.get("benefits", [])
            precautions = matched_pose.get("precautions", "")
            instr = matched_pose.get("instructions", [])

            resp_lines = [
                f"**{p_name}** ({sanskrit}):",
                f"- **Alignment Key:** {instr[0] if instr else 'Lengthen spine and ground into foundation.'}",
            ]
            if benefits:
                resp_lines.append(f"- **Benefits:** {benefits[0]}")
            if precautions:
                resp_lines.append(f"- **Safety Notice:** {precautions}")

            resp_text = "\n".join(resp_lines)
            speak_text = f"{p_name} is a classical posture. {instr[0] if instr else 'Focus on steady spine alignment and smooth breathing.'}"

            return {
                "character_state": KikiCharacterState.CORRECT_POSE.value,
                "kiki_state": KikiCharacterState.CORRECT_POSE.value,
                "response": resp_text,
                "reply": resp_text,
                "speak_text": clean_spoken_text(speak_text),
                "safety_alert": False,
                "action": "EXPLAIN_POSE",
                "intent": "pose_explanation",
                "ai_provider": "local_grounded_engine",
                "provider_status": "unconfigured",
            }

        # Pranayama / Breathing guidance
        if any(w in msg_clean for w in ["breath", "breathing", "pranayama", "inhale", "exhale", "ujjayi"]):
            resp = (
                "In yoga, steady breath anchors the nervous system. Practice Dirga Pranayama (three-part breath): "
                "Inhale smoothly through your nose into belly, ribs, and chest for 4 counts. "
                "Exhale gently for 4 counts, maintaining length through the crown of your head."
            )
            speak = "Practice three-part breathing. Inhale gently for four counts, and exhale smoothly for four counts."
            return {
                "character_state": KikiCharacterState.CORRECT_POSE.value,
                "kiki_state": KikiCharacterState.CORRECT_POSE.value,
                "response": resp,
                "reply": resp,
                "speak_text": clean_spoken_text(speak),
                "safety_alert": False,
                "action": "BREATHING_GUIDANCE",
                "intent": "breathing_guidance",
                "ai_provider": "local_grounded_engine",
                "provider_status": "unconfigured",
            }

        # Warmup & Routine guidance
        if any(w in msg_clean for w in ["warm up", "warmup", "start", "routine", "sequence", "surya"]):
            resp = (
                "Surya Namaskar (Sun Salutation) is the classical sequence to warm every major joint. "
                "Move through Pranamasana, Hastauttanasana, and Padahastasana, syncing each movement with an inhale or exhale."
            )
            speak = "Surya Namaskar warms the spine and shoulders. Flow through each asana with conscious breath."
            return {
                "character_state": KikiCharacterState.CORRECT_POSE.value,
                "kiki_state": KikiCharacterState.CORRECT_POSE.value,
                "response": resp,
                "reply": resp,
                "speak_text": clean_spoken_text(speak),
                "safety_alert": False,
                "action": "RECOMMEND_SEQUENCE",
                "intent": "routine_guidance",
                "ai_provider": "local_grounded_engine",
                "provider_status": "unconfigured",
            }

        # Default grounded posture encouragement
        resp = (
            f"In {current_pose_name}, maintain smooth diaphragmatic breathing. "
            f"Ground firmly through your foundation, lengthen your spine, and relax your shoulders away from your ears. "
            f"(Note: To chat with Kiki using generative AI, add your GEMINI_API_KEY to your .env file)."
        )
        speak = f"In {current_pose_name}, lengthen your spine, soften your gaze, and maintain steady breath."
        return {
            "character_state": KikiCharacterState.IDLE.value,
            "kiki_state": KikiCharacterState.IDLE.value,
            "response": resp,
            "reply": resp,
            "speak_text": clean_spoken_text(speak),
            "safety_alert": False,
            "action": "COACH_ENCOURAGEMENT",
            "intent": "coach_encouragement",
            "ai_provider": "local_grounded_engine",
            "provider_status": "unconfigured",
        }

    def process_query(
        self,
        user_message: str = "",
        user_id: int = 1,
        engine=None,
        is_pro: bool = True,
        message: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Processes practitioner question with contextual grounding.
        Prioritizes safety layer first, queries live biomechanical session context,
        and uses Gemini LLM or verified database knowledge base.
        """
        clean_msg = (message or user_message or "").strip()
        if not engine:
            try:
                from web_app import get_coach_engine_for_user
                engine = self.engine or (get_coach_engine_for_user(user_id) if user_id else None)
            except Exception:
                engine = self.engine

        if not clean_msg:
            return {
                "character_state": KikiCharacterState.IDLE.value,
                "kiki_state": KikiCharacterState.IDLE.value,
                "response": "I'm listening. Ask me about your pose alignment, posture score, or session pace.",
                "reply": "I'm listening. Ask me about your pose alignment, posture score, or session pace.",
                "speak_text": "I am listening. Ask me anything about your yoga practice.",
                "voice_gender": "female",
                "safety_alert": False,
                "action": "NONE",
                "intent": "none",
                "ai_provider": "local",
                "provider_status": "ready",
            }

        # 1. CRITICAL SAFETY GUARDRAIL
        msg_lower = clean_msg.lower()
        for kw in self.PAIN_KEYWORDS:
            if kw in msg_lower:
                pain_msg = (
                    "Please stop the movement immediately. If you are experiencing pain or sharp discomfort, "
                    "release the pose gently and rest in Child's pose (Balasana). "
                    "KI.AI provides computer-vision fitness guidance and is not a substitute for medical advice from a doctor or healthcare professional."
                )
                speak = "Please stop immediately. If you feel pain, do not continue. Rest comfortably in Child's pose."
                return {
                    "character_state": KikiCharacterState.CONFUSED.value,
                    "kiki_state": KikiCharacterState.CONFUSED.value,
                    "response": pain_msg,
                    "reply": pain_msg,
                    "speak_text": speak,
                    "voice_gender": "female",
                    "safety_alert": True,
                    "action": "PAUSE_AND_REST",
                    "intent": "pain_safety_alert",
                    "ai_provider": "safety_guardrail",
                    "provider_status": "active",
                }

        # 2. Extract live biomechanical session context
        latest_eval = getattr(engine, "latest_assessment", None) if engine else None
        current_pose_name = "your current pose"
        overall_score = 0
        joint_results = []
        is_body_visible = False
        has_real_tracking = False

        if engine and getattr(engine, "current_exercise", None):
            current_pose_name = engine.current_exercise.get("name", "your current pose")

        if latest_eval:
            posture_result = latest_eval.get("posture_result") or latest_eval.get("eval_details") or latest_eval
            overall_score = round(float(posture_result.get("overall_score", latest_eval.get("overall_score", 0.0))))
            joint_results = posture_result.get("joint_results") or posture_result.get("incorrect_joints") or []
            is_body_visible = bool(latest_eval.get("is_body_visible", True))
            has_real_tracking = is_body_visible and (bool(joint_results) or overall_score > 0)

        # 3. Intent: Question about score / alignment explanation
        if any(q in msg_lower for q in ["why is my score", "score low", "how to improve", "what is wrong", "my score", "alignment", "score", "why did i"]):
            worst_joint = None
            max_dev = 0.0
            for j in joint_results:
                if isinstance(j, dict):
                    dev = float(j.get("deviation", 0.0))
                    if dev > max_dev:
                        max_dev = dev
                        worst_joint = j

            if worst_joint and has_real_tracking:
                j_name = worst_joint.get("formatted_name") or str(worst_joint.get("joint_name", "")).replace("_", " ")
                actual_a = round(float(worst_joint.get("actual_angle", 0)))
                target_a = round(float(worst_joint.get("target_angle", 0)))
                resp = (
                    f"Your current posture accuracy is {overall_score}%. The main adjustment is your {j_name}, "
                    f"currently at {actual_a}° instead of target {target_a}° (off by {int(max_dev)}°). "
                    f"{worst_joint.get('feedback_message', 'Adjust this joint to increase score.')}"
                )
                speak = f"Your main adjustment is your {j_name}, off by {int(max_dev)} degrees. Follow the visual cue to align it."
                return {
                    "character_state": KikiCharacterState.ADJUST_POSE.value,
                    "kiki_state": KikiCharacterState.ADJUST_POSE.value,
                    "response": resp,
                    "reply": resp,
                    "speak_text": speak,
                    "voice_gender": "female",
                    "safety_alert": False,
                    "action": "EXPLAIN_SCORE",
                    "intent": "score_explanation",
                    "ai_provider": "biomechanical_engine",
                    "provider_status": "active",
                    "details": {
                        "joint_name": j_name,
                        "actual_angle": actual_a,
                        "target_angle": target_a,
                        "deviation": int(max_dev),
                    },
                }
            elif has_real_tracking:
                resp = f"Your current measured score is {overall_score}%. Ensure your full body stays steady in the camera frame."
                return {
                    "character_state": KikiCharacterState.CORRECT_POSE.value if overall_score >= 75 else KikiCharacterState.ADJUST_POSE.value,
                    "kiki_state": KikiCharacterState.CORRECT_POSE.value if overall_score >= 75 else KikiCharacterState.ADJUST_POSE.value,
                    "response": resp,
                    "reply": resp,
                    "speak_text": f"Your score is {overall_score} percent. Keep steady alignment.",
                    "voice_gender": "female",
                    "safety_alert": False,
                    "action": "EXPLAIN_SCORE",
                    "intent": "score_explanation",
                    "ai_provider": "biomechanical_engine",
                    "provider_status": "active",
                }
            else:
                # Truthful handling when camera is inactive or body not detected
                resp = (
                    "I cannot see your posture right now because the camera is inactive or your body is not fully in frame. "
                    "Position your device so your head and feet are visible to receive live alignment scoring."
                )
                speak = "I cannot see your posture right now. Step back into camera view to receive live scoring."
                return {
                    "character_state": KikiCharacterState.CONFUSED.value,
                    "kiki_state": KikiCharacterState.CONFUSED.value,
                    "response": resp,
                    "reply": resp,
                    "speak_text": speak,
                    "voice_gender": "female",
                    "safety_alert": False,
                    "action": "EXPLAIN_SCORE",
                    "intent": "score_explanation",
                    "ai_provider": "biomechanical_engine",
                    "provider_status": "camera_inactive",
                }

        # 4. Intent: Pose modification / too hard
        if any(q in msg_lower for q in ["too hard", "can't do", "cannot do", "struggling", "difficult", "modify"]):
            resp = (
                f"Honoring your body's limits is true yoga. For {current_pose_name}, you can soften your stance, "
                f"use a wall for balance, or reduce the bend. Would you like me to switch to an easier variation?"
            )
            return {
                "character_state": KikiCharacterState.ADJUST_POSE.value,
                "kiki_state": KikiCharacterState.ADJUST_POSE.value,
                "response": resp,
                "reply": resp,
                "speak_text": f"That is completely fine. For {current_pose_name}, soften your stance or take support.",
                "voice_gender": "female",
                "safety_alert": False,
                "action": "OFFER_VARIATION",
                "intent": "offer_variation",
                "ai_provider": "adaptive_engine",
                "provider_status": "active",
            }

        # 5. Intent: Skip pose
        if any(q in msg_lower for q in ["skip", "next pose", "skip this", "move on"]):
            resp = f"Skipping {current_pose_name}. Moving ahead to the next pose in your roadmap."
            return {
                "character_state": KikiCharacterState.IDLE.value,
                "kiki_state": KikiCharacterState.IDLE.value,
                "response": resp,
                "reply": resp,
                "speak_text": f"Skipping {current_pose_name}. Moving to next exercise.",
                "voice_gender": "female",
                "safety_alert": False,
                "action": "SKIP_POSE",
                "intent": "skip_pose",
                "ai_provider": "session_engine",
                "provider_status": "active",
            }

        # 6. Intent: User progress / stats
        if any(q in msg_lower for q in ["progress", "improving", "how am i doing", "my stats", "history"]):
            sessions_count = 0
            avg_acc = 80.0
            if self.db:
                stats = self.db.get_user_stats(user_id) or {}
                sessions_count = stats.get("total_sessions", 0)
                avg_acc = stats.get("avg_score", 80.0)

            c_state = KikiCharacterState.CELEBRATING.value if sessions_count > 0 else KikiCharacterState.IDLE.value
            resp = f"You have logged {sessions_count} sessions with an average accuracy of {avg_acc}%. Keep showing up on your mat!"
            return {
                "character_state": c_state,
                "kiki_state": c_state,
                "response": resp,
                "reply": resp,
                "speak_text": f"You have logged {sessions_count} sessions with {avg_acc} percent average accuracy. Great dedication.",
                "voice_gender": "female",
                "safety_alert": False,
                "action": "SHOW_PROGRESS",
                "intent": "show_progress",
                "ai_provider": "database_analytics",
                "provider_status": "active",
            }

        # 7. Conversational Query — Try Gemini LLM first if configured
        if getattr(settings, "GEMINI_API_KEY", ""):
            # Build context prompt grounded in real measurements
            context_lines = [
                f"Current Session Posture: {current_pose_name}",
                f"Camera Posture Tracking Active: {'YES' if has_real_tracking else 'NO'}",
            ]
            if has_real_tracking:
                context_lines.append(f"Measured Alignment Score: {overall_score}%")
                if joint_results:
                    context_lines.append(
                        "Measured Deviations: "
                        + ", ".join(
                            f"{j.get('joint_name')}: {j.get('actual_angle')}° vs target {j.get('target_angle')}°"
                            for j in joint_results[:4]
                            if isinstance(j, dict)
                        )
                    )
            else:
                context_lines.append(
                    "NOTICE: You currently cannot see the user's posture (no camera feed or person not visible). "
                    "Do NOT claim to see them or make up scores."
                )

            context_prompt = "\n".join(context_lines)
            ok, provider, reply_txt, speak_txt = self.call_gemini_api(
                user_message=clean_msg,
                context_prompt=context_prompt,
                history=history,
            )

            if ok:
                char_state = KikiCharacterState.CORRECT_POSE.value if overall_score >= 75 else KikiCharacterState.IDLE.value
                return {
                    "character_state": char_state,
                    "kiki_state": char_state,
                    "response": reply_txt,
                    "reply": reply_txt,
                    "speak_text": speak_txt or clean_spoken_text(reply_txt),
                    "voice_gender": "female",
                    "safety_alert": False,
                    "action": "GENERATE_DIALOGUE",
                    "intent": "general_dialogue",
                    "ai_provider": "gemini",
                    "provider_status": "active",
                    "model": getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash"),
                    "live_tracking_available": has_real_tracking,
                }
            else:
                logger.info(f"Gemini unavailable ({provider}). Falling back to grounded classical yoga engine.")

        # 8. Grounded Classical Yoga Engine (When Gemini is unconfigured or unavailable)
        grounded_resp = self.answer_grounded_yoga_query(
            user_message=clean_msg,
            current_pose_name=current_pose_name,
            user_id=user_id,
        )
        grounded_resp["voice_gender"] = "female"
        grounded_resp["live_tracking_available"] = has_real_tracking
        return grounded_resp
