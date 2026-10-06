"""
Unit tests for ScoreCalculator and qualitative posture tiers.
"""

import pytest
from analysis.score_calculator import ScoreCalculator
from config import settings


def test_joint_score_exact_target():
    # Exact match: actual = 90.0, target = 90.0 -> 100.0 score
    score = ScoreCalculator.calculate_joint_score(90.0, 90.0, tolerance=15.0)
    assert score == 100.0


def test_joint_score_within_tolerance():
    # Half tolerance deviation: actual = 97.5, target = 90.0, tol = 15.0 -> ~95.0 score
    score = ScoreCalculator.calculate_joint_score(97.5, 90.0, tolerance=15.0)
    assert pytest.approx(score, 0.1) == 95.0


def test_joint_score_at_tolerance_boundary():
    # At exact boundary: actual = 105.0, target = 90.0, tol = 15.0 -> 90.0 score
    score = ScoreCalculator.calculate_joint_score(105.0, 90.0, tolerance=15.0)
    assert pytest.approx(score, 0.1) == 90.0


def test_joint_score_beyond_tolerance_decay():
    # Beyond tolerance: actual = 135.0 (45° deviation, 30° excess) -> drops below 50.0
    score = ScoreCalculator.calculate_joint_score(135.0, 90.0, tolerance=15.0, max_penalty_deviation=45.0)
    assert 0.0 <= score < 90.0
    assert pytest.approx(score, 1.0) == 30.0


def test_overall_weighted_score():
    joint_results = [
        {"joint_name": "left_knee", "actual_angle": 90.0, "target_angle": 90.0, "tolerance": 15.0, "weight": 25.0},
        {"joint_name": "right_knee", "actual_angle": 175.0, "target_angle": 175.0, "tolerance": 15.0, "weight": 25.0},
        {"joint_name": "left_arm", "actual_angle": 90.0, "target_angle": 90.0, "tolerance": 15.0, "weight": 25.0},
        {"joint_name": "right_arm", "actual_angle": 90.0, "target_angle": 90.0, "tolerance": 15.0, "weight": 25.0},
    ]
    overall, level_key, level_info = ScoreCalculator.calculate_overall_score(joint_results)
    assert overall == 100.0
    assert level_key == "EXCELLENT"
    assert level_info["label"] == "EXCELLENT"


def test_score_level_boundaries():
    assert ScoreCalculator.get_score_level(95.0)[0] == "EXCELLENT"
    assert ScoreCalculator.get_score_level(85.0)[0] == "GOOD"
    assert ScoreCalculator.get_score_level(75.0)[0] == "NEEDS_IMPROVEMENT"
    assert ScoreCalculator.get_score_level(50.0)[0] == "INCORRECT"
