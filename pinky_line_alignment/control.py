"""Testable low-speed, odometry-closed-loop TURN -> DRIVE -> TURN controller.

On sensor dropout, timeout or conflict: return zero Twist. This is a test
controller, NOT a certified protective stop or collision avoidance system.
"""
from dataclasses import dataclass
from enum import Enum
import math
from .vision import LineEstimate


def wrap(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


def clamp(x: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, x))


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    yaw: float


class State(str, Enum):
    IDLE = 'IDLE'
    OBSERVE = 'OBSERVE'
    TURN_TO_TARGET = 'TURN_TO_TARGET'
    DRIVE_TO_TARGET = 'DRIVE_TO_TARGET'
    TURN_TO_TANGENT = 'TURN_TO_TANGENT'
    VERIFY = 'VERIFY'
    READY = 'READY'
    COMPLETE = 'COMPLETE'
    FAILED = 'FAILED'


@dataclass(frozen=True)
class Command:
    linear: float = 0.
    angular: float = 0.


class AlignmentController:
    def __init__(self):
        # Conservative starting *software limits*, not Pinky-verified safe speeds.
        self.v_max = 0.05
        self.w_max = 0.35
        self.heading_tol = math.radians(6)
        self.approach_tol = 0.025
        self.final_lateral_tol = 0.015
        self.final_heading_tol = math.radians(6)
        self.max_vision_age_s = 0.5
        self.max_odom_age_s = 0.3
        self.max_phase_s = 14.
        self.max_total_s = 50.
        self.max_replans = 2
        self.max_ready_s = 2.0  # readiness is temporary until follower handoff
        self.state = State.IDLE
        self.reason = 'not started'
        self.pose: Pose | None = None
        self.pose_time = -1e9
        self.line: LineEstimate | None = None
        self.line_time = -1e9
        self.line_seq = -1
        self.count_seq = -1
        self.good_frames = 0
        self.verified_frames = 0
        self.replans = 0
        self.target_x = 0.
        self.target_y = 0.
        self.target_yaw = 0.
        self.phase_start = 0.
        self.started = 0.

    def update_pose(self, pose: Pose, now: float) -> None:
        if not all(math.isfinite(v) for v in (pose.x, pose.y, pose.yaw, now)):
            self.pose = None
            self.pose_time = -1e9
            return
        self.pose = pose
        self.pose_time = now

    def update_line(self, line: LineEstimate | None, now: float, seq: int) -> None:
        if line is not None and not all(math.isfinite(v) for v in
                (line.lateral_m, line.heading_rad, line.target_x_m, line.target_y_m,
                 line.nearest_visible_dist_m, line.quality)):
            line = None
        self.line = line
        self.line_time = now
        self.line_seq = seq

    def fresh(self, now: float) -> bool:
        return (self.pose is not None and self.line is not None
                and now-self.pose_time <= self.max_odom_age_s
                and now-self.line_time <= self.max_vision_age_s
                and now >= self.pose_time and now >= self.line_time)

    def _transition(self, state: State, now: float, reason: str = '') -> None:
        self.state = state
        self.phase_start = now
        self.reason = reason or state.value

    def start(self, now: float) -> tuple[bool, str]:
        if self.state not in (State.IDLE, State.FAILED, State.COMPLETE):
            return False, 'Stop current alignment first'
        if not self.fresh(now):
            return False, 'Need fresh camera line AND /odom before start'
        self.replans = self.good_frames = self.verified_frames = 0
        self.count_seq = -1
        self.started = now
        self._transition(State.OBSERVE, now)
        return True, 'Alignment started; check space and stop switch'

    def stop(self, now: float, reason: str = 'operator stop') -> None:
        self._transition(State.IDLE, now, reason)

    def alignment_valid(self, now: float) -> bool:
        return (self.fresh(now) and self.line is not None
                and abs(self.line.lateral_m) < self.final_lateral_tol
                and abs(self.line.heading_rad) < self.final_heading_tol)

    def handoff_ack(self, follower_ready: bool, now: float) -> tuple[bool, str]:
        if self.state != State.READY or not follower_ready:
            return False, 'Must be READY and follower must explicitly be ready'
        if now - self.phase_start > self.max_ready_s or not self.alignment_valid(now):
            self._transition(State.FAILED, now, 'handoff denied: alignment expired or lost')
            return False, self.reason
        self._transition(State.COMPLETE, now, 'handoff acknowledged; external mux must switch owner')
        return True, self.reason

    def _set_plan(self, now: float) -> None:
        assert self.pose is not None and self.line is not None
        c, s = math.cos(self.pose.yaw), math.sin(self.pose.yaw)
        self.target_x = self.pose.x + c*self.line.target_x_m - s*self.line.target_y_m
        self.target_y = self.pose.y + s*self.line.target_x_m + c*self.line.target_y_m
        self.target_yaw = wrap(self.pose.yaw + self.line.heading_rad)
        self._transition(State.TURN_TO_TARGET, now, 'target fixed in odom for this attempt')

    def tick(self, now: float) -> Command:
        if self.state == State.READY:
            # Crucial: READY must not remain latched after losing the line or odom.
            if now - self.phase_start > self.max_ready_s or not self.alignment_valid(now):
                self._transition(State.FAILED, now, 'ready expired or sensor/alignment lost')
            return Command()
        if self.state in (State.IDLE, State.COMPLETE, State.FAILED):
            return Command()
        if now-self.started > self.max_total_s:
            self._transition(State.FAILED, now, 'total time exceeded')
            return Command()
        if not self.fresh(now):
            self._transition(State.FAILED, now, 'stale/lost line or odometry')
            return Command()
        if now-self.phase_start > self.max_phase_s:
            self._transition(State.FAILED, now, 'phase timeout')
            return Command()
        assert self.pose is not None and self.line is not None
        if self.state == State.OBSERVE:
            if self.line_seq != self.count_seq:
                self.good_frames += 1
                self.count_seq = self.line_seq
            if self.good_frames >= 3:
                self.good_frames = 0
                self._set_plan(now)
            return Command()
        dx = self.target_x-self.pose.x
        dy = self.target_y-self.pose.y
        distance = math.hypot(dx,dy)
        target_bearing = math.atan2(dy,dx)
        if self.state == State.TURN_TO_TARGET:
            if distance < self.approach_tol:
                self._transition(State.TURN_TO_TANGENT, now)
                return Command()
            e = wrap(target_bearing-self.pose.yaw)
            if abs(e) < self.heading_tol:
                self._transition(State.DRIVE_TO_TARGET, now)
                return Command()
            return Command(0., clamp(1.3*e,-self.w_max,self.w_max))
        if self.state == State.DRIVE_TO_TARGET:
            if distance < self.approach_tol:
                self._transition(State.TURN_TO_TANGENT, now)
                return Command()
            e = wrap(target_bearing-self.pose.yaw)
            if abs(e) > math.radians(24):
                self._transition(State.TURN_TO_TARGET, now, 'bearing correction')
                return Command()
            return Command(min(self.v_max, max(0.012, 0.65*distance)),
                           clamp(1.4*e,-self.w_max,self.w_max))
        if self.state == State.TURN_TO_TANGENT:
            e = wrap(self.target_yaw-self.pose.yaw)
            if abs(e) < self.heading_tol:
                self.verified_frames = 0
                self.count_seq = -1
                self._transition(State.VERIFY, now)
                return Command()
            return Command(0., clamp(1.3*e,-self.w_max,self.w_max))
        if self.state == State.VERIFY:
            if (abs(self.line.lateral_m) < self.final_lateral_tol
                    and abs(self.line.heading_rad) < self.final_heading_tol):
                if self.line_seq != self.count_seq:
                    self.verified_frames += 1
                    self.count_seq = self.line_seq
                if self.verified_frames >= 5:
                    self._transition(State.READY, now, 'verified five fresh camera frames; motors stopped')
            elif self.line_seq != self.count_seq:
                self.verified_frames = 0
                self.count_seq = self.line_seq
            # Replan only after a short stable observation window, not a single bad frame.
            if self.state == State.VERIFY and now-self.phase_start > 1.8:
                if self.replans >= self.max_replans:
                    self._transition(State.FAILED, now, 'failed final position/orientation tolerance')
                else:
                    self.replans += 1
                    self.good_frames = 0
                    self.count_seq = -1
                    self._transition(State.OBSERVE, now, 'replanning after failed verification')
            return Command()
        self._transition(State.FAILED, now, 'unexpected state')
        return Command()
