"""
Pose Identification / Classification Engine for AI Yoga Assistant.
Distinguishes what yoga pose the user is currently performing across the pose catalog
independently of specific posture accuracy scoring.
Supports bilateral symmetry (left/right leg variations) and geometric posture sanity checks.
"""

from typing import Any, Dict, List, Optional, Tuple
from analysis.score_calculator import ScoreCalculator


class PoseClassifier:
    """Classifies which yoga pose a set of detected angles represents."""

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

    @classmethod
    def _evaluate_rule_set(
        cls,
        actual_angles: Dict[str, float],
        rules: List[Dict[str, Any]],
        mirrored: bool = False,
    ) -> float:
        """Computes weighted match score against a rule set (optionally mirrored)."""
        total_score = 0.0
        total_weight = 0.0

        for rule in rules:
            joint_name = rule.get("joint_name", "")
            if mirrored:
                eval_joint = cls.MIRROR_MAP.get(joint_name, joint_name)
            else:
                eval_joint = joint_name

            target = float(rule.get("target_angle", 0.0))
            tol = float(rule.get("tolerance", 20.0))
            weight = float(rule.get("weight", 10.0))

            actual = actual_angles.get(eval_joint)
            if actual is not None:
                joint_score = ScoreCalculator.calculate_joint_score(
                    actual, target, tol, max_penalty_deviation=60.0
                )
                total_score += joint_score * weight
                total_weight += weight
            else:
                total_weight += weight

        return (total_score / total_weight) if total_weight > 0 else 0.0

    @classmethod
    def identify_pose(
        cls,
        actual_angles: Dict[str, float],
        all_poses: List[Dict[str, Any]],
        confidence_threshold: float = 65.0,
        expected_pose: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, float, Optional[Dict[str, Any]]]:
        """
        Evaluates detected angles against all known poses to determine the closest match.
        Supports bilateral variations for asymmetric standing/balance poses and prioritizes
        the expected active pose when within tolerance.
        
        Args:
            actual_angles: Dictionary of extracted joint angles.
            all_poses: List of all pose dictionaries containing their respective rules.
            confidence_threshold: Minimum match score to qualify as a known pose.
            expected_pose: Optional expected active pose from current session step.
            
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

            # Check direct orientation
            direct_score = cls._evaluate_rule_set(actual_angles, rules, mirrored=False)
            
            # Check mirrored orientation for asymmetric poses
            mirrored_score = cls._evaluate_rule_set(actual_angles, rules, mirrored=True)

            pose_score = max(direct_score, mirrored_score)

            is_better = False
            if pose_score > best_score + 1.5:
                is_better = True
            elif abs(pose_score - best_score) <= 1.5 and best_pose:
                # Prefer catalog poses with comprehensive rules over 2-rule transition steps
                curr_is_step = "step " in pose.get("name", "").lower()
                best_is_step = "step " in best_pose.get("name", "").lower()
                if best_is_step and not curr_is_step:
                    is_better = True
                elif len(rules) > len(best_pose.get("rules", [])):
                    is_better = True
            elif best_score < 0:
                is_better = True

            if is_better:
                best_score = pose_score
                best_pose = pose

        # If expected pose is provided, check if user's posture matches expected pose
        if expected_pose and expected_pose.get("rules"):
            exp_rules = expected_pose.get("rules", [])
            exp_direct = cls._evaluate_rule_set(actual_angles, exp_rules, mirrored=False)
            exp_mirror = cls._evaluate_rule_set(actual_angles, exp_rules, mirrored=True)
            exp_score = max(exp_direct, exp_mirror)

            # If expected pose meets strong alignment (>= 68%) and is within 8% of top match
            if exp_score >= 68.0 and (best_score - exp_score <= 8.0):
                best_score = exp_score
                best_pose = expected_pose
            elif exp_score >= 60.0 and best_pose and ("step " in best_pose.get("name", "").lower()):
                best_score = exp_score
                best_pose = expected_pose

        best_score = float(round(best_score, 1))

        if best_pose and best_score >= confidence_threshold:
            return best_pose.get("name", "Unknown Pose"), best_score, best_pose
        elif best_pose and best_score >= 50.0:
            return f"Transitioning / {best_pose.get('name')}", best_score, best_pose
        else:
            return "Unknown / Neutral Pose", max(0.0, best_score), None
