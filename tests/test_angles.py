"""
Unit tests for AngleCalculator and trigonometric geometric utilities.
"""

import math
import pytest
from analysis.angle_calculator import AngleCalculator


def test_calculate_right_angle():
    # Perpendicular points: A=(0, 1), B=(0, 0), C=(1, 0) -> Angle at B should be 90.0°
    a = [0.0, 1.0]
    b = [0.0, 0.0]
    c = [1.0, 0.0]
    angle = AngleCalculator.calculate_angle(a, b, c)
    assert pytest.approx(angle, 0.01) == 90.0


def test_calculate_straight_line_angle():
    # Collinear points: A=(-1, 0), B=(0, 0), C=(1, 0) -> 180.0°
    a = [-1.0, 0.0]
    b = [0.0, 0.0]
    c = [1.0, 0.0]
    angle = AngleCalculator.calculate_angle(a, b, c)
    assert pytest.approx(angle, 0.01) == 180.0


def test_calculate_acute_angle():
    # 45 degree triangle: A=(1, 1), B=(0, 0), C=(1, 0) -> 45.0°
    a = [1.0, 1.0]
    b = [0.0, 0.0]
    c = [1.0, 0.0]
    angle = AngleCalculator.calculate_angle(a, b, c)
    assert pytest.approx(angle, 0.05) == 45.0


def test_zero_length_vector_handling():
    # Coinciding points should safely return 0.0 instead of crashing or NaN
    a = [0.0, 0.0]
    b = [0.0, 0.0]
    c = [1.0, 1.0]
    angle = AngleCalculator.calculate_angle(a, b, c)
    assert angle == 0.0


def test_calculate_angle_with_vertical():
    # Perfectly vertical segment (top=(0.5, 0.2), bottom=(0.5, 0.8))
    # Note: image Y is inverted (0 is top, 1 is bottom)
    top = [0.5, 0.2]
    bottom = [0.5, 0.8]
    angle = AngleCalculator.calculate_angle_with_vertical(top, bottom)
    assert pytest.approx(angle, 0.1) == 90.0


def test_calculate_angle_with_horizontal():
    # Horizontal segment (left=(0.2, 0.5), right=(0.8, 0.5)) -> 0° tilt
    p1 = [0.2, 0.5]
    p2 = [0.8, 0.5]
    angle = AngleCalculator.calculate_angle_with_horizontal(p1, p2)
    assert pytest.approx(angle, 0.1) == 0.0


def test_extract_all_angles_from_landmarks():
    # Synthetic landmark dictionary
    mock_landmarks = {
        "LEFT_SHOULDER": {"x": 0.6, "y": 0.3, "z": 0.0, "visibility": 0.9},
        "RIGHT_SHOULDER": {"x": 0.4, "y": 0.3, "z": 0.0, "visibility": 0.9},
        "LEFT_ELBOW": {"x": 0.8, "y": 0.3, "z": 0.0, "visibility": 0.9},
        "RIGHT_ELBOW": {"x": 0.2, "y": 0.3, "z": 0.0, "visibility": 0.9},
        "LEFT_WRIST": {"x": 0.95, "y": 0.3, "z": 0.0, "visibility": 0.9},
        "RIGHT_WRIST": {"x": 0.05, "y": 0.3, "z": 0.0, "visibility": 0.9},
        "LEFT_HIP": {"x": 0.55, "y": 0.6, "z": 0.0, "visibility": 0.9},
        "RIGHT_HIP": {"x": 0.45, "y": 0.6, "z": 0.0, "visibility": 0.9},
        "LEFT_KNEE": {"x": 0.55, "y": 0.8, "z": 0.0, "visibility": 0.9},
        "RIGHT_KNEE": {"x": 0.45, "y": 0.8, "z": 0.0, "visibility": 0.9},
        "LEFT_ANKLE": {"x": 0.55, "y": 0.98, "z": 0.0, "visibility": 0.9},
        "RIGHT_ANKLE": {"x": 0.45, "y": 0.98, "z": 0.0, "visibility": 0.9},
    }

    angles = AngleCalculator.extract_all_angles(mock_landmarks)
    assert "left_elbow" in angles
    assert "right_elbow" in angles
    assert "left_knee" in angles
    assert "right_knee" in angles
    assert "left_shoulder" in angles
    assert "torso_vertical" in angles
    # Straight arms -> ~180°
    assert pytest.approx(angles["left_elbow"], 1.0) == 180.0
    # Straight legs -> ~180°
    assert pytest.approx(angles["left_knee"], 1.0) == 180.0
