"""Validate synthetic camera-to-command behavior without ROS or robot access.

The renderer uses a fixed 10-pixel straight tape and ideal planar odometry.
No result establishes real camera accuracy, motor safety, or mux readiness.
"""

import argparse
import csv
import dataclasses
import json
import logging
import math
import pathlib

from pinky_line_alignment import closed_loop_sim
from pinky_line_alignment import command_gate
from pinky_line_alignment import control
from pinky_line_alignment import resource_paths
from pinky_line_alignment import vision


LOGGER = logging.getLogger(__name__)
_SCENARIOS = ("align_left", "align_right", "camera_dropout", "operator_stop")


@dataclasses.dataclass(frozen=True)
class ScenarioResult:
    """Report one synthetic outcome with explicit units and pass criteria."""

    name: str
    passed: bool
    state: str
    reason: str
    elapsed_s: float
    final_lateral_m: float
    final_heading_rad: float
    frame_count: int
    nonzero_request_count: int
    post_fault_zero_count: int
    expected: str


def _load_synthetic_calibration() -> vision.Calibration:
    source = resource_paths.calibration_file("synthetic_calibration.json")
    calibration = vision.Calibration.load(source)
    if calibration.kind != "synthetic" or calibration.validated:
        raise ValueError("Validation requires unvalidated synthetic geometry")
    return calibration


def _run_scenario(
    name: str,
    destination: pathlib.Path,
    step_s: float,
    max_s: float,
) -> ScenarioResult:
    """Exercise actual detection, controller, gate, and ideal motion together."""
    calibration = _load_synthetic_calibration()
    detector = vision.LineDetector(calibration)
    controller = control.AlignmentController()
    gate = command_gate.CommandGate()
    gate.set_enabled(True, 0.0)
    if not gate.select_owner("alignment", 0.0):
        raise RuntimeError(
            "Synthetic alignment ownership could not be selected"
        )
    initial_y_m = 0.08 if name == "align_right" else -0.08
    pose = control.Pose(0.0, initial_y_m, 0.0)
    fault_at_s = 1.0
    frame_count = 0
    nonzero_count = 0
    post_fault_zero_count = 0
    unsafe_after_fault = False
    stopped = False
    elapsed_s = 0.0
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=(
                "frame_index",
                "elapsed_s",
                "state",
                "line_received",
                "lateral_m",
                "heading_rad",
                "requested_linear_m_s",
                "requested_angular_rad_s",
                "selected_linear_m_s",
                "selected_angular_rad_s",
                "gate_allowed",
                "gate_reason",
            ),
        )
        writer.writeheader()
        for frame_index in range(int(max_s / step_s)):
            elapsed_s = frame_index * step_s
            frame_count += 1
            controller.update_pose(pose, elapsed_s)
            line_received = not (
                name == "camera_dropout" and elapsed_s >= fault_at_s
            )
            if line_received:
                # 합성 관측도 실제 검출기를 통과시키며 성공 값을 주입하지 않는다.
                frame = closed_loop_sim.render_tape(calibration, pose)
                line = detector.detect(frame)
                controller.update_line(line, elapsed_s, frame_index)
            if frame_index == 0:
                accepted, _ = controller.start(elapsed_s)
                if not accepted:
                    raise RuntimeError("Synthetic controller failed to start")
            if (
                name == "operator_stop"
                and elapsed_s >= fault_at_s
                and not stopped
            ):
                gate.stop()
                controller.stop(elapsed_s, "synthetic operator stop")
                stopped = True
            requested = controller.tick(elapsed_s)
            gate.submit("alignment", requested, elapsed_s)
            decision = gate.decide(elapsed_s)
            selected = decision.command
            nonzero = selected.linear != 0.0 or selected.angular != 0.0
            nonzero_count += int(nonzero)
            fault_active = (
                name == "operator_stop"
                and stopped
                or name == "camera_dropout"
                and controller.state == control.State.FAILED
            )
            if fault_active:
                post_fault_zero_count += int(not nonzero)
                unsafe_after_fault |= nonzero
            writer.writerow(
                {
                    "frame_index": frame_index,
                    "elapsed_s": elapsed_s,
                    "state": controller.state.value,
                    "line_received": line_received,
                    "lateral_m": pose.y,
                    "heading_rad": pose.yaw,
                    "requested_linear_m_s": requested.linear,
                    "requested_angular_rad_s": requested.angular,
                    "selected_linear_m_s": selected.linear,
                    "selected_angular_rad_s": selected.angular,
                    "gate_allowed": decision.allowed,
                    "gate_reason": decision.reason,
                }
            )
            pose = control.Pose(
                pose.x + selected.linear * math.cos(pose.yaw) * step_s,
                pose.y + selected.linear * math.sin(pose.yaw) * step_s,
                control.wrap(pose.yaw + selected.angular * step_s),
            )
            if controller.state in (control.State.READY, control.State.FAILED):
                break
            if stopped and elapsed_s >= fault_at_s + 0.16:
                break
    if name.startswith("align_"):
        expected = "READY; lateral < 0.015 m; heading < 6 deg; time < 50 s"
        passed = (
            controller.state == control.State.READY
            and abs(pose.y) < 0.015
            and abs(pose.yaw) < math.radians(6.0)
            and elapsed_s < 50.0
            and nonzero_count > 0
        )
    elif name == "camera_dropout":
        expected = "FAILED after camera receipt timeout; zero output on failure"
        passed = (
            controller.state == control.State.FAILED
            and "stale" in controller.reason
            and post_fault_zero_count > 0
            and not unsafe_after_fault
            and nonzero_count > 0
        )
    else:
        expected = "IDLE after operator stop; all post-stop outputs are zero"
        passed = (
            controller.state == control.State.IDLE
            and gate.stopped
            and post_fault_zero_count >= 2
            and not unsafe_after_fault
            and nonzero_count > 0
        )
    return ScenarioResult(
        name=name,
        passed=passed,
        state=controller.state.value,
        reason=controller.reason,
        elapsed_s=elapsed_s,
        final_lateral_m=pose.y,
        final_heading_rad=pose.yaw,
        frame_count=frame_count,
        nonzero_request_count=nonzero_count,
        post_fault_zero_count=post_fault_zero_count,
        expected=expected,
    )


