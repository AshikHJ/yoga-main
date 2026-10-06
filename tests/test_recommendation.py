"""
Unit tests for PoseRecommender algorithm.
"""

import pytest
from database.database import Database
from recommendation.recommender import PoseRecommender


@pytest.fixture
def test_env(tmp_path):
    db_file = tmp_path / "test_yoga.db"
    db = Database(db_path=db_file)
    user_id = db.create_user("Alice", 28, "Beginner", "Flexibility")
    recommender = PoseRecommender(db=db)
    return db, recommender, user_id


def test_goal_based_recommendations(test_env):
    db, recommender, user_id = test_env
    recs = recommender.get_recommendations(user_id)

    assert "goal_based" in recs
    assert len(recs["goal_based"]) > 0
    # Primary recommendations should prioritize Flexibility
    for pose in recs["goal_based"]:
        assert pose.get("goal") == "Flexibility" or pose.get("category") == "Flexibility"


def test_weakness_targeted_practice_recommendation(test_env):
    db, recommender, user_id = test_env
    warrior = db.get_pose_by_name("Virabhadrasana II")

    # Record low score session
    db.save_practice_session(
        user_id=user_id,
        pose_id=warrior["id"],
        duration=30,
        average_score=62.0,
        final_score=65.0,
        hold_duration=5,
        corrections_count=6,
    )

    recs = recommender.get_recommendations(user_id)
    assert "practice_more" in recs
    assert any(p["name"] == "Virabhadrasana II" for p in recs["practice_more"])
