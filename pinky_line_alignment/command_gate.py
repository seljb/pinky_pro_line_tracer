"""Select dry-run velocity requests without writing to a robot.

This software gate is neither a hardware emergency stop nor a certified mux.
All timestamps use one local monotonic clock, in seconds.
"""

import dataclasses
import math

from pinky_line_alignment import control


@dataclasses.dataclass(frozen=True)
class GateDecision:
    """Describe one software decision; allowed does not prove motor movement."""

    command: control.Command
    allowed: bool
    reason: str
    owner: str | None


class CommandGate:
    """Own dry-run command selection, a latched stop, and freshness checks."""

    _OWNERS = frozenset(("alignment", "follower"))

    def __init__(
        self,
        timeout_s: float = 0.25,
        readiness_timeout_s: float = 0.5,
        max_linear_m_s: float = 0.05,
        max_angular_rad_s: float = 0.35,
    ) -> None:
        """Initialize disabled with positive finite software limits.

        Raises:
            ValueError: If a duration or limit is not finite and positive.
        """
        values = (
            timeout_s,
            readiness_timeout_s,
            max_linear_m_s,
            max_angular_rad_s,
        )
        if any(not self._finite(value) or value <= 0 for value in values):
            raise ValueError("Durations and limits must be finite and positive")
        self.timeout_s = timeout_s
        self.readiness_timeout_s = readiness_timeout_s
        self.max_linear_m_s = max_linear_m_s
        self.max_angular_rad_s = max_angular_rad_s
        self.enabled = False
        self.stopped = False
        self.owner: str | None = None
        self._selected_at_s: float | None = None
        self._request: tuple[control.Command, float] | None = None
        self._follower_ready_at_s: float | None = None
        self._last_event_s: float | None = None

    @staticmethod
    def _finite(value: float) -> bool:
        """Return whether an external numeric value is finite and not bool."""
        try:
            return not isinstance(value, bool) and math.isfinite(value)
        except (TypeError, ValueError, OverflowError):
            return False

    def _accept_time(self, now_s: float) -> bool:
        """Advance one shared receipt clock, disabling on invalid clock input."""
        valid = (
            self._finite(now_s)
            and now_s >= 0
            and (self._last_event_s is None or now_s >= self._last_event_s)
        )
        if not valid:
            # 시계 오류 뒤에는 이전 요청을 재사용하지 않고 다시 활성화한다.
            self.enabled = False
            self._clear_selection()
            self._follower_ready_at_s = None
            return False
        self._last_event_s = now_s
        return True

    def _clear_selection(self) -> None:
        self.owner = None
        self._selected_at_s = None
        self._request = None

    def set_enabled(self, enabled: bool, now_s: float) -> None:
        """Require fresh selection and request after each enable operation.

        Args:
            enabled: Explicit operator enable flag; a stop latch still wins.
            now_s: Current monotonic time in seconds.
        """
        time_valid = self._accept_time(now_s)
        self.enabled = enabled is True and time_valid and not self.stopped
        self._clear_selection()
        self._follower_ready_at_s = None

    def stop(self) -> None:
        """Latch stop and discard every active request and readiness flag."""
        self.stopped = True
        self.enabled = False
        self._clear_selection()
        self._follower_ready_at_s = None

    def reset_stop(self) -> None:
        """Clear the stop latch but remain disabled until explicitly enabled."""
        self.stopped = False
        self.enabled = False
        self._clear_selection()
        self._follower_ready_at_s = None

    def set_follower_ready(self, ready: bool, now_s: float) -> None:
        """Record follower readiness; invalid or regressing timestamps revoke it.

        Args:
            ready: Whether the follower explicitly reports readiness.
            now_s: Receipt time in monotonic seconds, never a ROS wall stamp.
        """
        time_valid = self._accept_time(now_s)
        if (
            ready is not True
            or not time_valid
            or self._follower_ready_at_s is not None
            and now_s < self._follower_ready_at_s
        ):
            self._follower_ready_at_s = None
            if self.owner == "follower":
                self._request = None
            return
        self._follower_ready_at_s = now_s

    def _follower_fresh(self, now_s: float) -> bool:
        return self._follower_ready_at_s is not None and (
            0 <= now_s - self._follower_ready_at_s <= self.readiness_timeout_s
        )

    def select_owner(self, owner: str, now_s: float) -> bool:
        """Select one owner and discard the previously selected request.

        Args:
            owner: Exactly 'alignment' or 'follower'.
            now_s: Current monotonic time in seconds.

        Returns:
            False for disabled, stopped, invalid-time, or unready selection.
            Failure clears ownership, so a failed switch cannot drive old data.
        """
        self._clear_selection()
        time_valid = self._accept_time(now_s)
        if (
            not isinstance(owner, str)
            or owner not in self._OWNERS
            or not self.enabled
            or self.stopped
            or not time_valid
            or owner == "follower"
            and not self._follower_fresh(now_s)
        ):
            return False
        self.owner = owner
        self._selected_at_s = now_s
        return True

    def submit(
        self, owner: str, command: control.Command, now_s: float
    ) -> bool:
        """Accept one bounded request from the selected owner.

        Args:
            owner: Producer identity matching the explicit selection.
            command: Linear m/s and angular rad/s software request.
            now_s: Local receipt time in monotonic seconds.

        Returns:
            False for conflicts, invalid data, or backward receipt time. Any
            rejected request discards the active request, yielding zero output.
        """
        previous_time = None if self._request is None else self._request[1]
        self._request = None
        time_valid = self._accept_time(now_s)
        if (
            not self.enabled
            or self.stopped
            or owner != self.owner
            or self.owner is None
            or not time_valid
            or self._selected_at_s is None
            or now_s < self._selected_at_s
            or previous_time is not None
            and now_s < previous_time
            or not isinstance(command, control.Command)
        ):
            return False
        if (
            not self._finite(command.linear)
            or not self._finite(command.angular)
            or abs(command.linear) > self.max_linear_m_s
            or abs(command.angular) > self.max_angular_rad_s
        ):
            return False
        self._request = (command, now_s)
        return True

    def decide(self, now_s: float) -> GateDecision:
        """Return a fresh selected request or zero, with the decision reason.

        Args:
            now_s: Current monotonic time in seconds.

        Returns:
            A zero command on every denied path. Invalid clocks, expired data,
            and missing follower readiness discard the request permanently.
            A clock error disables selection until explicit operator re-enable.
        """
        reason = ""
        if not self._accept_time(now_s):
            reason = "invalid or regressing clock; explicit re-enable required"
        else:
            if self.stopped:
                reason = "operator stop latched"
            elif not self.enabled:
                reason = "operator enable required"
            elif self.owner is None or self._selected_at_s is None:
                reason = "owner selection required"
            elif now_s < self._selected_at_s:
                reason = "owner selection is future-dated"
            elif self.owner == "follower" and not self._follower_fresh(now_s):
                reason = "follower readiness missing or expired"
            elif self._request is None:
                reason = "fresh request required after owner selection"
            elif not 0 <= now_s - self._request[1] <= self.timeout_s:
                reason = "request timestamp expired or future-dated"
        if reason:
            self._request = None
            return GateDecision(control.Command(), False, reason, self.owner)
        # The checks above establish presence, without an assert safety guard.
        request = self._request
        if request is None:
            return GateDecision(
                control.Command(), False, "request unavailable", self.owner
            )
        return GateDecision(
            request[0], True, "fresh selected request", self.owner
        )