def run_validation(
    output_dir: pathlib.Path,
    step_s: float = 0.04,
    max_s: float = 55.0,
) -> dict[str, object]:
    """Write four synthetic scenario CSVs and one machine-readable summary.

    Args:
        output_dir: New directory; an existing path is never overwritten.
        step_s: Positive finite ideal integration interval in seconds.
        max_s: Positive finite budget permitting at least one simulation step.

    Returns:
        Summary containing scenario outcomes and overall passed status.

    Raises:
        ValueError: If the simulation interval or budget is invalid.
        FileExistsError: If the output path already exists.
        OSError: If output cannot be written.
    """
    if (
        isinstance(step_s, bool)
        or isinstance(max_s, bool)
        or not math.isfinite(step_s)
        or not math.isfinite(max_s)
        or step_s <= 0
        or max_s < step_s
    ):
        raise ValueError("Require finite step_s > 0 and max_s >= step_s")
    if max_s / step_s > 1_000_000:
        raise ValueError("Simulation budget exceeds one million steps")
    output_dir = pathlib.Path(output_dir)
    # 기존 시험 기록을 덮어쓰지 않고 매번 새 출력 폴더를 요구한다.
    output_dir.mkdir(parents=True, exist_ok=False)
    outcomes = [
        _run_scenario(name, output_dir / f"{name}.csv", step_s, max_s)
        for name in _SCENARIOS
    ]
    summary: dict[str, object] = {
        "schema_version": 1,
        "mode": "synthetic_command_validation",
        "physical_robot_tested": False,
        "ros_transport_tested": False,
        "physical_mux_tested": False,
        "renderer": "straight tape of fixed 10-pixel image thickness",
        "limitations": [
            "ideal planar odometry; no actuator lag or wheel slip",
            "no physical-width tape projection or real image noise model",
            "no full line follower, corner navigation, or interior mission",
            "software request gate is not a hardware emergency stop",
        ],
        "step_s": step_s,
        "max_s": max_s,
        "passed": all(result.passed for result in outcomes),
        "scenarios": [dataclasses.asdict(result) for result in outcomes],
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as output:
        json.dump(
            summary, output, ensure_ascii=False, indent=2, allow_nan=False
        )
        output.write("\n")
    return summary


def main(argv: list[str] | None = None) -> int:
    """Run headless validation; return nonzero on errors or failed scenarios."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    parser.add_argument("--step-s", type=float, default=0.04)
    parser.add_argument("--max-s", type=float, default=55.0)
    args = parser.parse_args(argv)
    try:
        summary = run_validation(args.output_dir, args.step_s, args.max_s)
    except (OSError, ValueError, RuntimeError) as error:
        LOGGER.error("Synthetic validation failed: %s", error)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
