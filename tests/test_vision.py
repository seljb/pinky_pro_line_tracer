"""Test vision behavior with synthetic inputs only."""

import math
from pathlib import Path
import numpy as np
import pytest
from pinky_line_alignment.vision import Calibration, LineDetector
from pinky_line_alignment.offline_demo import synthetic_image

CAL = Path(__file__).resolve().parents[1] / "config/synthetic_calibration.json"


def test_synthetic_line_location_and_heading():
    """Check synthetic line estimates against known ground geometry."""
    detector = LineDetector(Calibration.load(CAL))
    result = detector.detect(synthetic_image(offset_m=0.08, slope=0.2))
    assert result is not None
    assert abs(result.heading_rad - math.atan(0.2)) < 0.045
    assert abs(result.target_y_m - 0.08) < 0.065
    assert result.count >= 7


def test_no_line_returns_none():
    """Return no estimate for a uniformly white image."""
    detector = LineDetector(Calibration.load(CAL))
    assert detector.detect(np.full((480, 640, 3), 255, np.uint8)) is None


def test_image_size_must_match_calibration():
    """Reject images whose size differs from the calibration."""
    detector = LineDetector(Calibration.load(CAL))
    with pytest.raises(ValueError):
        detector.detect(np.full((240, 320, 3), 255, np.uint8))


def test_synthetic_calibration_never_marked_real():
    """Keep the synthetic fixture unvalidated and distinct from real data."""
    cal = Calibration.load(CAL)
    assert cal.kind == "synthetic" and not cal.validated
