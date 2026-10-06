# KI.AI — AI-Guided Yoga Learning System & Posture Intelligence

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Web App](https://img.shields.io/badge/Web%20App-Flask%20%7C%20HTML5%20%7C%20JS-green.svg)](https://flask.palletsprojects.com/)
[![Computer Vision](https://img.shields.io/badge/Vision-MediaPipe%20Pose-orange.svg)](https://developers.google.com/mediapipe)
[![Tests](https://img.shields.io/badge/Tests-PyTest%20(36%20Passed)-brightgreen.svg)](https://docs.pytest.org/)
[![Database](https://img.shields.io/badge/Database-SQLite3-lightgrey.svg)](https://www.sqlite.org/)

---

## 1. Product Overview
**KI.AI** is a complete, polished AI-Guided Yoga Learning System and Posture Intelligence platform. Instead of forcing users to manually search for and practice individual poses, KI.AI acts as a personal **AI Yoga Coach** that dynamically generates, guides, and teaches progressive yoga learning sessions tailored to user goals, experience level, and biomechanical accuracy history.

---

## 2. Core Architecture & Product Features

### 1. AI-Guided Yoga Learning System
- **Single Primary CTA**: Users choose their Goal, Level, and Time, then click **"START TODAY'S SESSION"**.
- **Automated Multi-Exercise Roadmaps**: Generates step-by-step sessions incorporating Breathing -> Warm-up -> Standing Alignment -> Asanas -> Surya Namaskar -> Balasana -> Decompression.
- **Automatic Transitions & Countdown**: Automatically transitions between exercises with a 3.. 2.. 1.. countdown overlay upon hold completion.

### 2. Three Main Learning Programs
- **LEVEL 1 — Foundation (Beginner)**: Build body awareness and master alignment fundamentals.
- **LEVEL 2 — Progress (Intermediate)**: Build strength, flexibility, balance, and control.
- **LEVEL 3 — Mastery (Advanced)**: Advanced sequences, deep mobility work, Natarajasana dancer extensions, and safety checks.

### 3. Live AI Camera Coaching & Intelligent Valid Hold Timer
- **Automatic Pose Detection**: Automatically identifies user pose and verifies alignment.
- **Intelligent Valid Hold Timer**: Only counts hold time when posture is correct, body is fully visible, and required joint angles stay within tolerance.
- **Visual Skeleton Overlay**: Green/Red joint feedback with exact angle error callouts.
- **Audio Voice Coaching**: Throttled text-to-speech coaching cues.

### 4. Interactive Conversational AI Coach & Safety Layer
- **Voice & Chat Assistant**: Web Speech API voice interaction answering posture questions, adjusting session length, or skipping exercises.
- **Clinical Safety Layer**: Immediate stop alert when pain/discomfort keywords are mentioned, instructing practitioner to rest in Child's pose (Balasana).

### 5. Japanese Botanical Design System
- Warm botanical off-white / deep forest green palette (`#0B120E`, `#121A15`, `#2D6A4F`, `#E9ECE6`).
- Clean editorial typography (`Plus Jakarta Sans` & `Inter`).

---

## 3. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python 3.12+ / Flask | Server logic, session state machine, and REST APIs |
| **Computer Vision** | MediaPipe Tasks Vision API | 33 3D full-body landmark estimation |
| **Session Engine** | `SessionPlanner` | Dynamic roadmap generation & program unlock logic |
| **AI Coach** | `ConversationalCoach` & `CoachEngine` | Dialogue parsing, safety trigger, and debounced audio |
| **Database** | SQLite3 | Relational user, session, and pose data storage |
| **Frontend** | HTML5, CSS3, ES6 JS, Chart.js | Responsive UI, canvas rendering, and analytics |
| **Testing** | pytest | Automated unit test suite (36 passed) |

---

## 4. How to Launch the Application

### Launch Command
```bash
python3 web_app.py
```

### Access URL
Open your web browser and navigate to:
```text
http://localhost:8080
```

---

## 5. Verification & Testing

Run automated unit tests and code compilation:
```bash
python3 -m compileall .
pytest tests/ -v
```

Expected output:
```text
============================== 22 passed in 5.18s ==============================
```
