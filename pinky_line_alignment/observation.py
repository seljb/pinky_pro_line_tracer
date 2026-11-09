"""Observe dark tape in pixel space without device or motion access.

Coordinates use image x-right/y-down pixels. A valid observation is not a
physical calibration, path decision, or proof that driving is safe.
"""

import dataclasses
import math
import numbers

import cv2
import numpy as np


@dataclasses.dataclass(frozen=True)
class ObservationConfig:
    """Configure segmentation and conservative image-space path selection.

    ROI coordinates are normalized left, top, right, bottom fractions. Pixel
    limits and default values are development settings, not robot measurements.
    """

    method: str = "fixed"
    threshold: int = 100
    roi: tuple[float, float, float, float] = (0.0, 0.25, 1.0, 1.0)
    blur_size: int = 3
    open_size: int = 0
    close_size: int = 0
    sample_count: int = 9
    max_run_fraction: float = 0.22
    max_step_fraction: float = 0.12
    ambiguity_margin_fraction: float = 0.04
    min_support: int = 5
    max_gap_s: float = 0.5
    adaptive_block_size: int = 31
    adaptive_c: float = 7.0
    min_run_px: int = 2
    min_contrast_gray: float = 10.0

    def __post_init__(self) -> None:
        """Reject invalid configuration before any frame is processed.

        Raises:
            ValueError: If a method, ROI, size, or numeric bound is invalid.
        """
        if not isinstance(self.method, str) or self.method not in {
            "fixed",
            "otsu",
            "adaptive",
        }:
            raise ValueError("method must be fixed, otsu, or adaptive")
        _check_integer("threshold", self.threshold, 0, 255)
        for name in ("blur_size", "open_size", "close_size"):
            size = getattr(self, name)
            _check_integer(name, size, 0, 101)
            if size != 0 and size % 2 == 0:
                raise ValueError(f"{name} must be zero or an odd integer")
        _check_integer("sample_count", self.sample_count, 3, 101)
        _check_integer("min_support", self.min_support, 2, self.sample_count)
        _check_integer("min_run_px", self.min_run_px, 1, 1000)
        _check_integer("adaptive_block_size", self.adaptive_block_size, 3, 501)
        if self.adaptive_block_size % 2 == 0:
            raise ValueError("adaptive_block_size must be odd")
        if not isinstance(self.roi, (tuple, list)) or len(self.roi) != 4:
            raise ValueError("roi must contain left, top, right, bottom")
        bounds = tuple(_finite_number("roi", v) for v in self.roi)
        left, top, right, bottom = bounds
        if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
            raise ValueError("roi must be ordered normalized bounds in [0,1]")
        object.__setattr__(self, "roi", bounds)
        for name in (
            "max_run_fraction",
            "max_step_fraction",
            "ambiguity_margin_fraction",
        ):
            value = _finite_number(name, getattr(self, name))
            if not 0 < value <= 1:
                raise ValueError(f"{name} must be in (0,1]")
        if _finite_number("max_gap_s", self.max_gap_s) <= 0:
            raise ValueError("max_gap_s must be positive")
        _finite_number("adaptive_c", self.adaptive_c)
        contrast = _finite_number("min_contrast_gray", self.min_contrast_gray)
        if not 0 < contrast <= 255:
            raise ValueError("min_contrast_gray must be in (0,255]")


@dataclasses.dataclass(frozen=True)
class FrameAnalysis:
    """Return segmentation and fresh pixel observations for one frame.

    mask is a full-size uint8 image with dark-tape candidates marked 255.
    centers_px contains selected (x,y) samples ordered near to far. error_px
    is None whenever valid is False. support counts selected sample rows;
    it is not a success probability or a physical accuracy measurement.
    """

    mask: np.ndarray
    centers_px: tuple[tuple[float, float], ...]
    error_px: float | None
    valid: bool
    reason: str
    ambiguous: bool
    support: int


