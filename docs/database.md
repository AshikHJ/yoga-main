# Database Design and Schema Documentation

The application uses an embedded **SQLite 3** relational database (`database/yoga.db`) designed for offline performance, ACID compliance, and foreign key integrity.

---

## 1. Entity-Relationship (ER) Diagram

```
+-------------------+             +-----------------------+
|       users       | 1         * |         poses         |
+-------------------+-------------+-----------------------+
| id (PK)           |             | id (PK)               |
| name              |             | name (UNIQUE)         |
| age               |             | sanskrit_name         |
| experience        |             | category              |
| goal              |             | difficulty            |
| created_at        |             | goal                  |
+---------+---------+             | description           |
          |                       | benefits (JSON)       |
          | 1                     | instructions (JSON)   |
          |                       | precautions           |
          |                       | image_path            |
          |                       | hold_duration         |
          |                       | is_custom             |
          |                       | created_by (FK)       |
          |                       | created_at            |
          |                       +-----------+-----------+
          |                                   | 1
          |                                   |
          | 1                                 | *
+---------+-------------+         +-----------+-----------+
|   practice_sessions   | *     1 |      pose_rules       |
+-----------------------+---------+-----------------------+
| id (PK)               |         | id (PK)               |
| user_id (FK)          |         | pose_id (FK)          |
| pose_id (FK)          |         | joint_name            |
| start_time            |         | target_angle          |
| end_time              |         | min_angle             |
| duration              |         | max_angle             |
| average_score         |         | tolerance             |
| final_score           |         | weight                |
| hold_duration         |         | feedback_message      |
| corrections_count     |         +-----------------------+
| created_at            |
+-----------+-----------+
            | 1
            |
            | *
+-----------+-----------+         +-----------------------+
|       feedback        |         | custom_pose_templates |
+-----------------------+         +-----------------------+
| id (PK)               |         | id (PK)               |
| session_id (FK)       |         | pose_id (FK, UNIQUE)  |
| body_part             |         | reference_data (JSON) |
| message               |         | created_at            |
| accuracy              |         +-----------------------+
| created_at            |
+-----------------------+
```

---

## 2. Table Specifications

### `users`
Stores user profile information, experience levels, and fitness goals.
- `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `name` (TEXT, NOT NULL)
- `age` (INTEGER)
- `experience` (TEXT, DEFAULT 'Beginner') - `['Beginner', 'Intermediate', 'Advanced']`
- `goal` (TEXT, DEFAULT 'General Fitness') - `['Flexibility', 'Strength', 'Balance', 'Relaxation', 'General Fitness']`
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

### `poses`
Catalog of built-in and user-created custom yoga postures.
- `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `name` (TEXT, UNIQUE, NOT NULL)
- `sanskrit_name` (TEXT)
- `category` (TEXT, NOT NULL) - `['Standing', 'Sitting', 'Balance', 'Strength', 'Flexibility', 'Relaxation', 'Custom']`
- `difficulty` (TEXT, NOT NULL)
- `goal` (TEXT, NOT NULL)
- `description` (TEXT)
- `benefits` (TEXT, JSON array of strings)
- `instructions` (TEXT, JSON array of strings)
- `precautions` (TEXT)
- `image_path` (TEXT)
- `hold_duration` (INTEGER, DEFAULT 20)
- `is_custom` (INTEGER, DEFAULT 0)
- `created_by` (INTEGER, FOREIGN KEY REFERENCES `users(id)`)
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

### `pose_rules`
Anatomical joint constraints, target degree angles, tolerances, and corrective cues.
- `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `pose_id` (INTEGER, NOT NULL, FOREIGN KEY REFERENCES `poses(id)` ON DELETE CASCADE)
- `joint_name` (TEXT, NOT NULL) - e.g. `'left_knee'`, `'right_shoulder'`, `'torso_vertical'`
- `target_angle` (REAL, NOT NULL)
- `min_angle` (REAL, NOT NULL)
- `max_angle` (REAL, NOT NULL)
- `tolerance` (REAL, DEFAULT 15.0)
- `weight` (REAL, DEFAULT 15.0)
- `feedback_message` (TEXT)

### `practice_sessions`
Historical logs of completed practice workouts.
- `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `user_id` (INTEGER, NOT NULL, FOREIGN KEY REFERENCES `users(id)` ON DELETE CASCADE)
- `pose_id` (INTEGER, NOT NULL, FOREIGN KEY REFERENCES `poses(id)` ON DELETE CASCADE)
- `start_time` (TIMESTAMP)
- `end_time` (TIMESTAMP)
- `duration` (INTEGER, seconds)
- `average_score` (REAL)
- `final_score` (REAL)
- `hold_duration` (INTEGER, seconds achieved)
- `corrections_count` (INTEGER)
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

### `feedback`
Individual joint feedback events and corrections per practice session.
- `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `session_id` (INTEGER, NOT NULL, FOREIGN KEY REFERENCES `practice_sessions(id)` ON DELETE CASCADE)
- `body_part` (TEXT, NOT NULL)
- `message` (TEXT, NOT NULL)
- `accuracy` (REAL, NOT NULL)
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

### `custom_pose_templates`
Stores raw multi-frame captured geometric statistics for custom poses.
- `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `pose_id` (INTEGER, NOT NULL, UNIQUE, FOREIGN KEY REFERENCES `poses(id)` ON DELETE CASCADE)
- `reference_data` (TEXT, NOT NULL, JSON dictionary of joint angle averages & standard deviations)
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

---

## 3. Database Indexes

To optimize query speeds during real-time lookups and chart generation:
- `CREATE INDEX idx_poses_category ON poses(category);`
- `CREATE INDEX idx_poses_difficulty ON poses(difficulty);`
- `CREATE INDEX idx_poses_goal ON poses(goal);`
- `CREATE INDEX idx_pose_rules_pose_id ON pose_rules(pose_id);`
- `CREATE INDEX idx_sessions_user ON practice_sessions(user_id);`
- `CREATE INDEX idx_sessions_pose ON practice_sessions(pose_id);`
- `CREATE INDEX idx_sessions_created ON practice_sessions(created_at);`
