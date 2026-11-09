"""Write a small labeled synthetic AVI, never a robot camera recording."""

import argparse
import csv
import logging
import math
import pathlib

import cv2
import numpy as np


LOGGER = logging.getLogger(__name__)


def make_clip(output: pathlib.Path, frame_count: int = 60) -> pathlib.Path:
    """Write synthetic scenes and a CSV of scene names without overwriting.

    Args:
        output: New .avi path; the parent directory may already exist.
        frame_count: Positive number of 320-by-240 frames at ten FPS.

    Returns:
        The new video path. Labels describe rendered scenes, not real accuracy.

    Raises:
        ValueError: If the format or count is invalid.
        OSError: If output files exist or a writer cannot be opened.
    """
    if output.suffix.lower() != ".avi":
        raise ValueError("Synthetic fixture requires an .avi output")
    if type(frame_count) is not int or not 1 <= frame_count <= 10000:
        raise ValueError("frame_count must be an integer from 1 to 10000")
    labels = output.with_suffix(".scenes.csv")
    if output.exists() or labels.exists():
        raise FileExistsError("Choose a new synthetic video and labels path")
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (320, 240)
    )
    try:
        if not writer.isOpened():
            raise OSError("Synthetic MJPG writer could not be opened")
        with labels.open("x", encoding="utf-8", newline="") as destination:
            rows = csv.writer(destination)
            rows.writerow(("frame_index", "timestamp_s", "synthetic_scene"))
            for index in range(frame_count):
                scene = (index * 4) // frame_count
                x_center = round(160 + 18 * math.sin(index / 10))
                gray = np.full((240, 320), 240, dtype=np.uint8)
                if scene == 2:
                    gradient = np.linspace(65, 240, 320, dtype=np.uint8)
                    gray[:] = gradient
                frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                name = "missing_line"
                if scene != 1:
                    points = np.array(
                        [(x_center, 239), (x_center + 8, 0)], np.int32
                    )
                    cv2.polylines(frame, [points], False, (8, 8, 8), 10)
                    name = "shaded_tape" if scene == 2 else "straight_tape"
                    if scene == 3:
                        cv2.line(
                            frame, (x_center, 110), (319, 110), (8, 8, 8), 12
                        )
                        name = "branch_candidate"
                writer.write(frame)
                rows.writerow((index, index / 10.0, name))
    finally:
        writer.release()
    return output


def main(argv: list[str] | None = None) -> int:
    """Create the fixture and return an error status on failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--frames", type=int, default=60)
    args = parser.parse_args(argv)
    try:
        make_clip(args.output, args.frames)
    except (ValueError, OSError, cv2.error) as error:
        LOGGER.error("Synthetic fixture failed; type=%s", type(error).__name__)
        return 2
    LOGGER.warning("Synthetic fixture only; no physical robot was tested")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
