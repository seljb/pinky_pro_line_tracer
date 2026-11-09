"""Check saved-file replay artifacts and meaningful failure boundaries."""

import csv
import json
import pathlib
import subprocess
import sys

import cv2
import numpy as np
import pytest

from pinky_line_alignment import video_replay


def _frame(x_px: int = 80, height: int = 120) -> np.ndarray:
    frame = np.full((height, 160, 3), 240, dtype=np.uint8)
    cv2.line(frame, (x_px, 10), (x_px, height - 1), (0, 0, 0), 9)
    return frame


def _image(path: pathlib.Path, x_px: int = 80, height: int = 120) -> None:
    if not cv2.imwrite(str(path), _frame(x_px, height)):
        raise RuntimeError("Test image could not be written")


def _video(path: pathlib.Path, frame_count: int = 4) -> None:
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (160, 120)
    )
    try:
        if not writer.isOpened():
            raise RuntimeError("Test MJPG writer is not available")
        for index in range(frame_count):
            writer.write(_frame(70 + index))
    finally:
        writer.release()


def _csv_rows(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def test_image_comparison_has_separate_pixel_reports(tmp_path: pathlib.Path):
    """Process one frame through every method with identifiable artifacts."""
    source = tmp_path / "input.png"
    _image(source, 55)
    output = tmp_path / "output"
    summary = video_replay.run_replay(source, output, save_frames=True)
    assert summary["status"] == "completed"
    assert summary["mode"] == "pixel_only_no_motion"
    assert summary["processed_frames"] == 1
    assert summary["accuracy_evaluated"] is False
    assert summary["physical_robot_validated"] is False
    assert len(summary["input"]["sha256"]) == 64
    assert json.loads((output / "summary.json").read_text()) == summary
    assert set(summary["methods"]) == set(video_replay.METHODS)
    for method in video_replay.METHODS:
        rows = _csv_rows(output / method / "frames.csv")
        assert len(rows) == 1
        assert tuple(rows[0]) == video_replay.CSV_FIELDS
        assert float(rows[0]["timestamp_s"]) == 0.0
        assert float(rows[0]["processing_ms"]) >= 0.0
        mask = cv2.imread(
            str(output / method / "frames" / "000000_mask.png"),
            cv2.IMREAD_GRAYSCALE,
        )
        assert mask is not None
        assert mask[90, 55] == 255
        assert mask[90, 130] == 0
        assert (output / method / "frames" / "000000_overlay.png").is_file()


def test_blank_image_records_missing_observation(tmp_path: pathlib.Path):
    """A valid source without a line records absence instead of an error."""
    source = tmp_path / "white.jpg"
    assert cv2.imwrite(str(source), np.full((120, 160, 3), 255, np.uint8))
    output = tmp_path / "output"
    summary = video_replay.run_replay(source, output, methods=("fixed",))
    row = _csv_rows(output / "fixed" / "frames.csv")[0]
    assert row["valid"] == "False"
    assert row["error_px"] == ""
    assert summary["methods"]["fixed"]["invalid_frames"] == 1


def test_image_sequence_order_and_limit_are_reproducible(
    tmp_path: pathlib.Path,
):
    """Sort input names, limit processing, and fingerprint all source images."""
    source = tmp_path / "images"
    source.mkdir()
    _image(source / "b.png", 110)
    _image(source / "a.png", 50)
    output = tmp_path / "output"
    summary = video_replay.run_replay(
        source,
        output,
        methods=("fixed",),
        max_frames=1,
        image_fps=5.0,
    )
    assert summary["processed_frames"] == 1
    assert summary["reported_frame_count"] == 2
    assert summary["frame_limit_reached"] is True
    assert [item["name"] for item in summary["input"]["files"]] == [
        "a.png",
        "b.png",
    ]
    rows = _csv_rows(output / "fixed" / "frames.csv")
    assert len(rows) == 1
    assert float(rows[0]["error_px"]) < 0


def test_video_replay_writes_a_decodable_annotated_video(
    tmp_path: pathlib.Path,
):
    """Exercise actual file decoding and video encoding through EOF."""
    source = tmp_path / "input.avi"
    _video(source)
    output = tmp_path / "output"
    summary = video_replay.run_replay(
        source, output, methods=("fixed",), save_video=True
    )
    assert summary["source_kind"] == "video"
    assert summary["processed_frames"] == 4
    assert summary["fps_from_video_metadata"] is True
    rows = _csv_rows(output / "fixed" / "frames.csv")
    assert [float(row["timestamp_s"]) for row in rows] == [0, 0.1, 0.2, 0.3]
    capture = cv2.VideoCapture(str(output / "fixed" / "annotated.avi"))
    try:
        decoded = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            assert frame.shape == (120, 160, 3)
            decoded += 1
        assert decoded == 4
    finally:
        capture.release()


@pytest.mark.parametrize("name", ["missing.png", "corrupt.png", "wrong.txt"])
def test_invalid_source_does_not_create_output(
    tmp_path: pathlib.Path, name: str
):
    """Reject missing, damaged, and unsupported inputs before artifact creation."""
    source = tmp_path / name
    if name != "missing.png":
        source.write_text("not an image", encoding="utf-8")
    output = tmp_path / "output"
    with pytest.raises(ValueError):
        video_replay.run_replay(source, output)
    assert not output.exists()


def test_empty_image_directory_is_not_a_success(tmp_path: pathlib.Path):
    """A zero-frame source cannot pass readiness validation."""
    source = tmp_path / "empty"
    source.mkdir()
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="no supported images"):
        video_replay.run_replay(source, output)
    assert not output.exists()


