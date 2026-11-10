"""Deterministic, ROS-free idealized planar simulation for integration tests.

The only purpose is to exercise our detector + odometry-based controller
together.
This ignores camera exposure latency, wheel slip, obstacles,
actuator lag, TF
errors and imperfect calibrations. A simulated pass is NOT
physical validation.
"""

from dataclasses import dataclass
import math
from pathlib import Path

import cv2
import numpy as np

from .vision import Calibration, LineDetector
from .control import AlignmentController, Pose, State, wrap


@dataclass(frozen=True)
class SimResult:
    """Report idealized simulation errors, duration, and final state."""

    state: str
    reason: str
    duration_s: float
    lateral_error_m: float
    heading_error_rad: float
    replans: int
    count: int


def render_tape(
    cal: Calibration, pose: Pose, tape_y_world: float = 0.0
) -> np.ndarray:
    """Project 10-pixel synthetic black tape into a synthetic camera image."""
    H_inv = np.linalg.inv(cal.H)
    x = np.linspace(-0.8, 2.0, 750)
    world = np.column_stack([x, np.full_like(x, tape_y_world)])
    relative = world - np.array([pose.x, pose.y])
    c, s = math.cos(pose.yaw), math.sin(pose.yaw)
    local = np.column_stack(
        [
            c * relative[:, 0] + s * relative[:, 1],
            -s * relative[:, 0] + c * relative[:, 1],
        ]
    )
    pix = cv2.perspectiveTransform(
        local.astype(np.float32).reshape(-1, 1, 2), H_inv
    ).reshape(-1, 2)
    visible = (
        (pix[:, 0] >= 0)
        & (pix[:, 0] < cal.width)
        & (pix[:, 1] >= 0)
        & (pix[:, 1] < cal.height)
    )
    frame = np.full((cal.height, cal.width, 3), 255, np.uint8)
    if visible.sum() >= 3:
        cv2.polylines(
            frame, [pix[visible].astype(np.int32)], False, (0, 0, 0), 10
        )
    return frame


def simulate(
    start_y: float = -0.08,
    start_yaw: float = 0.0,
    step_s: float = 0.04,
    max_s: float = 55.0,
) -> SimResult:
    """Run a deterministic synthetic detector/controller feedback loop.

    Args:
        start_y: Initial lateral position in metres.
        start_yaw: Initial heading in radians.
        step_s: Ideal integration interval in seconds; must be positive.
        max_s: Simulation budget in seconds; must allow at least one step.

    Returns:
        Final simulated state and errors; not evidence of physical performance.

    Raises:
        ValueError: If calibration is not the unvalidated synthetic model."""
    cal_path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "synthetic_calibration.json"
    )
    cal = Calibration.load(cal_path)
    if cal.kind != "synthetic" or cal.validated:
        raise ValueError("Only use a known unvalidated synthetic camera model")
    detector = LineDetector(cal)
    ctrl = AlignmentController()
    pose = Pose(0.0, start_y, start_yaw)
    n = int(max_s / step_s)
    for i in range(n):
        t = step_s * i
        line = detector.detect(render_tape(cal, pose))
        ctrl.update_pose(pose, t)
        ctrl.update_line(line, t, i)
        if i == 0 and not ctrl.start(t)[0]:
            break
        cmd = ctrl.tick(t)
        pose = Pose(
            pose.x + cmd.linear * math.cos(pose.yaw) * step_s,
            pose.y + cmd.linear * math.sin(pose.yaw) * step_s,
            wrap(pose.yaw + cmd.angular * step_s),
        )
        if ctrl.state in (State.READY, State.FAILED):
            break
    return SimResult(
        ctrl.state.value,
        ctrl.reason,
        float(step_s * i),
        float(pose.y),
        float(wrap(pose.yaw)),
        ctrl.replans,
        i + 1,
    )


def main() -> None:
    """Print both synthetic outcomes; use pytest to enforce success."""
    for y in (-0.08, 0.08):
        result = simulate(start_y=y)
        print(f"OFFLINE SYNTHETIC initial lateral {y:+.3f}m -> {result}")
    print(
        (
            "NOTE: Idealized closed loop is not evidence of "
            "real robot motion performance"
        )
    )


if __name__ == "__main__":
    main()
