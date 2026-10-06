"""
Personalized Yoga Pose Recommendation Engine.
Combines user fitness goals, experience level, past performance scores,
and weakness-targeting algorithms to generate dynamic, tailored pose recommendations.
"""

from typing import Any, Dict, List, Optional
from database.database import Database


class PoseRecommender:
    """Calculates personalized yoga recommendations based on user profile and practice history."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def get_recommendations(
        self,
        user_id: int,
        limit: int = 4
    ) -> Dict[str, Any]:
        """
        Generates full recommendation sections for the user:
        - daily_routine: Balanced 3-4 pose routine
        - goal_based: Poses directly aligning with user's selected fitness goal
        - practice_more: Poses with lower scores needing posture refinement
        - next_level: Higher difficulty challenges if eligible
        """
        user = self.db.get_user_by_id(user_id)
        all_poses = self.db.get_all_poses()

        if not user or not all_poses:
            # Fallback for guest or empty user
            return {
                "daily_routine": all_poses[:limit],
                "goal_based": all_poses[:limit],
                "practice_more": [],
                "next_level": [],
                "insights": ["Complete your first practice session to unlock personalized AI insights!"]
            }

        user_goal = user.get("goal", "General Fitness")
        user_level = user.get("experience", "Beginner")

        # Fetch user performance breakdown
        history_stats = self.db.get_pose_performance_breakdown(user_id)
        history_map = {h["pose_name"]: h for h in history_stats}

        # 1. Goal-Based Recommendations
        goal_poses = [
            p for p in all_poses
            if p.get("goal", "").lower() == user_goal.lower()
            or p.get("category", "").lower() == user_goal.lower()
        ]
        if not goal_poses:
            goal_poses = all_poses

        # Filter roughly by difficulty preference
        if user_level == "Beginner":
            filtered_goal = [p for p in goal_poses if p.get("difficulty") in ["Beginner", "Intermediate"]]
        elif user_level == "Intermediate":
            filtered_goal = [p for p in goal_poses if p.get("difficulty") in ["Intermediate", "Advanced", "Beginner"]]
        else:
            filtered_goal = goal_poses

        if not filtered_goal:
            filtered_goal = goal_poses

        # 2. Practice More (Weakness-Targeted)
        practice_more_poses: List[Dict[str, Any]] = []
        insights: List[str] = []

        for h in history_stats:
            if h["avg_score"] < 80.0:
                pose_dict = self.db.get_pose_by_name(h["pose_name"])
                if pose_dict:
                    pose_copy = dict(pose_dict)
                    pose_copy["user_avg_score"] = h["avg_score"]
                    practice_more_poses.append(pose_copy)

        if practice_more_poses:
            lowest = practice_more_poses[0]
            insights.append(
                f"Your average score on {lowest['name']} is {lowest['user_avg_score']}%. "
                "Extra focus on joint alignment is recommended."
            )
        else:
            insights.append(f"Great consistency! Tailoring poses aligned with your goal: {user_goal}.")

        # 3. Next Level Challenges
        next_level_poses: List[Dict[str, Any]] = []
        high_scoring_sessions = [h for h in history_stats if h["avg_score"] >= 88.0]

        if len(high_scoring_sessions) >= 2 or user_level in ["Intermediate", "Advanced"]:
            target_diff = "Advanced" if user_level == "Intermediate" else "Intermediate"
            next_level_poses = [p for p in all_poses if p.get("difficulty") == target_diff]
            if next_level_poses:
                insights.append(f"Mastery detected! Try expanding your practice with {target_diff} poses.")

        # 4. Daily Routine Sequencing (Warmup, Peak, Cooldown)
        daily_routine = self._build_daily_routine(all_poses, user_goal, user_level)

        return {
            "daily_routine": daily_routine[:limit],
            "goal_based": filtered_goal[:limit],
            "practice_more": practice_more_poses[:limit],
            "next_level": next_level_poses[:limit],
            "insights": insights,
        }

    def _build_daily_routine(
        self,
        all_poses: List[Dict[str, Any]],
        goal: str,
        level: str
    ) -> List[Dict[str, Any]]:
        """Constructs a balanced routine: 1 Warmup, 2 Core, 1 Cooldown."""
        warmups = [p for p in all_poses if p.get("name") in ["Tadasana", "Balasana", "Sukhasana"]]
        standing_core = [p for p in all_poses if p.get("category") in ["Standing", "Strength", "Balance"]]
        flexibility_core = [p for p in all_poses if p.get("category") in ["Flexibility"]]
        cooldowns = [p for p in all_poses if p.get("category") in ["Relaxation", "Sitting"] or p.get("name") == "Balasana"]

        routine: List[Dict[str, Any]] = []

        # 1. Warm-up
        if warmups:
            routine.append(warmups[0])
        elif all_poses:
            routine.append(all_poses[0])

        # 2. Peak Poses
        if standing_core:
            for p in standing_core:
                if p not in routine:
                    routine.append(p)
                    break

        if flexibility_core:
            for p in flexibility_core:
                if p not in routine:
                    routine.append(p)
                    break

        # 3. Cooldown
        if cooldowns:
            for p in cooldowns:
                if p not in routine:
                    routine.append(p)
                    break

        # Fallback if routine is short
        for p in all_poses:
            if len(routine) >= 4:
                break
            if p not in routine:
                routine.append(p)

        return routine