def test_existing_output_is_preserved(tmp_path: pathlib.Path):
    """Refuse overwriting outputs even when the source is valid."""
    source = tmp_path / "input.png"
    _image(source)
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "keep.txt"
    marker.write_text("user content", encoding="utf-8")
    with pytest.raises(FileExistsError):
        video_replay.run_replay(source, output)
    assert marker.read_text() == "user content"
    assert sorted(path.name for path in output.iterdir()) == ["keep.txt"]


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_frame_limit_is_rejected(tmp_path: pathlib.Path, value: object):
    """Do not silently accept boolean, fractional, or nonpositive limits."""
    with pytest.raises(ValueError, match="max_frames"):
        video_replay.run_replay(
            tmp_path / "unused.png", tmp_path / "output", max_frames=value
        )


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True])
def test_invalid_fallback_fps_is_rejected(tmp_path: pathlib.Path, value: float):
    """Replay timestamps require a finite positive frame rate."""
    with pytest.raises(ValueError, match="image_fps"):
        video_replay.run_replay(
            tmp_path / "unused.png", tmp_path / "output", image_fps=value
        )


@pytest.mark.parametrize("methods", [(), ("fixed", "fixed"), ("unknown",)])
def test_invalid_method_selection_is_rejected(
    tmp_path: pathlib.Path, methods: tuple[str, ...]
):
    """Reject duplicate and unknown methods before creating artifacts."""
    with pytest.raises(ValueError):
        video_replay.run_replay(
            tmp_path / "unused.png", tmp_path / "output", methods=methods
        )


@pytest.mark.parametrize(
    "config", ['{"threshold_typo": 4}', '{"method": "fixed"}', "[]", "{"]
)
def test_config_json_is_strict(tmp_path: pathlib.Path, config: str):
    """Misspelled options must not silently change the comparison."""
    path = tmp_path / "config.json"
    path.write_text(config, encoding="utf-8")
    with pytest.raises(ValueError):
        video_replay.load_options(path)


def test_invalid_observation_options_do_not_create_output(
    tmp_path: pathlib.Path,
):
    """Validate segmentation options before decoding or writing files."""
    output = tmp_path / "output"
    with pytest.raises(ValueError):
        video_replay.run_replay(
            tmp_path / "unused.png", output, options={"threshold": -1}
        )
    assert not output.exists()


def test_later_corrupt_frame_marks_output_as_failed(tmp_path: pathlib.Path):
    """Preserve partial diagnostics while clearly marking an incomplete run."""
    source = tmp_path / "images"
    source.mkdir()
    _image(source / "a.png")
    (source / "b.png").write_text("corrupt", encoding="utf-8")
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="cannot be decoded"):
        video_replay.run_replay(source, output, methods=("fixed",))
    failure = json.loads((output / "summary.json").read_text())
    assert failure["status"] == "failed"
    assert failure["completed_frames"] == 1
    assert len(_csv_rows(output / "fixed" / "frames.csv")) == 1


def test_changed_dimensions_fail_video_output_and_close_writer(
    tmp_path: pathlib.Path,
):
    """A mixed image sequence cannot silently create malformed video."""
    source = tmp_path / "images"
    source.mkdir()
    _image(source / "a.png")
    _image(source / "b.png", height=140)
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="constant frame sizes"):
        video_replay.run_replay(
            source, output, methods=("fixed",), save_video=True
        )
    failure = json.loads((output / "summary.json").read_text())
    assert failure["status"] == "failed"
    capture = cv2.VideoCapture(str(output / "fixed" / "annotated.avi"))
    try:
        assert capture.read()[0]
    finally:
        capture.release()


def test_odd_video_dimensions_are_not_silently_cropped(tmp_path: pathlib.Path):
    """Reject codec dimensions that MJPG may otherwise truncate silently."""
    source = tmp_path / "odd.png"
    _image(source, height=121)
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="even frame dimensions"):
        video_replay.run_replay(
            source, output, methods=("fixed",), save_video=True
        )
    assert (
        json.loads((output / "summary.json").read_text())["status"] == "failed"
    )


def test_cli_exit_status_and_report(tmp_path: pathlib.Path):
    """Run the public module entry point without ROS or desktop access."""
    source = tmp_path / "input.png"
    _image(source)
    output = tmp_path / "output"
    command = [
        sys.executable,
        "-m",
        "pinky_line_alignment.video_replay",
        "--input",
        str(source),
        "--output-dir",
        str(output),
        "--methods",
        "fixed",
    ]
    result = subprocess.run(
        command, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "No robot motion was requested" in result.stdout
    repeated = subprocess.run(
        command, capture_output=True, text=True, check=False
    )
    assert repeated.returncode == 2
    assert "already exists" in repeated.stderr
