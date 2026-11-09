"""Require actual synthetic feedback and meaningful zero-output fault checks."""

import csv
import json
import math
import pathlib

import pytest

from pinky_line_alignment import validation_run


def test_end_to_end_scenarios_and_current_csv_results(
    tmp_path: pathlib.Path,
) -> None:
    destination = tmp_path / "validation"
    report = validation_run.run_validation(destination)
    assert report["passed"] is True
    assert report["physical_robot_tested"] is False
    assert report["ros_transport_tested"] is False
    assert report == json.loads((destination / "summary.json").read_text())
    scenarios = {result["name"]: result for result in report["scenarios"]}
    assert set(scenarios) == {
        "align_left",
        "align_right",
        "camera_dropout",
        "operator_stop",
    }
    for name, result in scenarios.items():
        assert result["nonzero_request_count"] > 0
        with (destination / f"{name}.csv").open(newline="") as source:
            rows = list(csv.DictReader(source))
        assert len(rows) == result["frame_count"]
        assert rows[-1]["state"] == result["state"]
        if name.startswith("align_"):
            assert result["state"] == "READY"
            assert abs(result["final_lateral_m"]) < 0.015
            assert abs(result["final_heading_rad"]) < math.radians(6)
        else:
            state = "FAILED" if name == "camera_dropout" else "IDLE"
            stopped = [row for row in rows if row["state"] == state]
            assert stopped
            assert all(
                float(row["selected_linear_m_s"]) == 0 for row in stopped
            )
            assert all(
                float(row["selected_angular_rad_s"]) == 0 for row in stopped
            )


@pytest.mark.parametrize(
    ("step_s", "max_s"),
    [(0.0, 1.0), (-0.1, 1.0), (math.nan, 1.0), (0.1, math.inf), (1.0, 0.1)],
)
def test_invalid_simulation_budget_creates_no_output(
    tmp_path: pathlib.Path, step_s: float, max_s: float
) -> None:
    destination = tmp_path / "invalid"
    with pytest.raises(ValueError):
        validation_run.run_validation(destination, step_s=step_s, max_s=max_s)
    assert not destination.exists()


def test_existing_output_is_not_overwritten(tmp_path: pathlib.Path) -> None:
    marker = tmp_path / "marker.txt"
    marker.write_text("keep")
    with pytest.raises(FileExistsError):
        validation_run.run_validation(tmp_path)
    assert marker.read_text() == "keep"
    assert not (tmp_path / "summary.json").exists()


def test_cli_returns_failure_for_incomplete_scenarios(
    tmp_path: pathlib.Path,
) -> None:
    destination = tmp_path / "too-short"
    status = validation_run.main(
        [
            "--output-dir",
            str(destination),
            "--step-s",
            "0.04",
            "--max-s",
            "0.04",
        ]
    )
    assert status == 1
    summary = json.loads((destination / "summary.json").read_text())
    assert summary["passed"] is False
    assert not all(result["passed"] for result in summary["scenarios"])


def test_cli_reports_invalid_budget_without_success(
    tmp_path: pathlib.Path,
) -> None:
    destination = tmp_path / "invalid-cli"
    status = validation_run.main(
        ["--output-dir", str(destination), "--step-s", "nan"]
    )
    assert status == 2
    assert not destination.exists()
