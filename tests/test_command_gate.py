"""Exercise dry-run ownership, time boundaries, and latched stop behavior."""

import math

import pytest

from pinky_line_alignment import command_gate
from pinky_line_alignment import control


def enabled_gate() -> command_gate.CommandGate:
    """Create an explicitly enabled gate with alignment ownership."""
    gate = command_gate.CommandGate()
    gate.set_enabled(True, 0.0)
    assert gate.select_owner("alignment", 0.0)
    return gate


def test_disabled_by_default_and_explicit_selection() -> None:
    gate = command_gate.CommandGate()
    request = control.Command(0.03, 0.1)
    assert not gate.submit("alignment", request, 0.0)
    assert not gate.decide(0.0).allowed
    gate.set_enabled(True, 0.0)
    assert not gate.submit("alignment", request, 0.0)
    assert gate.select_owner("alignment", 0.0)
    assert gate.submit("alignment", request, 0.0)
    assert gate.decide(0.1).command == request


def test_stale_request_cannot_be_reused() -> None:
    gate = enabled_gate()
    assert gate.submit("alignment", control.Command(0.04), 0.0)
    assert gate.decide(0.25).allowed
    stale = gate.decide(0.25001)
    assert stale.command == control.Command()
    assert not stale.allowed
    assert not gate.decide(0.26).allowed


def test_stop_latches_and_reset_does_not_enable() -> None:
    gate = enabled_gate()
    assert gate.submit("alignment", control.Command(0.04), 0.0)
    gate.stop()
    gate.set_enabled(True, 0.1)
    assert not gate.select_owner("alignment", 0.1)
    assert not gate.decide(0.1).allowed
    gate.reset_stop()
    assert not gate.select_owner("alignment", 0.2)
    gate.set_enabled(True, 0.2)
    assert gate.select_owner("alignment", 0.2)
    assert not gate.decide(0.2).allowed
    assert gate.submit("alignment", control.Command(0.02), 0.2)
    assert gate.decide(0.2).allowed


def test_follower_switch_requires_ready_and_fresh_new_request() -> None:
    gate = enabled_gate()
    assert gate.submit("alignment", control.Command(0.03), 0.0)
    assert not gate.select_owner("follower", 0.1)
    assert gate.decide(0.1).command == control.Command()
    gate.set_follower_ready(True, 0.2)
    assert gate.select_owner("follower", 0.2)
    assert not gate.decide(0.2).allowed
    assert gate.submit("follower", control.Command(0.01), 0.2)
    assert gate.decide(0.2).allowed
    assert not gate.submit("alignment", control.Command(0.03), 0.21)
    assert gate.decide(0.21).command == control.Command()


def test_expired_follower_readiness_blocks_selection_and_output() -> None:
    gate = enabled_gate()
    gate.set_follower_ready(True, 0.0)
    assert not gate.select_owner("follower", 0.51)
    gate.set_follower_ready(True, 1.0)
    assert gate.select_owner("follower", 1.0)
    assert gate.submit("follower", control.Command(0.01), 1.49)
    assert gate.decide(1.49).allowed
    assert gate.decide(1.51).command == control.Command()


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_nonfinite_time_and_commands_produce_zero(bad: float) -> None:
    gate = enabled_gate()
    assert not gate.submit("alignment", control.Command(bad), 0.0)
    assert gate.decide(0.0).command == control.Command()
    assert gate.submit("alignment", control.Command(0.01), 0.1)
    assert gate.decide(bad).command == control.Command()
    assert not gate.submit("alignment", control.Command(), bad)


@pytest.mark.parametrize(
    "velocity", [control.Command(0.051), control.Command(0.0, -0.351)]
)
def test_excess_requests_are_rejected_not_silently_clamped(
    velocity: control.Command,
) -> None:
    gate = enabled_gate()
    assert not gate.submit("alignment", velocity, 0.0)
    assert not gate.decide(0.0).allowed


def test_future_and_regressing_time_invalidate_request() -> None:
    gate = enabled_gate()
    assert gate.submit("alignment", control.Command(0.01), 1.0)
    assert not gate.decide(0.9).allowed
    assert not gate.decide(1.0).allowed
    assert not gate.submit("alignment", control.Command(0.01), 1.1)
    gate.set_enabled(True, 1.1)
    assert gate.select_owner("alignment", 1.1)
    assert gate.submit("alignment", control.Command(0.01), 1.1)
    assert gate.decide(1.1).allowed
    assert not gate.decide(1.0).allowed
    assert not gate.decide(1.2).allowed


def test_unknown_owner_and_disable_discard_request() -> None:
    gate = enabled_gate()
    assert not gate.select_owner("teleop", 0.0)
    assert not gate.decide(0.0).allowed
    assert gate.select_owner("alignment", 0.0)
    assert gate.submit("alignment", control.Command(0.01), 0.0)
    gate.set_enabled(False, 0.1)
    gate.set_enabled(True, 0.2)
    assert not gate.decide(0.2).allowed


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf, True])
def test_invalid_limits_fail_construction(bad: float) -> None:
    with pytest.raises(ValueError):
        command_gate.CommandGate(timeout_s=bad)


@pytest.mark.parametrize("bad", [-0.01, -math.inf, math.nan])
def test_invalid_clock_during_enable_requires_new_operator_action(
    bad: float,
) -> None:
    gate = command_gate.CommandGate()
    gate.set_enabled(True, bad)
    assert not gate.select_owner("alignment", 0.0)
    assert gate.decide(0.0).command == control.Command()


def test_clock_order_is_checked_before_first_decision() -> None:
    gate = command_gate.CommandGate()
    gate.set_enabled(True, 100.0)
    assert not gate.select_owner("alignment", 0.0)
    assert not gate.enabled
    gate.set_enabled(True, 100.0)
    assert gate.select_owner("alignment", 100.0)
    assert gate.submit("alignment", control.Command(0.01), 100.0)
    gate.set_follower_ready(True, 99.0)
    assert not gate.enabled
    assert not gate.decide(100.0).allowed
    gate.set_enabled(True, 100.1)
    gate.set_follower_ready(True, 100.1)
    assert gate.select_owner("follower", 100.1)
    assert not gate.decide(100.1).allowed