def _finite_number(name: str, value: object) -> float:
    """Return a finite scalar while rejecting strings and booleans."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _check_integer(name: str, value: object, low: int, high: int) -> None:
    """Reject non-integral sizes and values outside inclusive limits."""
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Integral)
        or not low <= value <= high
    ):
        raise ValueError(f"{name} must be an integer in [{low},{high}]")


def _runs(row: np.ndarray, min_width_px: int) -> list[tuple[int, int]]:
    """Return inclusive bounds of separate foreground runs in one mask row."""
    edges = np.diff(np.pad(row > 0, (1, 1)).astype(np.int8))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1) - 1
    return [
        (int(left), int(right))
        for left, right in zip(starts, ends)
        if right - left + 1 >= min_width_px
    ]


class PixelLineTracker:
    """Own one temporal reference and reject ambiguous image-space paths."""

    def __init__(self, config: ObservationConfig) -> None:
        """Create a tracker without opening a camera or changing global state.

        Args:
            config: Validated segmentation and path-selection configuration.

        Raises:
            TypeError: If config is not an ObservationConfig.
        """
        if not isinstance(config, ObservationConfig):
            raise TypeError("config must be an ObservationConfig")
        self.config = config
        self._last_time_s: float | None = None
        self._near_x_px: float | None = None
        self._frame_shape: tuple[int, int] | None = None

    def reset(self) -> None:
        """Explicitly start a new clock epoch and discard the old path."""
        self._last_time_s = None
        self._discard_path()

    def _discard_path(self) -> None:
        """Clear image-space history while retaining the time high-water mark."""
        self._near_x_px = None
        self._frame_shape = None

    def _mask(self, frame: np.ndarray) -> tuple[np.ndarray, tuple[int, ...]]:
        """Build a full-frame candidate mask and integer ROI bounds."""
        height, width = frame.shape[:2]
        left, top, right, bottom = self.config.roi
        x0, y0 = math.floor(left * width), math.floor(top * height)
        x1, y1 = math.ceil(right * width), math.ceil(bottom * height)
        gray = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
        if self.config.blur_size > 1:
            gray = cv2.GaussianBlur(
                gray, (self.config.blur_size, self.config.blur_size), 0
            )
        if self.config.method == "adaptive":
            local = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                self.config.adaptive_block_size,
                self.config.adaptive_c,
            )
        else:
            mode = cv2.THRESH_BINARY_INV
            if self.config.method == "otsu":
                mode |= cv2.THRESH_OTSU
            _, local = cv2.threshold(gray, self.config.threshold, 255, mode)
        for size, operation in (
            (self.config.open_size, cv2.MORPH_OPEN),
            (self.config.close_size, cv2.MORPH_CLOSE),
        ):
            if size > 1:
                kernel = np.ones((size, size), dtype=np.uint8)
                local = cv2.morphologyEx(local, operation, kernel)
        mask = np.zeros((height, width), dtype=np.uint8)
        mask[y0:y1, x0:x1] = local
        return mask, (x0, y0, x1, y1)

    def _has_dark_contrast(
        self,
        gray: np.ndarray,
        row: int,
        left: int,
        right: int,
        roi_left: int,
        roi_right: int,
    ) -> bool:
        """Require a dark run to have brighter source pixels on both sides."""
        shoulder_width = max(2, min(5, (right - left + 1) // 2))
        if left - shoulder_width < roi_left or (
            right + 1 + shoulder_width > roi_right
        ):
            return False
        center_gray = float(np.median(gray[row, left : right + 1]))
        left_gray = float(np.median(gray[row, left - shoulder_width : left]))
        right_gray = float(
            np.median(gray[row, right + 1 : right + 1 + shoulder_width])
        )
        # 넓은 그림자의 한쪽 경계는 검은 테이프의 양쪽 경계가 아니다.
        return min(left_gray, right_gray) - center_gray >= (
            self.config.min_contrast_gray
        )

    def _invalid(
        self,
        mask: np.ndarray,
        reason: str,
        ambiguous: bool = False,
        centers: tuple[tuple[float, float], ...] = (),
    ) -> FrameAnalysis:
        """Clear the prior path and return no usable error for this frame."""
        self._discard_path()
        return FrameAnalysis(
            mask, centers, None, False, reason, ambiguous, len(centers)
        )

    def process(self, frame: np.ndarray, timestamp_s: float) -> FrameAnalysis:
        """Analyze one fresh BGR uint8 frame without producing motor requests.

        Args:
            frame: Nonempty H-by-W-by-3 BGR uint8 image.
            timestamp_s: Finite nonnegative monotonic frame time, in seconds.

        Returns:
            A mask and fresh observations. Ambiguous, missing, repeated-time,
            or backward-time frames have no usable error. Gaps discard the
            temporal reference; only the actual new image can reacquire it.
            Invalid input preserves the accepted time high-water mark. Only
            reset() permits a new clock epoch.

        Raises:
            ValueError: If frame format or timestamp is invalid.
        """
        try:
            now_s = _finite_number("timestamp_s", timestamp_s)
            if now_s < 0:
                raise ValueError("timestamp_s must be nonnegative")
            if (
                not isinstance(frame, np.ndarray)
                or frame.dtype != np.uint8
                or frame.ndim != 3
                or frame.shape[2] != 3
                or min(frame.shape[:2]) < 2
            ):
                raise ValueError("frame must be a nonempty BGR uint8 image")
        except ValueError:
            self._discard_path()
            raise
        mask, (x0, y0, x1, y1) = self._mask(frame)
        if self._last_time_s is not None and now_s <= self._last_time_s:
            return self._invalid(mask, "nonmonotonic_time")
        if (
            self._last_time_s is None
            or now_s - self._last_time_s > self.config.max_gap_s
            or frame.shape[:2] != self._frame_shape
        ):
            self._near_x_px = None
        self._last_time_s = now_s
        self._frame_shape = frame.shape[:2]
        width = frame.shape[1]
        # 코너의 가로 선분은 표본 행 사이에도 있을 수 있어 모든 ROI 행을 본다.
        rows = {
            y: _runs(mask[y, x0:x1], self.config.min_run_px)
            for y in range(y0, y1)
        }
        max_width_px = (x1 - x0) * self.config.max_run_fraction
        if any(
            right - left + 1 > max_width_px
            for runs in rows.values()
            for left, right in runs
        ):
            return self._invalid(mask, "wide_region_or_corner", True)
        sample_rows = np.unique(
            np.linspace(y1 - 1, y0, self.config.sample_count).astype(int)
        )[::-1]
        _, labels = cv2.connectedComponents(mask, connectivity=8)
        source_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        centers: list[tuple[float, float]] = []
        selected_component: int | None = None
        contrast_rejected = False
        reference_x = self._near_x_px
        limit_px = width * self.config.max_step_fraction
        margin_px = width * self.config.ambiguity_margin_fraction
        for y in sample_rows:
            candidates = []
            for left, right in rows[int(y)]:
                if self._has_dark_contrast(
                    source_gray, int(y), left + x0, right + x0, x0, x1
                ):
                    candidates.append((left + right) / 2 + x0)
                else:
                    contrast_rejected = True
            if not candidates:
                continue
            anchor = width / 2 if reference_x is None else reference_x
            candidates.sort(key=lambda x: abs(x - anchor))
            nearest = candidates[0]
            # 두 가지를 평균하면 실제로 없는 선을 관측했다고 오인하게 된다.
            if len(candidates) > 1:
                first_distance = abs(nearest - anchor)
                second_distance = abs(candidates[1] - anchor)
                if (
                    second_distance - first_distance <= margin_px
                    or second_distance <= limit_px
                ):
                    return self._invalid(
                        mask, "multiple_paths", True, tuple(centers)
                    )
            if reference_x is not None and abs(nearest - anchor) > limit_px:
                return self._invalid(
                    mask, "path_discontinuity", True, tuple(centers)
                )
            component = int(labels[int(y), math.floor(nearest)])
            if selected_component is not None and component != (
                selected_component
            ):
                return self._invalid(
                    mask, "disconnected_path", True, tuple(centers)
                )
            selected_component = component
            centers.append((float(nearest), float(y)))
            reference_x = nearest
        if len(centers) < self.config.min_support:
            return self._invalid(
                mask,
                (
                    "insufficient_contrast"
                    if contrast_rejected
                    else "insufficient_support"
                ),
                False,
                tuple(centers),
            )
        self._near_x_px = centers[0][0]
        # 화면 중앙 기준 오차는 픽셀 단위이며 차체의 실제 거리가 아니다.
        error_px = centers[0][0] - width / 2
        return FrameAnalysis(
            mask, tuple(centers), error_px, True, "tracked", False, len(centers)
        )
