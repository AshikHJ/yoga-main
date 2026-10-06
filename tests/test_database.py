"""
Unit tests for Database operations, custom pose creation, and persistence.
"""

import pytest
from database.database import Database


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "yoga_test.db"
    return Database(db_path=db_file)


def test_user_creation_and_retrieval(temp_db):
    user_id = temp_db.create_user("John Doe", 30, "Intermediate", "Strength")
    assert user_id > 0

    user = temp_db.get_user_by_id(user_id)
    assert user is not None
    assert user["name"] == "John Doe"
    assert user["experience"] == "Intermediate"
    assert user["goal"] == "Strength"


def test_seed_poses_loaded(temp_db):
    poses = temp_db.get_all_poses()
    assert len(poses) >= 12
    # Verify rules are attached when querying by id
    pose1 = temp_db.get_pose_by_id(1)
    assert pose1 is not None
    assert len(pose1["rules"]) > 0


def test_add_custom_pose_and_template(temp_db):
    user_id = temp_db.create_user("Customizer", 25, "Beginner", "Balance")

    rules = [
        {"joint_name": "left_knee", "target_angle": 120.0, "tolerance": 15.0, "weight": 20.0},
        {"joint_name": "right_knee", "target_angle": 180.0, "tolerance": 15.0, "weight": 20.0},
    ]
    ref_data = {
        "angles": {"left_knee": 120.0, "right_knee": 180.0},
        "stability_variance": 2.1,
    }

    pose_id = temp_db.add_custom_pose(
        name="Custom Flamingo Pose",
        category="Balance",
        difficulty="Intermediate",
        goal="Balance",
        description="A flamingo balance stance.",
        benefits=["Balance", "Core"],
        instructions=["Stand on right leg", "Bend left knee 120°"],
        precautions="None",
        image_path=None,
        hold_duration=15,
        rules=rules,
        reference_data=ref_data,
        created_by=user_id,
    )

    assert pose_id > 0
    pose = temp_db.get_pose_by_id(pose_id)
    assert pose["name"] == "Custom Flamingo Pose"
    assert pose["is_custom"] == 1
    assert len(pose["rules"]) == 2

    # Template retrieval
    tpl = temp_db.get_custom_template(pose_id)
    assert tpl is not None
    assert tpl["angles"]["left_knee"] == 120.0


def test_session_saving_and_analytics(temp_db):
    user_id = temp_db.create_user("SessionUser", 32, "Beginner", "Flexibility")
    pose = temp_db.get_all_poses()[0]

    session_id = temp_db.save_practice_session(
        user_id=user_id,
        pose_id=pose["id"],
        duration=45,
        average_score=88.5,
        final_score=92.0,
        hold_duration=20,
        corrections_count=2,
        feedback_items=[{"body_part": "left_knee", "message": "Straighten left leg", "accuracy": 92.0}],
    )

    assert session_id > 0
    sessions = temp_db.get_user_sessions(user_id)
    assert len(sessions) == 1
    assert sessions[0]["final_score"] == 92.0

    stats = temp_db.get_user_stats(user_id)
    assert stats["total_sessions"] == 1
    assert stats["overall_avg_score"] == 88.5
    assert stats["best_score"] == 92.0
