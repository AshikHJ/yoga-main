"""
Session Planner Engine for KI.AI — AI-Guided Yoga Learning System.
Generates progressive, personalized multi-exercise yoga practice roadmaps
tailored to user level, goal, practice time, weakest joints, and past performance.
"""

import logging
import random
from typing import Any, Dict, List, Optional
from database.database import Database

logger = logging.getLogger(__name__)


class SessionPlanner:
    """Intelligent Yoga Session Generator & Program Progression Engine."""

    LEVEL_TITLES = {
        "Beginner": {"name": "Foundation", "subtitle": "Build your body awareness and learn the fundamentals."},
        "Intermediate": {"name": "Progress", "subtitle": "Build strength, flexibility, balance and control."},
        "Advanced": {"name": "Mastery", "subtitle": "Advanced sequences for strength, mobility, balance and precision."},
    }

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def generate_session(
        self,
        user_id: int = 1,
        duration_minutes: int = 20,
        goal: str = "General Fitness",
        level: str = "Beginner",
        focus_area: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates a complete structured yoga learning session roadmap.
        
        Args:
            user_id: User integer ID.
            duration_minutes: Available practice time in minutes (e.g. 10, 15, 20, 30).
            goal: Fitness/wellness goal (e.g. Flexibility, Strength, Balance, Posture Improvement, Relaxation).
            level: User experience level ('Beginner', 'Intermediate', 'Advanced').
            focus_area: Optional focus ('Hip & Spine Mobility', 'Core & Balance', 'Full Body Alignment').
            
        Returns:
            Structured session plan dictionary containing roadmap exercises, hold times, and instructions.
        """
        user = self.db.get_user_by_id(user_id) or {}
        stats = self.db.get_user_stats(user_id) or {}
        user_goal = goal or user.get("goal", "General Fitness")
        user_level = level or user.get("experience", "Beginner")

        # Map experience string to program level name
        if "adv" in user_level.lower():
            level_key = "Advanced"
        elif "inter" in user_level.lower():
            level_key = "Intermediate"
        else:
            level_key = "Beginner"

        program_info = self.LEVEL_TITLES[level_key]
        all_poses = self.db.get_all_poses()
        surya_poses = self.db.get_surya_namaskar_poses()

        # Build exercise list based on program level and duration
        exercises = self._assemble_roadmap_exercises(
            level_key=level_key,
            goal=user_goal,
            duration=duration_minutes,
            all_poses=all_poses,
            surya_poses=surya_poses,
            stats=stats,
        )

        focus = focus_area or self._determine_focus_area(user_goal, level_key)
        total_exercises = len(exercises)
        total_seconds = sum(e.get("duration", e.get("duration_seconds", 30)) for e in exercises)
        plan_id = f"plan_{user_id}_{level_key.lower()}_{duration_minutes}m"

        return {
            "id": plan_id,
            "user_id": user_id,
            "title": f"Today's {program_info['name']} Session",
            "program_name": program_info["name"],
            "program_subtitle": program_info["subtitle"],
            "level": level_key,
            "goal": user_goal,
            "focus": focus,
            "focus_area": focus,
            "duration_minutes": duration_minutes,
            "target_duration_minutes": duration_minutes,
            "estimated_duration": total_seconds,
            "estimated_duration_seconds": total_seconds,
            "difficulty": level_key,
            "reason": f"Customized for your {user_goal} goal and {level_key} progression.",
            "exercises": exercises,
            "roadmap": exercises,
            "total_exercises": total_exercises,
            "user_stats_summary": {
                "avg_score": stats.get("avg_score", 0.0),
                "completed_sessions": stats.get("total_sessions", 0),
                "streak_days": min(stats.get("total_sessions", 0), 7),
            },
        }

    def _determine_focus_area(self, goal: str, level: str) -> str:
        """Determines daily focus area based on goal and level."""
        goal_lower = goal.lower()
        if "flex" in goal_lower:
            return "Hamstrings & Spine Mobility"
        elif "strength" in goal_lower:
            return "Core & Lower Body Endurance"
        elif "balan" in goal_lower:
            return "Proprioception & Ankle Alignment"
        elif "posture" in goal_lower:
            return "Shoulder Retraction & Spinal Extension"
        elif "relax" in goal_lower:
            return "Parasympathetic Decompression"
        return "Full Body Posture Alignment"

    def _assemble_roadmap_exercises(
        self,
        level_key: str,
        goal: str,
        duration: int,
        all_poses: List[Dict[str, Any]],
        surya_poses: List[Dict[str, Any]],
        stats: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Assembles ordered step-by-step roadmap items for a session."""
        roadmap = []
        step_id = 1

        # 1. BREATHING & INTRO
        roadmap.append({
            "step": step_id,
            "type": "breathing",
            "pose_id": 0,
            "name": "Pranayama & Centering",
            "sanskrit_name": "Pranayama",
            "duration": 45,
            "duration_seconds": 45,
            "hold_seconds": 45,
            "rest": 5,
            "instruction": "Establish steady, rhythmic diaphragmatic breathing. Inhale deeply through nose, expand ribcage, and release slowly.",
            "breathing": "Inhale 4s — Hold 2s — Exhale 6s",
            "breathing_cue": "Inhale 4s — Hold 2s — Exhale 6s",
            "difficulty": "Beginner",
            "purpose": "Centering mind and preparing lungs for yoga flow",
            "target_angles": {},
            "safety_notes": ["Breathe naturally without straining"],
            "requires_camera": False,
        })
        step_id += 1

        # 2. WARM-UP STRETCH (Unless ultra-short 10m session)
        if duration >= 15:
            roadmap.append({
                "step": step_id,
                "type": "warmup",
                "pose_id": 0,
                "name": "Gentle Spinal & Shoulder Warm-up",
                "sanskrit_name": "Sukhasana Stretch",
                "duration": 50,
                "duration_seconds": 50,
                "hold_seconds": 50,
                "rest": 5,
                "instruction": "Rotate shoulders backwards, lengthen spine upward, and release neck tension before standing poses.",
                "breathing": "Continuous smooth breaths into chest",
                "breathing_cue": "Continuous smooth breaths into chest",
                "difficulty": "Beginner",
                "purpose": "Spine decompression and shoulder mobility",
                "target_angles": {},
                "safety_notes": ["Move gently without forcing joint range"],
                "requires_camera": False,
            })
            step_id += 1

        # Lookup pose helper
        pose_dict_by_name = {p["name"].lower(): p for p in all_poses}

        def find_pose(names: List[str]) -> Optional[Dict[str, Any]]:
            for n in names:
                for k, v in pose_dict_by_name.items():
                    if n.lower() in k:
                        return v
            return all_poses[0] if all_poses else None

        # 3. LEVEL SPECIFIC POSES & SEQUENCING
        if level_key == "Beginner":
            tadasana = find_pose(["mountain", "tadasana"])
            vrikshasana = find_pose(["tree", "vrikshasana"])
            balasana = find_pose(["child", "balasana"])

            if tadasana:
                roadmap.append(self._pose_to_exercise(step_id, tadasana, hold_seconds=20, cue="Ground both feet evenly, pull belly inward, stack shoulders over hips."))
                step_id += 1

            if vrikshasana:
                roadmap.append(self._pose_to_exercise(step_id, vrikshasana, hold_seconds=25, cue="Fix gaze on a single point ahead. Place sole of foot firmly on inner thigh or calf."))
                step_id += 1

            # Surya Namaskar Flow (Beginner flow)
            if surya_poses and duration >= 15:
                roadmap.append({
                    "step": step_id,
                    "type": "flow",
                    "pose_id": 101,
                    "name": "Surya Namaskar (Beginner Flow)",
                    "sanskrit_name": "Sun Salutation",
                    "duration": 90,
                    "duration_seconds": 90,
                    "hold_seconds": 30,
                    "rest": 10,
                    "instruction": "Sequential 12-step sun salutation flow to harmonize breath with movement.",
                    "breathing": "Exhale into fold, inhale into extension",
                    "breathing_cue": "Exhale into fold, inhale into extension",
                    "difficulty": "Beginner",
                    "purpose": "Full-body warm-up and cardiovascular rhythm",
                    "target_angles": {},
                    "safety_notes": ["Bend knees slightly in forward folds if hamstrings are tight"],
                    "requires_camera": True,
                    "surya_steps": surya_poses[:6],
                })
                step_id += 1

            if balasana:
                roadmap.append(self._pose_to_exercise(step_id, balasana, hold_seconds=30, cue="Lower hips onto heels, stretch arms forward, rest forehead on mat."))
                step_id += 1

        elif level_key == "Intermediate":
            warrior = find_pose(["warrior ii", "virabhadrasana ii"])
            triangle = find_pose(["triangle", "trikonasana"])
            chair = find_pose(["chair", "utkatasana"])
            dog = find_pose(["downward", "adho mukha"])
            cobra = find_pose(["cobra", "bhujangasana"])
            bridge = find_pose(["bridge", "setu bandhasana"])

            # Surya Namaskar Flow
            if surya_poses and duration >= 15:
                roadmap.append({
                    "step": step_id,
                    "type": "flow",
                    "pose_id": 102,
                    "name": "Surya Namaskar Full Sequence",
                    "sanskrit_name": "Sun Salutation A",
                    "duration": 120,
                    "duration_seconds": 120,
                    "hold_seconds": 45,
                    "rest": 10,
                    "instruction": "Full 12-step rhythm for cardiovascular warmth and spinal articulation.",
                    "breathing": "Dynamic Vinyasa breathing",
                    "breathing_cue": "Dynamic Vinyasa breathing",
                    "difficulty": "Intermediate",
                    "purpose": "Full-body endurance and dynamic flexibility",
                    "target_angles": {},
                    "safety_notes": ["Protect lower back by engaging core throughout transitions"],
                    "requires_camera": True,
                    "surya_steps": surya_poses,
                })
                step_id += 1

            # Select poses based on duration
            poses_to_add = [warrior, triangle, dog] if duration <= 15 else [warrior, triangle, chair, dog, cobra, bridge]
            for p in poses_to_add:
                if p:
                    roadmap.append(self._pose_to_exercise(step_id, p, hold_seconds=25))
                    step_id += 1

        else:
            # Mastery sequence
            warrior = find_pose(["warrior ii", "virabhadrasana ii"])
            triangle = find_pose(["triangle", "trikonasana"])
            dancer = find_pose(["dancer", "natarajasana"])
            bow = find_pose(["bow", "dhanurasana"])
            dog = find_pose(["downward", "adho mukha"])
            bridge = find_pose(["bridge", "setu bandhasana"])

            # Safety Warning step
            roadmap.append({
                "step": step_id,
                "type": "safety_check",
                "pose_id": 0,
                "name": "Mastery Readiness & Safety Check",
                "sanskrit_name": "Ahimsā Safety",
                "duration": 15,
                "duration_seconds": 15,
                "hold_seconds": 15,
                "rest": 0,
                "instruction": "Advanced postures require warm spine & shoulders. Never force joint range beyond comfortable control.",
                "breathing": "Steady focus",
                "breathing_cue": "Steady focus",
                "difficulty": "Advanced",
                "purpose": "Safety readiness verification",
                "target_angles": {},
                "safety_notes": ["Do not attempt deep backbends if experiencing spine stiffness"],
                "requires_camera": False,
            })
            step_id += 1

            mastery_poses = [warrior, triangle, dancer, bow, dog, bridge]
            for p in mastery_poses:
                if p:
                    roadmap.append(self._pose_to_exercise(step_id, p, hold_seconds=30))
                    step_id += 1

        # COOLDOWN & DECOMPRESSION
        roadmap.append({
            "step": step_id,
            "type": "cooldown",
            "pose_id": 0,
            "name": "Savasana & Decompression",
            "sanskrit_name": "Śavāsana",
            "duration": 60,
            "duration_seconds": 60,
            "hold_seconds": 60,
            "rest": 0,
            "instruction": "Lie fully relaxed on your back, allow heart rate to recover, and integrate the benefits of today's session.",
            "breathing": "Natural effortless breath",
            "breathing_cue": "Natural effortless breath",
            "difficulty": "Beginner",
            "purpose": "Parasympathetic recovery and nervous system integration",
            "target_angles": {},
            "safety_notes": ["Relax completely and release all tension"],
            "requires_camera": False,
        })

        return roadmap

    def _pose_to_exercise(self, step: int, pose: Dict[str, Any], hold_seconds: int = 20, cue: str = "") -> Dict[str, Any]:
        """Converts database pose dict to structured roadmap exercise item matching spec."""
        pose_name = pose.get("name", "Yoga Pose")
        clean_name = "".join(c if c.isalnum() else "_" for c in pose_name.lower())
        fig = pose.get("figure_path") or f"assets/pose_figures/{clean_name}.svg"
        img = pose.get("image_path") or f"assets/images/yoga/{clean_name}.png"

        rules = pose.get("rules", [])
        target_angles = {r["joint_name"]: r["target_angle"] for r in rules if "joint_name" in r and "target_angle" in r}
        
        ins_list = pose.get("instructions", [])
        instruction_text = ins_list[0] if (isinstance(ins_list, list) and ins_list) else (pose.get("description") or "Follow visual posture guidance.")
        
        safety = [pose.get("precautions")] if pose.get("precautions") else ["Practice within comfortable range of motion."]

        return {
            "step": step,
            "type": "pose",
            "pose_id": pose.get("id"),
            "name": pose.get("name"),
            "sanskrit_name": pose.get("sanskrit_name", ""),
            "duration": hold_seconds + 10,
            "duration_seconds": hold_seconds + 10,
            "hold_seconds": hold_seconds,
            "rest": 10,
            "instruction": instruction_text,
            "breathing": cue or f"Breathe deeply and smoothly throughout {pose.get('name')}.",
            "breathing_cue": cue or f"Breathe deeply while holding {pose.get('name')}.",
            "difficulty": pose.get("difficulty", "Beginner"),
            "purpose": f"Develop {pose.get('goal', 'balance')} and joint alignment stability.",
            "target_angles": target_angles,
            "safety_notes": safety,
            "category": pose.get("category", "Standing"),
            "description": pose.get("description", ""),
            "benefits": pose.get("benefits", []),
            "instructions": pose.get("instructions", []),
            "precautions": pose.get("precautions", ""),
            "figure_path": fig,
            "image_path": img,
            "requires_camera": True,
            "rules": rules,
        }

    def evaluate_program_unlock(self, user_id: int) -> Dict[str, Any]:
        """Evaluates whether user has unlocked Foundation -> Progress -> Mastery programs."""
        stats = self.db.get_user_stats(user_id)
        avg_score = stats.get("avg_score", 0.0)
        total_sessions = stats.get("total_sessions", 0)

        unlocked_levels = ["Beginner"] # Foundation unlocked by default

        if total_sessions >= 3 and avg_score >= 75.0:
            unlocked_levels.append("Intermediate") # Progress unlocked
        
        if total_sessions >= 10 and avg_score >= 82.0:
            unlocked_levels.append("Advanced") # Mastery unlocked

        next_level = "Intermediate" if "Intermediate" not in unlocked_levels else ("Advanced" if "Advanced" not in unlocked_levels else "Mastery Achieved")
        req_sessions = 3 if "Intermediate" not in unlocked_levels else 10

        return {
            "unlocked_levels": unlocked_levels,
            "foundation_unlocked": True,
            "progress_unlocked": "Intermediate" in unlocked_levels,
            "mastery_unlocked": "Advanced" in unlocked_levels,
            "avg_score": avg_score,
            "total_sessions": total_sessions,
            "readiness_message": f"Complete {max(0, req_sessions - total_sessions)} more sessions with score ≥75% to unlock next level." if "Advanced" not in unlocked_levels else "You have unlocked all Mastery levels!"
        }
