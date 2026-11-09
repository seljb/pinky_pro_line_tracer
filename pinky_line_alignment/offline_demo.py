"""Generate a fake camera image and observe extraction; NO robot / ROS
required.
"""

import argparse
import cv2
import numpy as np
from pinky_line_alignment.resource_paths import calibration_file
from pinky_line_alignment.vision import Calibration, LineDetector


def synthetic_image(offset_m: float = 0.09, slope: float = 0.18):
    """Render a synthetic dark line without opening a camera.

    Args:
        offset_m: Lateral offset in the synthetic ground model, in metres.
        slope: Dimensionless line slope in ground coordinates.

    Returns:
        A 480-by-640 BGR image for the synthetic calibration only."""
    img = np.full((480, 640, 3), 255, np.uint8)
    points = []
    for x in np.linspace(0.035, 0.47, 120):
        y = offset_m + slope * (x - 0.25)
        u = round(320 - 1000 * y)
        v = round(480 - 1000 * x)
        points.append((int(u), int(v)))
    cv2.polylines(img, [np.asarray(points, np.int32)], False, (9, 9, 9), 11)
    return img


def main():
    """Save a synthetic detection preview; never connect to a robot."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="pinky_alignment_preview.png")
    parser.add_argument("--offset-m", type=float, default=0.09)
    parser.add_argument("--slope", type=float, default=0.18)
    args = parser.parse_args()
    cal = Calibration.load(calibration_file("synthetic_calibration.json"))
    det = LineDetector(cal)
    img = synthetic_image(args.offset_m, args.slope)
    estimate = det.detect(img)
    if estimate is None:
        raise RuntimeError("Synthetic line not detected")
    cv2.putText(
        img,
        f"lateral={estimate.lateral_m:.3f}m yaw={np.degrees(estimate.heading_rad):.1f}deg",
        (15, 27),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 0, 255),
        2,
    )
    cv2.imwrite(args.output, img)
    print("OFFLINE ONLY:", estimate)
    print("Preview:", args.output)


if __name__ == "__main__":
    main()
