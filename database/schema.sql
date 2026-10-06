-- =========================================================
-- KI.AI — AI-Powered Yoga & Posture Intelligence
-- Database Relational Schema (SQLite)
-- =========================================================

PRAGMA foreign_keys = ON;

-- Users Table with Auth & Profile support
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    age INTEGER DEFAULT 25,
    experience TEXT NOT NULL DEFAULT 'Beginner',
    goal TEXT NOT NULL DEFAULT 'General Fitness',
    avatar_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Yoga Poses Table
CREATE TABLE IF NOT EXISTS poses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sanskrit_name TEXT,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    goal TEXT NOT NULL,
    description TEXT,
    benefits TEXT,
    instructions TEXT,
    precautions TEXT,
    image_path TEXT,
    figure_path TEXT,
    hold_duration INTEGER DEFAULT 20,
    is_custom INTEGER DEFAULT 0,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Pose Rules Table
CREATE TABLE IF NOT EXISTS pose_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pose_id INTEGER NOT NULL,
    joint_name TEXT NOT NULL,
    target_angle REAL NOT NULL,
    min_angle REAL NOT NULL,
    max_angle REAL NOT NULL,
    tolerance REAL NOT NULL DEFAULT 15.0,
    weight REAL NOT NULL DEFAULT 15.0,
    feedback_message TEXT,
    FOREIGN KEY (pose_id) REFERENCES poses(id) ON DELETE CASCADE
);

-- Practice Sessions Table
CREATE TABLE IF NOT EXISTS practice_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    pose_id INTEGER NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration INTEGER NOT NULL DEFAULT 0,
    average_score REAL NOT NULL DEFAULT 0.0,
    final_score REAL NOT NULL DEFAULT 0.0,
    hold_duration INTEGER NOT NULL DEFAULT 0,
    corrections_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (pose_id) REFERENCES poses(id) ON DELETE CASCADE
);

-- Detailed Feedback Log Table
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    body_part TEXT NOT NULL,
    message TEXT NOT NULL,
    accuracy REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES practice_sessions(id) ON DELETE CASCADE
);

-- Custom Pose Templates Table
CREATE TABLE IF NOT EXISTS custom_pose_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pose_id INTEGER NOT NULL UNIQUE,
    reference_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pose_id) REFERENCES poses(id) ON DELETE CASCADE
);

-- User Preferences & Onboarding Table
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY,
    goal TEXT NOT NULL DEFAULT 'General Fitness',
    level TEXT NOT NULL DEFAULT 'Beginner',
    duration_minutes INTEGER NOT NULL DEFAULT 20,
    focus_area TEXT NOT NULL DEFAULT 'Full Body',
    voice_enabled INTEGER NOT NULL DEFAULT 1,
    voice_speed REAL NOT NULL DEFAULT 1.0,
    onboarding_completed INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- AI Generated Session Plans Table
CREATE TABLE IF NOT EXISTS session_plans (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    level TEXT NOT NULL,
    goal TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    focus TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Guided Multi-Exercise Practice Session Logs Table
CREATE TABLE IF NOT EXISTS guided_session_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_plan_id TEXT,
    level TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    avg_accuracy REAL NOT NULL DEFAULT 0.0,
    completed_poses INTEGER NOT NULL DEFAULT 0,
    total_poses INTEGER NOT NULL DEFAULT 0,
    best_pose TEXT,
    weakest_joint TEXT,
    status TEXT NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- AI Coach Interaction History Table
CREATE TABLE IF NOT EXISTS coach_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    message TEXT NOT NULL,
    intent TEXT,
    context_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Subscriptions Table
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plan TEXT NOT NULL DEFAULT 'FREE',
    status TEXT NOT NULL DEFAULT 'FREE',
    provider TEXT NOT NULL DEFAULT 'razorpay',
    provider_customer_id TEXT,
    provider_subscription_id TEXT,
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Payments Table
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subscription_id INTEGER,
    provider TEXT NOT NULL DEFAULT 'razorpay',
    order_id TEXT NOT NULL,
    payment_id TEXT,
    amount INTEGER NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL DEFAULT 'created',
    signature TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE SET NULL
);

-- Indexes for lightning fast queries
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_poses_category ON poses(category);
CREATE INDEX IF NOT EXISTS idx_poses_difficulty ON poses(difficulty);
CREATE INDEX IF NOT EXISTS idx_poses_goal ON poses(goal);
CREATE INDEX IF NOT EXISTS idx_pose_rules_pose_id ON pose_rules(pose_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON practice_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_pose ON practice_sessions(pose_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON practice_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_guided_logs_user ON guided_session_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_coach_conv_user ON coach_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_payment ON payments(payment_id);

