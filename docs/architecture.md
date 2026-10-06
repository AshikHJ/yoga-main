# System Architecture & Technical Specification

## 1. Overview & High-Level Pipeline

The **AI-Based Yoga Pose Recommendation and Real-Time Posture Correction System** is built on a decoupled, modular architecture that bridges real-time computer vision, trigonometric posture analysis, goal-based recommendation logic, and a responsive PySide6 desktop user interface.

```
+-----------------------------------------------------------------------------------+
|                                 CORE PIPELINE FLOW                                |
+-----------------------------------------------------------------------------------+
  WEBCAM (OpenCV Capture @ 30 FPS)
     ↓
  RGB VIDEO FRAME
     ↓
  POSE LANDMARK ESTIMATION (MediaPipe Tasks Vision API / 33 3D Keypoints)
     ↓
  BODY VISIBILITY & CONFIDENCE VERIFICATION (Keypoint presence check)
     ↓
  GEOMETRIC FEATURE EXTRACTION (2D/3D Joint Vector Angle Calculation)
     ↓
  ┌─────────────────────────────────────────────────────────────┐
  │  POSE IDENTIFICATION          │  POSTURE COMPARISON &       │
  │  (Classification vs Library)  │  DEVIATION ANALYSIS (Rules) │
  └───────────────────────────────┴─────────────────────────────┘
     ↓                                  ↓
  DETECTED POSE CONFIRMATION         ACCURACY SCORE & LEVEL (0-100%)
     ↓                                  ↓
  HOLD TIMER MANAGEMENT (Auto-pause) ACTIONABLE CORRECTIVE COACHING
     ↓                                  ↓
  SESSION PERSISTENCE (SQLite Database / History & Feedback Logs)
     ↓
  PROGRESS ANALYTICS & PERSONALIZED RECOMMENDATIONS (Goal/Weakness-Based)
```

---

## 2. Multi-Tiered Modular Structure

```
AI-YOGA/
├── app.py                      # Application bootstrap & Qt event loop
├── requirements.txt            # Package dependencies manifest
├── .gitignore                  # Git exclusions
├── config/
│   └── settings.py             # Centralized system constants, paths & theme tokens
├── database/
│   ├── database.py             # Thread-safe SQLite context managers & CRUD methods
│   ├── schema.sql              # Relational database schema with foreign keys & indexes
│   └── yoga.db                 # Embedded local database storage
├── vision/
│   ├── camera.py               # Asynchronous QThread camera worker
│   ├── pose_detector.py        # MediaPipe Pose Landmarker detector
│   ├── landmarks.py            # Landmark mappings, anatomical bones & visibility
│   └── drawing.py              # Visual skeleton rendering & posture color-coding
├── analysis/
│   ├── angle_calculator.py     # Trigonometric vector angle computations
│   ├── pose_classifier.py      # Independent pose identification engine
│   ├── posture_checker.py      # Rule template comparator & deviation calculator
│   ├── score_calculator.py     # Weighted score calculator & level classifier
│   └── feedback.py             # Verbal/visual corrective feedback & TTS synthesizer
├── recommendation/
│   └── recommender.py          # Goal-aligned, progression & weakness recommendation
├── ui/
│   ├── styles.py               # Modern dark theme QSS stylesheet & tokens
│   ├── main_window.py          # Sidebar navigation shell & stacked orchestrator
│   ├── login_window.py         # Profile switcher & user registration dialog
│   ├── home_window.py          # Dashboard with metrics, daily routines & quick start
│   ├── yoga_library.py         # Searchable, filterable catalog of yoga poses
│   ├── pose_details.py         # Detailed pose modal with instructions & benefits
│   ├── camera_window.py        # Live practice screen, HUD overlays, checklist & timer
│   ├── recommendation_window.py# Dedicated personalized recommendations screen
│   ├── add_pose_window.py      # Custom pose creation & multi-frame reference capture
│   ├── progress_window.py      # Matplotlib analytics & trend graphs
│   └── session_summary.py      # Post-practice completion summary & coaching tips
├── data/
│   ├── poses.json              # 12 Initial validated yoga poses dataset
│   └── reference_poses/        # Storage for captured custom pose snapshots
├── tests/
│   ├── test_angles.py          # Trigonometric & vector math unit tests
│   ├── test_scoring.py         # Scoring curves & qualitative tiers unit tests
│   ├── test_pose_rules.py      # Posture checker & classifier verification tests
│   ├── test_recommendation.py  # Recommendation engine unit tests
│   └── test_database.py        # Database CRUD & persistence unit tests
└── docs/
    ├── architecture.md         # This technical architecture document
    ├── algorithms.md           # Mathematical and algorithmic formulas
    └── database.md             # Entity-Relationship diagram and schema details
```

---

## 3. Threading and Concurrency Model

To guarantee 60 FPS UI responsiveness without frame drops or GUI freezing:
1. **Camera & Vision Worker Thread (`CameraWorker : QThread`)**:
   - Manages OpenCV video capture and MediaPipe tensor inference.
   - Dispatches parsed frames and landmark dictionaries through Qt Signals to the main thread.
2. **Main GUI Thread (`QApplication`)**:
   - Handles Qt event processing, layout management, skeleton rendering, and user input.
3. **Voice Feedback Synthesizer (`VoiceFeedbackWorker`)**:
   - Executes speech synthesis asynchronously in a daemon thread with debouncing and cooldown mechanisms to prevent audio buffer congestion.

---

## 4. Key Design Decisions

### A. Separation of Pose Identification vs Posture Correction
- **Pose Identification**: Evaluates *what* posture the user is performing across the full catalog.
- **Posture Correction**: Evaluates *how accurately* the user conforms to the selected pose's reference template.
- This decoupling allows the system to warn a user if they selected Warrior II but are performing Mountain Pose.

### B. Universal Rule & Template Engine
- Built-in poses and user-created custom poses share the exact same JSON-based rule representation.
- Custom poses captured via the multi-frame reference wizard integrate seamlessly into classification, scoring, checklist verification, and recommendation algorithms without altering core application code.
