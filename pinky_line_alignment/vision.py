"""Extract a single dark tape line, fit its ground-plane tangent and displacement.

Ground convention: robot x = forward, y = left, metres. Pixel transforms must
be measured on *this* robot; a screenshot or URDF camera is insufficient.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import math
import cv2
import numpy as np


@dataclass(frozen=True)
class Calibration:
    """Store image-to-ground geometry and its validation metadata."""
    kind: str
    validated: bool
    H: np.ndarray
    polygon: np.ndarray
    width: int
    height: int
    K: np.ndarray | None = None
    D: np.ndarray | None = None
    rmse: float | None = None

    @staticmethod
    def load(path: str | Path) -> 'Calibration':
        """Load and check the geometry needed by the detector.

        Args:
            path: UTF-8 calibration JSON path.

        Returns:
            Calibration metadata; loading alone does not certify real motion.

        Raises:
            OSError: If the file cannot be read.
            ValueError: If JSON or checked calibration fields are invalid.
            KeyError: If a required calibration field is missing."""
        c = json.loads(Path(path).read_text(encoding='utf-8'))
        if c.get('homography_img_to_ground') is None:
            raise ValueError('No ground homography. Calibrate physical camera first.')
        H = np.asarray(c['homography_img_to_ground'], dtype=np.float64)
        if H.shape != (3, 3) or abs(np.linalg.det(H)) < 1e-13 or not np.isfinite(H).all():
            raise ValueError('Invalid 3x3 homography')
        polygon = np.asarray(c['floor_roi_pixels'], dtype=np.int32)
        if polygon.ndim != 2 or polygon.shape[1] != 2 or len(polygon) < 3:
            raise ValueError('floor_roi_pixels must have 3+ pixel points')
        K = None if c.get('camera_matrix') is None else np.asarray(c['camera_matrix'], dtype=np.float64)
        D = None if c.get('dist_coeffs') is None else np.asarray(c['dist_coeffs'], dtype=np.float64)
        if (K is None) != (D is None):
            raise ValueError('camera_matrix and dist_coeffs must be both present or absent')
        if K is not None and (K.shape != (3, 3) or D.size < 4):
            raise ValueError('Invalid camera intrinsics')
        return Calibration(c.get('calibration_type', 'unknown'), bool(c.get('validated', False)),
                           H, polygon, int(c['image_width']), int(c['image_height']), K, D,
                           c.get('ground_rmse_m'))


@dataclass(frozen=True)
class LineEstimate:
    """Describe a ground line in metres/radians, not success probability."""
    lateral_m: float
    heading_rad: float
    target_x_m: float
    target_y_m: float
    nearest_visible_dist_m: float
    count: int
    span_m: float
    quality: float


class LineDetector:
    """Extract one supported dark line using calibrated ground geometry."""
    def __init__(self, calibration: Calibration, threshold: int = 100,
                 row_step: int = 9, min_rows: int = 7, max_width_px: int = 68):
        """Initialize owned state and explicit runtime dependencies."""
        self.cal = calibration
        self.threshold = int(threshold)
        self.row_step = int(row_step)
        self.min_rows = int(min_rows)
        self.max_width_px = int(max_width_px)
        self.last_mask = None

    def detect(self, frame: np.ndarray) -> LineEstimate | None:
        """Estimate line position and tangent from a calibrated BGR image.

        Args:
            frame: Three-channel image at the calibration resolution.

        Returns:
            A ground estimate, or None if no supported line can be fitted.
            quality describes heuristic support, not measured robot accuracy.

        Raises:
            ValueError: If image dimensions disagree with the calibration.
            cv2.error: If OpenCV cannot process the supplied image."""
        if frame is None or frame.ndim != 3 or frame.shape[:2] != (self.cal.height, self.cal.width):
            raise ValueError('Frame size differs from calibration; recalibrate at this mode')
        img = cv2.undistort(frame, self.cal.K, self.cal.D) if self.cal.K is not None else frame
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mask = cv2.inRange(gray, 0, self.threshold)
        roi = np.zeros(mask.shape, dtype=np.uint8)
        cv2.fillPoly(roi, [self.cal.polygon], 255)
        mask = cv2.bitwise_and(mask, roi)
        # Remove isolated single-pixel noise without erasing thin tape.
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        best = None
        for index in range(1, n):
            x, y, w, h, area = (int(v) for v in stats[index])
            if area < 50 or h < self.row_step * (self.min_rows - 1):
                continue
            candidates = []
            for vv in range(y + 1, min(y + h, mask.shape[0]), self.row_step):
                uu = np.flatnonzero(labels[vv, x:x+w] == index)
                if len(uu) < 2 or len(uu) > self.max_width_px:
                    continue
                candidates.append((float(x + np.median(uu)), float(vv)))
            if len(candidates) < self.min_rows:
                continue
            # Prefer long, coherent curves; reject huge blobs.
            score = len(candidates) * 3 + math.sqrt(area) - max(0, w * h / max(area, 1) - 6)
            if best is None or score > best[0]:
                best = (score, candidates)
        self.last_mask = mask
        if best is None:
            return None
        pixels = np.asarray(best[1], dtype=np.float32).reshape(-1, 1, 2)
        # 픽셀 오차를 직접 제어하지 않고 실측 바닥 좌표(m)로 바꾼다.
        ground = cv2.perspectiveTransform(pixels, self.cal.H).reshape(-1, 2).astype(float)
        if not np.isfinite(ground).all():
            return None
        origin = ground.mean(axis=0)
        # SVD의 주축은 현재 관측된 선의 직선 접선 근사다.
        _, _, vt = np.linalg.svd(ground - origin)
        tangent = vt[0].copy()
        if tangent[0] < 0:
            tangent = -tangent
        span = np.ptp((ground - origin) @ tangent)
        if span < 0.06:   # Need meaningful tangent in ground metres.
            return None
        normal = np.array([-tangent[1], tangent[0]])
        lateral = float((-origin) @ normal)
        heading = float(math.atan2(tangent[1], tangent[0]))
        nearest = origin - np.dot(origin, tangent) * tangent
        # Short advance along the line avoids aiming straight at the wheels.
        target = nearest + 0.10 * tangent
        projections = (ground - origin) @ tangent
        target_projection = float((target - origin) @ tangent)
        outside = max(float(projections.min() - target_projection), 0.,
                      float(target_projection - projections.max()))
        if outside > 0.18:
            return None  # Do not navigate to a far extrapolated invisible line.
        # Distance from image-supported line to robot's current origin.
        nearest_visible = ground[np.argmin(np.linalg.norm(ground, axis=1))]
        quality = float(min(1., span / 0.2) * min(1., len(ground) / 12.))
        return LineEstimate(lateral, heading, float(target[0]), float(target[1]),
                            float(np.linalg.norm(nearest_visible)), len(ground), float(span), quality)
