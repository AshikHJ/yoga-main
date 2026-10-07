"""
Automated unit & integration tests for the KI.AI Computer Vision Pipeline.
Validates:
1. Body visibility and tracking states (NO_PERSON, PARTIAL_BODY, GOOD_TRACKING)
2. Exact separation of expected_pose vs detected_pose
3. WRONG_POSE detection with score penalization
4. CORRECT posture verification and valid hold qualification
5. ADJUST posture evaluation with targeted incorrect joint highlighting
6. Session frame evaluation endpoint (/api/session/evaluate_frame)
7. Bilateral symmetry and mirrored pose evaluation
"""

import json
import pytest
from web_app import app
from analysis.angle_calculator import AngleCalculator
from analysis.pose_classifier import PoseClassifier
from analysis.posture_checker import PostureChecker
from database.database import Database


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def db_instance():
    return Database()


def create_sample_landmarks(straight_knee=True, bend_left_knee=False, visibility=0.99):
    """Generates standard MediaPipe landmarks for a standing figure."""
    l_knee_x = 0.41 if bend_left_knee else 0.46
    l_knee_y = 0.74 if bend_left_knee else 0.75

    return {
        "NOSE": {"x": 0.50, "y": 0.10, "z": 0.0, "visibility": visibility},
        "LEFT_SHOULDER": {"x": 0.45, "y": 0.25, "z": 0.0, "visibility": visibility},
        "RIGHT_SHOULDER": {"x": 0.55, "y": 0.25, "z": 0.0, "visibility": visibility},
        "LEFT_ELBOW": {"x": 0.44, "y": 0.40, "z": 0.0, "visibility": visibility},
        "RIGHT_ELBOW": {"x": 0.56, "y": 0.40, "z": 0.0, "visibility": visibility},
        "LEFT_WRIST": {"x": 0.43, "y": 0.55, "z": 0.0, "visibility": visibility},
        "RIGHT_WRIST": {"x": 0.57, "y": 0.55, "z": 0.0, "visibility": visibility},
        "LEFT_HIP": {"x": 0.46, "y": 0.55, "z": 0.0, "visibility": visibility},
        "RIGHT_HIP": {"x": 0.54, "y": 0.55, "z": 0.0, "visibility": visibility},
        "LEFT_KNEE": {"x": l_knee_x, "y": l_knee_y, "z": 0.0, "visibility": visibility},
        "RIGHT_KNEE": {"x": 0.54, "y": 0.75, "z": 0.0, "visibility": visibility},
        "LEFT_ANKLE": {"x": 0.46, "y": 0.95, "z": 0.0, "visibility": visibility},
        "RIGHT_ANKLE": {"x": 0.54, "y": 0.95, "z": 0.0, "visibility": visibility},
    }


def test_tracking_state_no_person(client):
    """When landmarks are absent or low visibility, status is NO_PERSON and WAITING."""
    low_vis = create_sample_landmarks(visibility=0.1)
    res = client.post("/api/analyze_posture", json={"landmarks": low_vis, "pose_id": 1})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["tracking_state"] == "NO_PERSON"
    assert not data["is_body_visible"]
    assert data["pose_status"] == "WAITING"
    assert not data["is_hold_valid"]


def test_tracking_state_partial_body(client):
    """When upper body is visible but lower body is cut off, returns PARTIAL_BODY."""
    lm = create_sample_landmarks(visibility=0.95)
    # Hide lower limbs
    for k in ["LEFT_KNEE", "RIGHT_KNEE", "LEFT_ANKLE", "RIGHT_ANKLE"]:
        lm[k]["visibility"] = 0.1

    res = client.post("/api/analyze_posture", json={"landmarks": lm, "pose_id": 1})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["tracking_state"] == "PARTIAL_BODY"
    assert not data["is_body_visible"]
    assert "Move back" in data["primary_feedback"] or "full body" in data["primary_feedback"].lower()


def test_tracking_state_good_tracking(client):
    """When both upper and lower body keypoints are visible, returns GOOD_TRACKING."""
    lm = create_sample_landmarks(visibility=0.95)
    res = client.post("/api/analyze_posture", json={"landmarks": lm, "pose_id": 1})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["tracking_state"] == "GOOD_TRACKING"
    assert data["is_body_visible"]


