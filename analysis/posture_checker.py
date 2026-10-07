"""
Posture Checking Engine for AI Yoga Assistant.
Generic comparator that evaluates user landmark angles against pose rules / templates
(works identically for built-in and user-created custom poses).
Supports bilateral symmetry and identifies specific incorrect joints for targeted visual feedback.
"""

import logging
from typing import Any, Dict, List, Optional
from analysis.angle_calculator import AngleCalculator
from analysis.feedback import FeedbackEngine
from analysis.score_calculator import ScoreCalculator
from config import settings

logger = logging.getLogger(__name__)


class PostureChecker:
    """Evaluates actual user joint angles against expected pose rules."""

    MIRROR_MAP = {
        "left_knee": "right_knee",
        "right_knee": "left_knee",
        "left_hip": "right_hip",
        "right_hip": "left_hip",
        "left_shoulder": "right_shoulder",
        "right_shoulder": "left_shoulder",
        "left_elbow": "right_elbow",
        "right_elbow": "left_elbow",
        "left_wrist": "right_wrist",
        "right_wrist": "left_wrist",
        "left_ankle": "right_ankle",
        "right_ankle": "left_ankle",
    }

    def __init__(self):
        self.feedback_engine = FeedbackEngine()

    def _evaluate_joints(
        self,
        rules: List[Dict[str, Any]],
        actual_angles: Dict[str, float],
        mirrored: bool = False,
    ) -> List[Dict[str, Any]]:
        """Evaluates joints against rules directly or mirrored."""
        joint_results: List[Dict[str, Any]] = []

        for rule in rules:
            joint_name = rule.get("joint_name", "")
            eval_joint = self.MIRROR_MAP.get(joint_name, joint_name) if mirrored else joint_name
            target_angle = float(rule.get("target_angle", 0.0))
            tolerance = float(rule.get("tolerance", settings.DEFAULT_TOLERANCE_DEGREES))
            weight = float(rule.get("weight", 10.0))
            custom_msg = rule.get("feedback_message")

            actual_angle = actual_angles.get(eval_joint)

            if actual_angle is None:
                joint_results.append({
                    "joint_name": eval_joint,
                    "formatted_name": FeedbackEngine.format_joint_name(eval_joint),
                    "actual_angle": 0.0,
                    "target_angle": target_angle,
                    "tolerance": tolerance,
                    "deviation": 999.0,
                    "is_correct": False,
                    "score": 0.0,
                    "weight": weight,
                    "status_code": "NOT_DETECTED",
                    "status_label": "Not Detected",
                    "status_dot": "⚪",
                    "status_color": "#94A3B8",
                    "feedback_message": f"{FeedbackEngine.format_joint_name(eval_joint)}: Not Detected (Please adjust position)",
                })
                continue

            deviation = abs(actual_angle - target_angle)
            is_correct = deviation <= tolerance
            score = ScoreCalculator.calculate_joint_score(actual_angle, target_angle, tolerance)

            if is_correct:
                status_code = "CORRECT"
                status_label = "Correct"
                status_dot = "🟢"
                status_color = "#10B981"
            elif deviation <= (tolerance * 1.4):
                status_code = "WARNING"
                status_label = "Adjust Slightly"
                status_dot = "🟡"
                status_color = "#F59E0B"
            else:
                status_code = "INCORRECT"
                status_label = "Needs Correction"
                status_dot = "🔴"
                status_color = "#EF4444"

            feedback_msg = custom_msg or FeedbackEngine.generate_correction_message(
                eval_joint, actual_angle, target_angle
            )

            joint_results.append({
                "joint_name": eval_joint,
                "formatted_name": FeedbackEngine.format_joint_name(eval_joint),
                "actual_angle": actual_angle,
                "target_angle": target_angle,
                "tolerance": tolerance,
                "deviation": round(deviation, 1),
                "is_correct": is_correct,
                "score": score,
                "weight": weight,
                "status_code": status_code,
                "status_label": status_label,
                "status_dot": status_dot,
                "status_color": status_color,
                "feedback_message": feedback_msg,
            })

        return joint_results

    def check_posture(
        self,
        pose_data: Dict[str, Any],
        actual_angles: Dict[str, float],
        is_body_visible: bool = True,
        visibility_message: str = "",
    ) -> Dict[str, Any]:
        """
        Compares extracted angles against pose rules and generates full scoring report.
        
        Args:
            pose_data: Dictionary representing the pose, including 'rules' list.
            actual_angles: Dictionary of joint angles extracted by AngleCalculator.
            is_body_visible: Boolean indicating if all key landmarks are detected.
            visibility_message: Visibility warning string if not visible.
            
        Returns:
            Structured posture evaluation dictionary.
        """
        rules = pose_data.get("rules", [])
        pose_name = pose_data.get("name", "Unknown Pose")
        pose_id = pose_data.get("id")

        if not is_body_visible:
            msg = visibility_message or "Your full body is not visible. Please adjust camera position."
            return {
                "pose_id": pose_id,
                "pose_name": pose_name,
                "overall_score": 0.0,
                "score_level": "INCORRECT",
                "level_info": settings.SCORE_LEVELS["INCORRECT"],
                "joint_results": [],
                "incorrect_joints": [],
                "critical_incorrect_joints": [],
                "primary_feedback": msg,
                "all_feedback": [msg],
                "structured_feedback": [],
                "is_body_visible": False,
                "is_valid": False,
            }

        # Check both direct and mirrored orientation, choosing the best match
        direct_results = self._evaluate_joints(rules, actual_angles, mirrored=False)
        direct_score, _, _ = ScoreCalculator.calculate_overall_score(direct_results)

        mirrored_results = self._evaluate_joints(rules, actual_angles, mirrored=True)
        mirrored_score, _, _ = ScoreCalculator.calculate_overall_score(mirrored_results)

        if mirrored_score > direct_score and (mirrored_score - direct_score) > 10.0:
            joint_results = mirrored_results
        else:
            joint_results = direct_results

        # Calculate overall weighted score & tier
        overall_score, level_key, level_info = ScoreCalculator.calculate_overall_score(joint_results)

        # Extract specific incorrect joints for UI highlighting
        incorrect_joints = [
            j["joint_name"] for j in joint_results if j.get("status_code") in {"WARNING", "INCORRECT", "NOT_DETECTED"}
        ]
        critical_incorrect_joints = [
            j["joint_name"] for j in joint_results if j.get("status_code") in {"INCORRECT", "NOT_DETECTED"}
        ]

        # Generate directional feedback
        primary_feedback, all_feedback, structured_feedback = self.feedback_engine.produce_primary_feedback(
            joint_results,
            overall_score,
            is_body_visible=True,
        )

        return {
            "pose_id": pose_id,
            "pose_name": pose_name,
            "overall_score": overall_score,
            "score_level": level_key,
            "level_info": level_info,
            "joint_results": joint_results,
            "incorrect_joints": incorrect_joints,
            "critical_incorrect_joints": critical_incorrect_joints,
            "primary_feedback": primary_feedback,
            "all_feedback": all_feedback,
            "structured_feedback": structured_feedback,
            "is_body_visible": True,
            "is_valid": True,
        }
