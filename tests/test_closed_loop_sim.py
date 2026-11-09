"""Test closed loop sim behavior with synthetic inputs only."""

import math
import pytest
from pinky_line_alignment.closed_loop_sim import simulate


@pytest.mark.parametrize('initial_lateral_m', [-0.08, 0.08])
def test_detector_and_controller_closed_loop_synthetic(initial_lateral_m):
    """Require READY within synthetic position, heading, and time limits."""
    result = simulate(start_y=initial_lateral_m)
    assert result.state == 'READY', result
    assert abs(result.lateral_error_m) < 0.015, result
    assert abs(math.degrees(result.heading_error_rad)) < 6, result
    assert result.duration_s < 50, result
