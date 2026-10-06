"""
Accuracy Score Calculation Module for AI Yoga Assistant.
Implements weighted joint scoring, tolerance decay curves, and qualitative level classifications.
"""

from typing import Any, Dict, List, Tuple
from config import settings


class ScoreCalculator:
    """Calculates granular and overall accuracy scores for yoga postures."""

    @classmethod
    def calculate_joint_score(
        cls,
        actual_angle: float,
        target_angle: float,
        tolerance: float = 15.0,
        max_penalty_deviation: float = 45.0,
    ) -> float:
        """
        Calculates an individual joint's accuracy score [0.0 - 100.0].
        
        Args:
            actual_angle: Measured angle in degrees.
            target_angle: Desired template angle in degrees.
            tolerance: Allowed margin of error for full/near-full score.
            max_penalty_deviation: Deviation beyond tolerance at which score drops to 0.
            
        Returns:
            Score from 0.0 to 100.0.
        """
        deviation = abs(actual_angle - target_angle)

        if deviation <= tolerance:
            # Within tolerance: Score between 90% and 100%
            ratio = deviation / max(tolerance, 1.0)
            score = 100.0 - (ratio * 10.0)
        else:
            # Beyond tolerance: Linear decay from 90% down to 0%
            excess = deviation - tolerance
            decay_factor = excess / max(max_penalty_deviation, 1.0)
            score = max(0.0, 90.0 - (decay_factor * 90.0))

        return float(round(score, 2))

    @classmethod
    def calculate_overall_score(
        cls,
        joint_results: List[Dict[str, Any]]
    ) -> Tuple[float, str, Dict[str, Any]]:
        """
        Calculates the weighted aggregate posture score and qualitative level.
        
        Args:
            joint_results: List of dicts, each with 'score' (or 'actual_angle', 'target_angle', 'tolerance')
                           and 'weight'.
                           
        Returns:
            Tuple of:
                - overall_score (float 0.0 - 100.0)
                - level_key (e.g. 'EXCELLENT', 'GOOD', 'NEEDS_IMPROVEMENT', 'INCORRECT')
                - level_info (dict with label, color, icon, etc.)
        """
        if not joint_results:
            return 0.0, "INCORRECT", settings.SCORE_LEVELS["INCORRECT"]

        total_weighted_score = 0.0
        total_weight = 0.0

        for item in joint_results:
            score = item.get("score")
            if score is None:
                actual = float(item.get("actual_angle", 0.0))
                target = float(item.get("target_angle", 0.0))
                tol = float(item.get("tolerance", settings.DEFAULT_TOLERANCE_DEGREES))
                score = cls.calculate_joint_score(actual, target, tol)

            weight = float(item.get("weight", 10.0))
            total_weighted_score += score * weight
            total_weight += weight

        if total_weight <= 0:
            final_score = 0.0
        else:
            final_score = total_weighted_score / total_weight

        final_score = float(round(max(0.0, min(100.0, final_score)), 1))
        level_key, level_info = cls.get_score_level(final_score)

        return final_score, level_key, level_info

    @staticmethod
    def get_score_level(score: float) -> Tuple[str, Dict[str, Any]]:
        """Maps a numerical score to qualitative level metadata."""
        if score >= settings.SCORE_EXCELLENT_THRESHOLD:
            return "EXCELLENT", settings.SCORE_LEVELS["EXCELLENT"]
        elif score >= settings.SCORE_GOOD_THRESHOLD:
            return "GOOD", settings.SCORE_LEVELS["GOOD"]
        elif score >= settings.SCORE_NEEDS_IMPROVEMENT_THRESHOLD:
            return "NEEDS_IMPROVEMENT", settings.SCORE_LEVELS["NEEDS_IMPROVEMENT"]
        else:
            return "INCORRECT", settings.SCORE_LEVELS["INCORRECT"]
