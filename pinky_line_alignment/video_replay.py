"""Replay saved images or video into pixel-only black-tape observations.

This entry point never opens a camera, imports ROS, or requests motion.
Replay timestamps are derived from frame order, not hardware capture time.
"""

import argparse
import contextlib
import csv
import dataclasses
import hashlib
import json
import logging
import math
import pathlib
import platform
import sys
import time

import cv2
import numpy as np

from pinky_line_alignment import observation


LOGGER = logging.getLogger(__name__)
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"})
VIDEO_SUFFIXES = frozenset({".avi", ".mp4", ".mkv", ".mov", ".m4v", ".webm"})
METHODS = ("fixed", "otsu", "adaptive")
CSV_FIELDS = (
    "frame_index",
    "timestamp_s",
    "valid",
    "error_px",
    "ambiguous",
    "support",
    "reason",
    "processing_ms",
)


def load_options(path: pathlib.Path | None) -> dict[str, object]:
    """Load strict observation options; the CLI selects methods separately.

    Args:
        path: UTF-8 JSON object, or None to use observation defaults.

    Returns:
        Options accepted by ObservationConfig, excluding its method field.

    Raises:
        OSError: If the requested file cannot be read.
        ValueError: If JSON is not an object or contains unknown options.
    """
    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Replay config must be a JSON object")
    allowed = {
        field.name
        for field in dataclasses.fields(observation.ObservationConfig)
        if field.name != "method"
    }
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(
            "Unknown replay options: " + ", ".join(sorted(unknown))
        )
    return value


