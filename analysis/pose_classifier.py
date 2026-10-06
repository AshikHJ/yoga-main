"""
Pose Identification / Classification Engine for AI Yoga Assistant.
Distinguishes what yoga pose the user is currently performing across the pose catalog
independently of specific posture accuracy scoring.
"""

from typing import Any, Dict, List, Optional, Tuple
from analysis.score_calculator import ScoreCalculator


class PoseClassifier:
    """Classifies which yoga pose a set of detected angles represents."""

    @classmethod
    def identify_pose(
        cls,
        actual_angles: Dict[str, float],
        all_poses: List[Dict[str, Any]],
        confidence_threshold: float = 65.0,
    ) -> Tuple[str, float, Optional[Dict[str, Any]]]:
        """
        Evaluates detected angles against all known poses to determine the closest match.
        
        Args:
            actual_angles: Dictionary of extracted joint angles.
            all_poses: List of all pose dictionaries containing their respective rules.
            confidence_threshold: Minimum match score to qualify as a known pose.
            
        Returns:
            Tuple of:
                - detected_pose_name (str)
                - match_confidence (float 0.0 - 100.0)
                - matched_pose_dict (Optional[Dict])
        """
        if not actual_angles or not all_poses:
            return "No Pose Detected", 0.0, None

        best_score = -1.0
        best_pose: Optional[Dict[str, Any]] = None

        for pose in all_poses:
            rules = pose.get("rules", [])
            if not rules:
                continue

            total_score = 0.0
            total_weight = 0.0

            for rule in rules:
                joint_name = rule.get("joint_name", "")
                target = float(rule.get("target_angle", 0.0))
                tol = float(rule.get("tolerance", 20.0))  # Slightly relaxed tolerance for classification
                weight = float(rule.get("weight", 10.0))

                actual = actual_angles.get(joint_name)
                if actual is not None:
                    joint_score = ScoreCalculator.calculate_joint_score(actual, target, tol, max_penalty_deviation=60.0)
                    total_score += joint_score * weight
                    total_weight += weight
                else:
                    # Missing joint penalizes classification match
                    total_weight += weight

            if total_weight > 0:
                pose_score = total_score / total_weight
                if pose_score > best_score:
                    best_score = pose_score
                    best_pose = pose

        best_score = float(round(best_score, 1))

        if best_pose and best_score >= confidence_threshold:
            return best_pose.get("name", "Unknown Pose"), best_score, best_pose
        elif best_pose and best_score >= 50.0:
            return f"Transitioning / {best_pose.get('name')}", best_score, best_pose
        else:
            return "Unknown / Neutral Pose", max(0.0, best_score), None
