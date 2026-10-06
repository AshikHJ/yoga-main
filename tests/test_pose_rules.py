"""
Unit tests for PostureChecker and PoseClassifier.
"""

import pytest
from analysis.pose_classifier import PoseClassifier
from analysis.posture_checker import PostureChecker
from database.database import Database


@pytest.fixture
def db():
    return Database()


@pytest.fixture
def checker():
    return PostureChecker()


def test_tadasana_correct_evaluation(db, checker):
    tadasana = db.get_pose_by_name("Tadasana")
    assert tadasana is not None

    # Perfect Tadasana angles (standing tall, straight legs and arms)
    actual_angles = {
        "left_knee": 178.0,
        "right_knee": 178.0,
        "left_hip": 176.0,
        "right_hip": 176.0,
        "left_elbow": 175.0,
        "right_elbow": 175.0,
        "torso_vertical": 90.0,
    }

    result = checker.check_posture(tadasana, actual_angles, is_body_visible=True)
    assert result["is_valid"] is True
    assert result["overall_score"] >= 95.0
    assert result["score_level"] == "EXCELLENT"
    assert "Excellent posture" in result["primary_feedback"]


def test_warrior2_incorrect_knee_feedback(db, checker):
    warrior = db.get_pose_by_name("Virabhadrasana II")
    assert warrior is not None

    # Warrior II with straight front knee instead of bent 90°
    actual_angles = {
        "left_knee": 170.0,  # Should be 90°!
        "right_knee": 175.0,
        "left_shoulder": 90.0,
        "right_shoulder": 90.0,
        "left_elbow": 175.0,
        "right_elbow": 175.0,
        "torso_vertical": 90.0,
    }

    result = checker.check_posture(warrior, actual_angles, is_body_visible=True)
    assert result["overall_score"] < 85.0
    # Check that feedback specifically catches the left knee
    assert any("left knee" in fb.lower() for fb in result["all_feedback"])


def test_pose_classifier_distinguishes_tadasana_vs_warrior(db):
    all_poses = db.get_all_poses()
    assert len(all_poses) >= 10

    # Angles for Warrior II: front knee bent 90°, arms outstretched 90°
    warrior_angles = {
        "left_knee": 90.0,
        "right_knee": 175.0,
        "left_shoulder": 90.0,
        "right_shoulder": 90.0,
        "left_elbow": 175.0,
        "right_elbow": 175.0,
        "torso_vertical": 90.0,
    }

    detected_name, score, matched = PoseClassifier.identify_pose(warrior_angles, all_poses)
    assert "Virabhadrasana II" in detected_name or "Warrior" in detected_name
    assert score >= 75.0