def _file_hash(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class _FrameSource:
    """Own file decoding and deterministic frame-order timestamps."""

    def __init__(self, path: pathlib.Path, image_fps: float) -> None:
        self.path = path
        self.fps = image_fps
        self.capture: cv2.VideoCapture | None = None
        self.images: list[pathlib.Path] = []
        self.first_frame: np.ndarray | None = None
        self.reported_count: int | None = None
        self.kind = "images"
        self.decoded_count = 0
        self.fps_from_video = False
        if "://" in str(path) or not path.exists():
            raise ValueError(
                "Input must be an existing local file or directory"
            )
        if path.is_dir():
            self.images = sorted(
                file
                for file in path.iterdir()
                if file.is_file() and file.suffix.lower() in IMAGE_SUFFIXES
            )
            if not self.images:
                raise ValueError("Input directory contains no supported images")
        elif path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            self.images = [path]
        elif path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES:
            self.kind = "video"
            self.capture = cv2.VideoCapture(str(path))
            if not self.capture.isOpened():
                self.close()
                raise ValueError("Input video cannot be opened")
            source_fps = float(self.capture.get(cv2.CAP_PROP_FPS))
            if math.isfinite(source_fps) and source_fps > 0:
                self.fps = source_fps
                self.fps_from_video = True
            count = float(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
            if math.isfinite(count) and count > 0:
                self.reported_count = int(count)
        else:
            raise ValueError(
                "Input extension is not a supported image or video"
            )
        if self.images:
            self.reported_count = len(self.images)
        try:
            self.first_frame = self._read_frame()
            if self.first_frame is None:
                raise ValueError("Input contains no decodable frames")
        except (ValueError, cv2.error):
            self.close()
            raise

    def fingerprint(self) -> dict[str, object]:
        """Hash encoded source bytes without retaining the source in memory."""
        if self.kind == "video":
            return {"name": self.path.name, "sha256": _file_hash(self.path)}
        entries = [
            {"name": path.name, "sha256": _file_hash(path)}
            for path in self.images
        ]
        encoded = json.dumps(entries, sort_keys=True).encode("utf-8")
        return {
            "name": self.path.name,
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "files": entries,
        }

    def _read_frame(self) -> np.ndarray | None:
        if self.capture is not None:
            ok, frame = self.capture.read()
            if not ok:
                # A codec header is not a perfect integrity proof; a short
                # decode relative to that header is still a useful failure.
                if (
                    self.reported_count is not None
                    and self.decoded_count < self.reported_count
                ):
                    raise ValueError(
                        "Video ended before its reported frame count"
                    )
                return None
        else:
            if self.decoded_count >= len(self.images):
                return None
            frame = cv2.imread(str(self.images[self.decoded_count]))
            if frame is None:
                raise ValueError("An input image cannot be decoded")
        if (
            frame is None
            or frame.dtype != np.uint8
            or frame.ndim != 3
            or frame.shape[2] != 3
        ):
            raise ValueError("Decoded frames must be uint8 BGR images")
        self.decoded_count += 1
        return frame

    def next_frame(self) -> np.ndarray | None:
        """Return a prefetched or newly decoded frame, or None at EOF."""
        if self.first_frame is not None:
            frame, self.first_frame = self.first_frame, None
            return frame
        return self._read_frame()

    def close(self) -> None:
        """Release the decoder if video input was selected."""
        if self.capture is not None:
            self.capture.release()


def _overlay(
    frame: np.ndarray, result: observation.FrameAnalysis
) -> np.ndarray:
    display = frame.copy()
    height, width = display.shape[:2]
    cv2.line(display, (width // 2, 0), (width // 2, height - 1), (255, 0, 0))
    for x_px, y_px in result.centers_px:
        cv2.circle(display, (round(x_px), round(y_px)), 3, (0, 200, 0), -1)
    error = "none" if result.error_px is None else f"{result.error_px:+.2f}px"
    cv2.putText(
        display,
        f"pixel-only error={error} valid={result.valid}",
        (5, min(18, height - 1)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (0, 0, 200),
        1,
    )
    return display


class _MethodOutput:
    """Own one method's artifacts and aggregate observed processing time."""

    def __init__(
        self,
        path: pathlib.Path,
        config: observation.ObservationConfig,
        stack: contextlib.ExitStack,
        fps: float,
        save_frames: bool,
        save_video: bool,
    ) -> None:
        path.mkdir()
        self.path = path
        self.config = config
        self.tracker = observation.PixelLineTracker(config)
        self.csv_file = stack.enter_context(
            (path / "frames.csv").open("w", newline="", encoding="utf-8")
        )
        self.csv = csv.DictWriter(self.csv_file, fieldnames=CSV_FIELDS)
        self.csv.writeheader()
        self.video: cv2.VideoWriter | None = None
        self.stack = stack
        self.fps = fps
        self.save_frames = save_frames
        self.save_video = save_video
        self.video_shape: tuple[int, int] | None = None
        self.valid_frames = 0
        self.ambiguous_frames = 0
        self.frame_count = 0
        self.total_ms = 0.0
        self.max_ms = 0.0
        self.reasons: dict[str, int] = {}
        if save_frames:
            (path / "frames").mkdir()

    def process(self, frame: np.ndarray, index: int) -> None:
        """Record one genuinely decoded frame in this method's own tracker."""
        timestamp_s = index / self.fps
        method_frame = frame.copy()
        start = time.perf_counter()
        result = self.tracker.process(method_frame, timestamp_s)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.csv.writerow(
            {
                "frame_index": index,
                "timestamp_s": f"{timestamp_s:.9f}",
                "valid": result.valid,
                "error_px": result.error_px,
                "ambiguous": result.ambiguous,
                "support": result.support,
                "reason": result.reason,
                "processing_ms": f"{elapsed_ms:.6f}",
            }
        )
        self.frame_count += 1
        self.valid_frames += int(result.valid)
        self.ambiguous_frames += int(result.ambiguous)
        self.total_ms += elapsed_ms
        self.max_ms = max(self.max_ms, elapsed_ms)
        self.reasons[result.reason] = self.reasons.get(result.reason, 0) + 1
        if self.save_frames or self.save_video:
            annotated = _overlay(frame, result)
            if self.save_frames:
                stem = self.path / "frames" / f"{index:06d}"
                mask_ok = cv2.imwrite(str(stem) + "_mask.png", result.mask)
                overlay_ok = cv2.imwrite(str(stem) + "_overlay.png", annotated)
                if not mask_ok or not overlay_ok:
                    raise OSError("Replay PNG output could not be written")
            if self.save_video:
                height, width = annotated.shape[:2]
                if height % 2 or width % 2:
                    raise ValueError(
                        "MJPG video output requires even frame dimensions"
                    )
                if self.video is None:
                    self.video = cv2.VideoWriter(
                        str(self.path / "annotated.avi"),
                        cv2.VideoWriter_fourcc(*"MJPG"),
                        self.fps,
                        (width, height),
                    )
                    self.stack.callback(self.video.release)
                    if not self.video.isOpened():
                        raise OSError("Replay video writer could not be opened")
                    self.video_shape = (height, width)
                if self.video_shape != (height, width):
                    raise ValueError(
                        "Video output requires constant frame sizes"
                    )
                self.video.write(annotated)

    def summary(self) -> dict[str, object]:
        """Report support counts without equating them to labeled accuracy."""
        config = dataclasses.asdict(self.config)
        config["roi"] = list(self.config.roi)
        return {
            "config": config,
            "processed_frames": self.frame_count,
            "valid_frames": self.valid_frames,
            "invalid_frames": self.frame_count - self.valid_frames,
            "ambiguous_frames": self.ambiguous_frames,
            "mean_processing_ms": self.total_ms / max(1, self.frame_count),
            "max_processing_ms": self.max_ms,
            "reasons": self.reasons,
            "accuracy_evaluated": False,
        }


def run_replay(
    input_path: pathlib.Path,
    output_dir: pathlib.Path,
    *,
    methods: tuple[str, ...] = METHODS,
    options: dict[str, object] | None = None,
    max_frames: int | None = None,
    save_frames: bool = False,
    save_video: bool = False,
    image_fps: float = 10.0,
) -> dict[str, object]:
    """Compare segmentation methods on the same saved source frames.

    Args:
        input_path: Existing local image, image directory, or saved video.
        output_dir: New artifact directory; existing paths are never replaced.
        methods: Unique names from fixed, otsu, and adaptive.
        options: ObservationConfig options other than method; None uses defaults.
        max_frames: Positive frame limit, or None to decode through EOF.
        save_frames: Save masks and annotated PNGs for each processed frame.
        save_video: Save an annotated AVI for each method.
        image_fps: Positive fallback frame rate for image sequences or bad FPS.

    Returns:
        JSON-compatible pixel-only summary, also saved to summary.json.

    Raises:
        ValueError: If configuration, decoding, or frame dimensions are invalid.
        OSError: If a source or output cannot be opened or written.
    """
    if not methods or len(set(methods)) != len(methods):
        raise ValueError("Select at least one unique method")
    if any(method not in METHODS for method in methods):
        raise ValueError("Methods must be fixed, otsu, or adaptive")
    if max_frames is not None and (
        type(max_frames) is not int or max_frames <= 0
    ):
        raise ValueError("max_frames must be a positive integer")
    if (
        isinstance(image_fps, bool)
        or not math.isfinite(image_fps)
        or image_fps <= 0
    ):
        raise ValueError("image_fps must be finite and positive")
    raw_options = {} if options is None else dict(options)
    allowed = {
        field.name
        for field in dataclasses.fields(observation.ObservationConfig)
        if field.name != "method"
    }
    if set(raw_options) - allowed:
        raise ValueError("Unknown observation options")
    configs = [
        observation.ObservationConfig(method=method, **raw_options)
        for method in methods
    ]
    if output_dir.exists():
        raise FileExistsError(
            "Output directory already exists; choose a new path"
        )
    with contextlib.ExitStack() as stack:
        source = _FrameSource(input_path, image_fps)
        stack.callback(source.close)
        fingerprint = source.fingerprint()
        # Validate decoding and parameters before creating persistent artifacts.
        output_dir.mkdir(parents=True, exist_ok=False)
        outputs = [
            _MethodOutput(
                output_dir / config.method,
                config,
                stack,
                source.fps,
                save_frames,
                save_video,
            )
            for config in configs
        ]
        count = 0
        try:
            while max_frames is None or count < max_frames:
                frame = source.next_frame()
                if frame is None:
                    break
                for output in outputs:
                    output.process(frame, count)
                count += 1
        except (ValueError, OSError, cv2.error) as error:
            failure = {
                "schema_version": "1.0",
                "status": "failed",
                "mode": "pixel_only_no_motion",
                "completed_frames": count,
                "error_type": type(error).__name__,
            }
            (output_dir / "summary.json").write_text(
                json.dumps(failure, indent=2), encoding="utf-8"
            )
            raise
        summary = {
            "schema_version": "1.0",
            "status": "completed",
            "mode": "pixel_only_no_motion",
            "input": fingerprint,
            "source_kind": source.kind,
            "source_fps": source.fps,
            "fps_from_video_metadata": source.fps_from_video,
            "reported_frame_count": source.reported_count,
            "timestamp_origin": "frame_index_divided_by_replay_fps",
            "hardware_capture_timestamps": False,
            "processed_frames": count,
            "frame_limit_reached": max_frames is not None
            and count == max_frames,
            "versions": {
                "python": platform.python_version(),
                "opencv": cv2.__version__,
                "numpy": np.__version__,
            },
            "methods": {
                output.config.method: output.summary() for output in outputs
            },
            "accuracy_evaluated": False,
            "physical_robot_validated": False,
        }
        (output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8"
        )
        return summary


def main(argv: list[str] | None = None) -> int:
    """Run the headless replay CLI and return a conventional exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=pathlib.Path)
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    parser.add_argument(
        "--methods", nargs="+", choices=METHODS, default=METHODS
    )
    parser.add_argument("--config", type=pathlib.Path)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--image-fps", type=float, default=10.0)
    parser.add_argument("--save-frames", action="store_true")
    parser.add_argument("--save-video", action="store_true")
    args = parser.parse_args(argv)
    try:
        summary = run_replay(
            args.input,
            args.output_dir,
            methods=tuple(args.methods),
            options=load_options(args.config),
            max_frames=args.max_frames,
            save_frames=args.save_frames,
            save_video=args.save_video,
            image_fps=args.image_fps,
        )
    except (ValueError, TypeError, OSError, cv2.error) as error:
        LOGGER.error("Replay failed; error_type=%s", type(error).__name__)
        print(f"Replay failed: {error}", file=sys.stderr)
        return 2
    print(
        f"Pixel-only replay completed: {summary['processed_frames']} frames. "
        "No robot motion was requested."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