def test_correct_posture_and_valid_hold(client):
    """When user is in correct expected posture, verify CORRECT status and valid hold."""
    lm = create_sample_landmarks(straight_knee=True, bend_left_knee=False, visibility=0.98)
    res = client.post("/api/analyze_posture", json={"landmarks": lm, "pose_id": 1})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["pose_matched"] is True
    assert data["pose_status"] == "CORRECT"
    assert data["right_wrong_status"] == "RIGHT"
    assert data["is_hold_valid"] is True
    assert data["overall_score"] >= 78.0
    assert len(data["critical_incorrect_joints"]) == 0


def test_wrong_pose_detection_and_penalty(client):
    """
    When user is performing Tadasana (straight standing) but the expected pose is
    Vrikshasana (Tree Pose, requiring a bent leg), system must identify WRONG_POSE,
    cap overall_score <= 45%, and pause hold.
    """
    lm = create_sample_landmarks(straight_knee=True, bend_left_knee=False, visibility=0.98)
    # Pose ID 3 is Vrikshasana (Tree Pose)
    res = client.post("/api/analyze_posture", json={"landmarks": lm, "pose_id": 3})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    
    # Expected vs detected separation
    assert "Vrikshasana" in data["expected_pose_name"] or "Tree" in data["expected_pose_name"]
    assert data["pose_matched"] is False
    assert data["pose_status"] == "WRONG_POSE"
    assert data["right_wrong_status"] == "WRONG"
    assert data["overall_score"] <= 45.0
    assert data["is_hold_valid"] is False
    assert "Tree" in data["primary_feedback"] or "Vrikshasana" in data["primary_feedback"] or "looks like" in data["primary_feedback"].lower()


def test_adjust_posture_and_incorrect_joints(client):
    """
    When user attempts Tadasana but bends their left knee slightly beyond tolerance,
    verify ADJUST status and that left_knee is listed in incorrect_joints.
    """
    lm = create_sample_landmarks(bend_left_knee=True, visibility=0.98)
    res = client.post("/api/analyze_posture", json={"landmarks": lm, "pose_id": 1})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["pose_status"] == "ADJUST"
    assert data["right_wrong_status"] == "ADJUST"
    assert not data["is_hold_valid"]
    assert any("knee" in j.lower() for j in data["incorrect_joints"])


def test_session_evaluate_frame(client):
    """Verifies /api/session/evaluate_frame endpoint returns full evaluation schema."""
    lm = create_sample_landmarks(visibility=0.95)
    payload = {
        "landmarks": lm,
        "exercise": {
            "name": "Tadasana",
            "target_pose_id": 1,
            "hold_seconds": 20
        }
    }
    res = client.post("/api/session/evaluate_frame", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "tracking_state" in data
    assert "is_body_visible" in data
    assert "detected_pose" in data
    assert "expected_pose_name" in data
    assert "is_hold_valid" in data
    assert "incorrect_joints" in data


def test_bilateral_symmetry_and_mirroring(db_instance):
    """
    Verifies bilateral symmetry handling in PoseClassifier & PostureChecker
    for mirrored left/right postures.
    """
    all_poses = db_instance.get_all_poses()
    vrikshasana = next((p for p in all_poses if "vrikshasana" in p["name"].lower()), None)
    if not vrikshasana:
        pytest.skip("Vrikshasana not in test database")

    # Angles with left knee bent (standard)
    angles_standard = {
        "left_knee": 50.0,
        "right_knee": 178.0,
        "left_elbow": 55.0,
        "right_elbow": 55.0,
        "torso_vertical": 90.0,
    }
    checker = PostureChecker()
    res_standard = checker.check_posture(vrikshasana, angles_standard)

    # Angles with right knee bent (mirrored)
    angles_mirrored = {
        "left_knee": 178.0,
        "right_knee": 50.0,
        "left_elbow": 55.0,
        "right_elbow": 55.0,
        "torso_vertical": 90.0,
    }
    res_mirrored = checker.check_posture(vrikshasana, angles_mirrored)

    # Both orientations should receive high scores thanks to bilateral symmetry
    assert res_standard["overall_score"] >= 75.0
    assert res_mirrored["overall_score"] >= 75.0
