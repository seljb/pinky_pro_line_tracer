"""Test control behavior with synthetic inputs only."""

import math
from pinky_line_alignment.control import AlignmentController, Pose, State, wrap
from pinky_line_alignment.vision import LineEstimate


def line(offset=-0.08, heading=0.0, target_x=0.10, target_y=0.08):
    """Build a synthetic estimate for controller tests, never real feedback."""
    return LineEstimate(offset, heading, target_x, target_y, 0.1, 20, 0.2, 1.0)


def test_does_not_start_without_sensors():
    """Reject alignment start without fresh camera and odometry."""
    c = AlignmentController()
    ok, _ = c.start(0.0)
    assert not ok and c.state == State.IDLE
    assert c.tick(0.0).linear == 0


def test_stale_sensor_stops_immediately():
    """Require zero requested motion after sensor data expires."""
    c = AlignmentController()
    c.update_pose(Pose(0, 0, 0), 0.0)
    c.update_line(line(), 0.0, 1)
    assert c.start(0.0)[0]
    assert c.tick(0.01).linear == 0.0
    c.tick(1.0)
    assert c.state == State.FAILED
    assert c.tick(1.1).angular == 0.0


def test_plan_and_motion_commands_with_explicit_handoff():
    """Exercise toy motion and require explicit follower-ready handoff."""
    c = AlignmentController()
    p = Pose(0, 0, 0)
    c.update_pose(p, 0.0)
    c.update_line(line(), 0.0, 1)
    assert c.start(0.0)[0]
    for i in range(2, 5):
        t = i * 0.01
        c.update_pose(p, t)
        c.update_line(line(), t, i)
        c.tick(t)
    assert c.state == State.TURN_TO_TARGET
    # Apply a toy kinematic simulation to the locked goal.
    for k in range(1000):
        t = 0.1 + k * 0.04
        c.update_pose(p, t)
        if c.state in (State.VERIFY, State.READY):
            # In a real run, new images must show this, never spoof real feedback.
            c.update_line(
                line(offset=0.0, target_x=0.0, target_y=0.0), t, 10 + k
            )
        else:
            c.update_line(line(), t, 10 + k)
        cmd = c.tick(t)
        p = Pose(
            p.x + cmd.linear * math.cos(p.yaw) * 0.04,
            p.y + cmd.linear * math.sin(p.yaw) * 0.04,
            wrap(p.yaw + cmd.angular * 0.04),
        )
        if c.state in (State.READY, State.FAILED):
            break
    assert c.state == State.READY, f"{c.state=} {c.reason=} {p=}"
    assert c.tick(t + 0.01).linear == 0.0
    assert not c.handoff_ack(False, t + 0.02)[0]
    assert c.handoff_ack(True, t + 0.03)[0]
    assert c.state == State.COMPLETE


def test_operator_stop():
    """Require IDLE and zero requested motion after operator stop."""
    c = AlignmentController()
    c.update_pose(Pose(0, 0, 0), 0.0)
    c.update_line(line(), 0.0, 1)
    c.start(0.0)
    c.stop(0.1)
    assert c.tick(0.2).linear == 0 and c.state == State.IDLE


def test_ready_expires_and_cannot_handoff_after_lost_sensors():
    """Invalidate READY and reject handoff when sensor data expires."""
    c = AlignmentController()
    c.state = State.READY
    c.phase_start = 1.0
    c.update_pose(Pose(0.0, 0.0, 0.0), 1.0)
    c.update_line(line(offset=0.0, heading=0.0), 1.0, 10)
    assert c.tick(1.01).linear == 0
    # Previous version kept READY latched despite losing camera and odometry.
    assert c.tick(1.9).linear == 0
    assert c.state == State.FAILED
    assert not c.handoff_ack(True, 1.91)[0]


def test_handoff_checks_current_alignment_not_only_ready_flag():
    """Reject handoff when current errors violate alignment tolerances."""
    c = AlignmentController()
    c.state = State.READY
    c.phase_start = 1.0
    c.update_pose(Pose(0.0, 0.0, 0.0), 1.1)
    c.update_line(line(offset=0.08, heading=0.0), 1.1, 10)
    ok, message = c.handoff_ack(True, 1.15)
    assert not ok and c.state == State.FAILED
    assert "alignment" in message


def test_ready_timeout_even_with_live_sensors():
    """Expire READY even if fresh observations continue to arrive."""
    c = AlignmentController()
    c.state = State.READY
    c.phase_start = 1.0
    c.update_pose(Pose(0.0, 0.0, 0.0), 4.0)
    c.update_line(line(offset=0.0, heading=0.0), 4.0, 10)
    assert c.tick(4.0).angular == 0
    assert c.state == State.FAILED


def test_invalid_odometry_cannot_drive():
    """Reject non-finite odometry before and during alignment."""
    c = AlignmentController()
    c.update_pose(Pose(float("nan"), 0.0, 0.0), 0.0)
    c.update_line(line(), 0.0, 1)
    assert not c.start(0.0)[0]
    c.update_pose(Pose(0.0, 0.0, 0.0), 0.1)
    assert c.start(0.1)[0]
    c.update_pose(Pose(0.0, float("inf"), 0.0), 0.2)
    assert c.tick(0.2).linear == 0.0
    assert c.tick(0.2).angular == 0.0
    assert c.state == State.FAILED


def test_invalid_line_estimate_cannot_handoff():
    """Reject a non-finite line estimate while waiting for handoff."""
    c = AlignmentController()
    c.state = State.READY
    c.phase_start = 1.0
    c.update_pose(Pose(0.0, 0.0, 0.0), 1.0)
    c.update_line(line(offset=float("nan")), 1.0, 1)
    assert c.tick(1.01).linear == 0.0
    assert c.state == State.FAILED
