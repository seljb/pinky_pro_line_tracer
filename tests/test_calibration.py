"""Test calibration behavior with synthetic inputs only."""

import numpy as np
import cv2
from pinky_line_alignment.calibration import floor, validate


def test_homography_holdout():
    """Check synthetic homography arithmetic and validation metadata."""
    H = np.array([[0, -0.001, 0.48], [-0.001, 0, 0.32], [0, 0, 1]], float)
    points = np.array(
        [[80, 60], [580, 60], [80, 450], [580, 450], [240, 220], [450, 350]],
        np.float32,
    )
    ground = cv2.perspectiveTransform(points.reshape(-1, 1, 2), H).reshape(
        -1, 2
    )
    pairs = {
        "pixel_points": points[:4].tolist(),
        "ground_xy_m": ground[:4].tolist(),
        "image_width": 640,
        "image_height": 480,
        "floor_roi_pixels": [[2, 2], [638, 2], [638, 478], [2, 478]],
    }
    d = floor(pairs)
    assert d["validated"] is False
    data = validate(
        d,
        {"pixel_points": points.tolist(), "ground_xy_m": ground.tolist()},
        0.015,
        True,
    )
    assert data["ground_rmse_m"] < 0.001
    assert data["validated"] is True
