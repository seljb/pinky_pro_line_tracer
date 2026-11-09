"""Reject malformed clocks and repeated observations before motion."""

import math

import pytest

from pinky_line_alignment import control, vision


def ready_controller() -> control.AlignmentController:
    """Return an active controller with synthetic observations at one second."""
    controller = control.AlignmentController()
    controller.update_pose(control.Pose(0.0, 0.0, 0.0), 1.0)
    controller.update_line(
        vision.LineEstimate(0.0, 0.0, 0.1, 0.0, 0.1, 20, 0.2, 1.0),
        1.0,
        1,
    )
    assert controller.start(1.0)[0]
    return controller


@pytest.mark.parametrize("now_s", [math.nan, math.inf, -1.0, 0.99])
def test_bad_control_clock_requests_zero(now_s: float) -> None:
    """Invalid or backward time must fail closed, even in active states."""
    controller = ready_controller()
    command = controller.tick(now_s)
    assert command == control.Command()
    assert controller.state == control.State.FAILED


def test_duplicate_frame_does_not_refresh_receipt_time() -> None:
    """Repeated camera sequence numbers cannot keep stale observations alive."""
    controller = ready_controller()
    original = controller.line
    controller.update_line(original, 1.6, 1)
    controller.update_pose(control.Pose(0.0, 0.0, 0.0), 1.6)
    assert controller.line_time == 1.0
    assert controller.tick(1.6) == control.Command()
    assert controller.state == control.State.FAILED


@pytest.mark.parametrize("now_s", [math.nan, math.inf, -1.0])
def test_bad_line_receipt_invalidates_observation(now_s: float) -> None:
    """A line update with invalid time cannot retain valid sensor status."""
    controller = ready_controller()
    controller.update_line(controller.line, now_s, 2)
    assert controller.line is None
    assert not controller.fresh(1.1)


def test_planning_guard_does_not_depend_on_assertions() -> None:
    """Missing plan inputs explicitly transition to FAILED."""
    controller = control.AlignmentController()
    controller._set_plan(0.0)
    assert controller.state == control.State.FAILED
    assert controller.tick(0.0) == control.Command()


def test_stop_with_bad_clock_still_requests_zero() -> None:
    """An invalid stop timestamp must not prevent an operator stop."""
    controller = ready_controller()
    controller.stop(math.nan)
    assert controller.tick(1.1) == control.Command()
    assert controller.state == control.State.IDLE
    assert math.isfinite(controller.phase_start)
