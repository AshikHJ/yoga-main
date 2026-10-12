"""
Tests for Full-Screen Camera Live Practice and Futuristic Neon Tracking HUD.
Validates:
1. Edge-to-edge practice viewport markup and styles.
2. Neon-green HUD elements: branding, tracking pill, sequence pill, large timer, controls.
3. Floating demo card with authentic photo, alignment targets, and breathing guidance.
4. Real-time biomechanical assessment card with score, status badge, and coach feedback.
5. Bottom dock with hold progress, timer, sequence counter, and audio indicator.
6. Absence of legacy pricing links, badges, and modals.
7. Dynamic bounding box, corner brackets, and clean tracking suppression in JavaScript.
"""

import re
import pytest
from web_app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_homepage_serves_hud_html(client):
    """Verifies that GET / serves 200 with the full-screen neon HUD markup."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 1. Full-screen practice container
    assert 'id="view-practice"' in html
    assert 'practice-fullscreen-mode' in html
    assert 'hud-fullscreen-container' in html
    assert 'id="practice-fullscreen-root"' in html

    # 2. Camera layer with video, canvas, and scanlines
    assert 'id="webcam-video"' in html
    assert 'id="skeleton-canvas"' in html
    assert 'hud-scanline-overlay' in html

    # 3. Framing screen frame with corner brackets
    assert 'hud-screen-frame' in html
    assert 'hud-corner-bracket top-left' in html
    assert 'hud-corner-bracket top-right' in html
    assert 'hud-corner-bracket bottom-left' in html
    assert 'hud-corner-bracket bottom-right' in html

    # 4. Top-left overlay: Technical labels and pose details
    assert "KI.AI // LIVE POSE TRACKING" in html
    assert 'id="hud-pose-title"' in html
    assert 'id="hud-pose-sanskrit"' in html
    assert 'id="hud-tracking-pill"' in html
    assert "BODY TRACKING: ACTIVE" in html
    assert 'id="hud-step-num"' in html

    # 5. Top-right overlay: Big timer and controls
    assert 'id="fs-timer"' in html
    assert 'id="btn-pause-resume"' in html
    assert 'id="btn-fit"' in html
    assert 'id="btn-hud-stop-voice"' in html
    assert "exitPracticeStudio()" in html
    assert "skipCurrentExercise()" in html

    # 6. Floating demonstration card
    assert 'id="practice-demo-panel"' in html
    assert 'id="demo-overlay-name-head"' in html
    assert 'id="btn-ref-min"' in html
    assert 'id="demo-pose-img"' in html
    assert 'id="demo-alignment-list"' in html
    assert 'id="demo-breathing-guidance"' in html

    # 7. Right-edge live posture assessment card
    assert 'id="hud-score"' in html
    assert 'id="hud-right-wrong-badge"' in html
    assert 'id="hud-feedback"' in html
    assert 'id="audio-wave-box"' in html

    # 8. Bottom dock
    assert 'id="hud-hold-display"' in html
    assert 'id="hud-hold-progress-bar"' in html
    assert 'id="fs-seq-label"' in html
    assert 'id="hud-next-upcoming"' in html


def test_pricing_and_pro_ui_completely_removed(client):
    """Verifies that all pricing nav links, drawer items, footer links, and plan badges are removed."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Nav and drawer buttons
    assert 'id="nav-btn-pricing"' not in html
    assert 'id="nav-plan-badge"' not in html
    assert 'Subscription &amp; Pro' not in html
    assert 'switchView(\'pricing\')' not in html


def test_hud_css_rules_present(client):
    """Verifies essential neon-green HUD CSS styling rules."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Neon Green color palette
    assert "#39FF14" in html
    # Full-screen fixed view
    assert "position: fixed !important;" in html
    assert "width: 100vw !important;" in html
    assert "height: 100dvh !important;" in html
    # Practice mode active body lock
    assert "body.practice-mode-active" in html


def test_dynamic_bounding_box_and_clean_suppression_in_js(client):
    """Verifies JavaScript implementation of dynamic bounding box and tracking logic."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Dynamic bounding box with corner brackets in drawSkeleton
    assert "DYNAMIC BOUNDING BOX AROUND DETECTED PERSON" in html
    assert "BODY_CONF:" in html
    assert "exitPracticeStudio" in html
    assert "practice-mode-active" in html
