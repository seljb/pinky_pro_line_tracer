"""Reject unusable simulation intervals before entering the feedback loop."""

import math

import pytest

from pinky_line_alignment import closed_loop_sim


@pytest.mark.parametrize(
    ("step_s", "max_s"),
    [(0.0, 1.0), (-0.1, 1.0), (math.nan, 1.0), (0.1, 0.01), (0.1, math.inf)],
)
def test_invalid_simulation_budget(step_s: float, max_s: float) -> None:
    """Non-finite or empty integration loops cannot report simulated success."""
    with pytest.raises(ValueError):
        closed_loop_sim.simulate(step_s=step_s, max_s=max_s)
