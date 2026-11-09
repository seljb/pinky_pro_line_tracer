"""Check dark-tape observations without a robot, ROS, or real calibration."""

import dataclasses

import cv2
import numpy as np
import pytest

from pinky_line_alignment import observation


def _frame(center_x: int = 80, width_px: int = 10) -> np.ndarray:
    """Return a synthetic 160-by-120 image with one vertical tape."""
    frame = np.full((120, 160, 3), 240, dtype=np.uint8)
    left = center_x - width_px // 2
    frame[:, left : left + width_px] = 10
    return frame


def _tracker(**kwargs: object) -> observation.PixelLineTracker:
    """Construct a tracker with explicit test configuration changes."""
    return observation.PixelLineTracker(observation.ObservationConfig(**kwargs))


@pytest.mark.parametrize("method", ["fixed", "otsu", "adaptive"])
def test_methods_find_dark_tape_and_preserve_full_mask(method: str) -> None:
    """Each method must identify a supported synthetic black line."""
    result = _tracker(method=method).process(_frame(100), 0.0)
    assert result.valid, result.reason
    assert result.error_px == pytest.approx(19.5, abs=1)
    assert result.mask.shape == (120, 160)
    assert result.mask.dtype == np.uint8
    assert result.mask[90, 100] == 255
    assert result.mask[90, 30] == 0
    assert np.count_nonzero(result.mask[:30]) == 0
    assert result.support == len(result.centers_px) == 9
    assert result.centers_px[0][1] > result.centers_px[-1][1]


@pytest.mark.parametrize("center_x,sign", [(45, -1), (115, 1)])
def test_pixel_error_has_expected_image_sign(center_x: int, sign: int) -> None:
    """Right-of-centre tape must have a positive pixel error."""
    result = _tracker().process(_frame(center_x), 1.0)
    assert result.valid
    assert result.error_px is not None and result.error_px * sign > 0


@pytest.mark.parametrize("method", ["fixed", "otsu", "adaptive"])
def test_uniform_white_has_no_usable_error(method: str) -> None:
    """A missing line must not reuse a previous valid observation."""
    tracker = _tracker(method=method)
    assert tracker.process(_frame(95), 0.0).valid
    result = tracker.process(np.full((120, 160, 3), 240, np.uint8), 0.1)
    assert not result.valid
    assert result.error_px is None
    assert result.reason == "insufficient_support"
    assert result.support == 0


def test_roi_offsets_are_restored_to_full_image_coordinates() -> None:
    """Cropping must not compare a local x coordinate with full-image centre."""
    result = _tracker(roi=(0.25, 0.25, 0.9, 1.0)).process(_frame(110), 0.0)
    assert result.valid
    assert result.error_px == pytest.approx(29.5)
    assert result.centers_px[0][0] == pytest.approx(109.5)
    assert not result.mask[:, :40].any()


def test_line_outside_roi_is_not_observed() -> None:
    """Only the explicitly selected floor region contributes candidates."""
    result = _tracker(roi=(0.3, 0.25, 1.0, 1.0)).process(_frame(20), 0.0)
    assert not result.valid
    assert result.error_px is None


def test_equal_competing_paths_are_not_averaged() -> None:
    """Two plausible branches must not create a nonexistent centre line."""
    frame = _frame(45)
    frame[:, 110:120] = 10
    result = _tracker().process(frame, 0.0)
    assert not result.valid
    assert result.ambiguous
    assert result.reason == "multiple_paths"
    assert result.error_px is None


def test_temporal_reference_preserves_the_same_distinct_path() -> None:
    """A distant competing line must not replace an established nearby path."""
    tracker = _tracker()
    assert tracker.process(_frame(115), 0.0).valid
    frame = _frame(115)
    frame[:, 40:50] = 10
    result = tracker.process(frame, 0.1)
    assert result.valid
    assert result.centers_px[0][0] == pytest.approx(114.5)


def test_large_temporal_jump_is_rejected() -> None:
    """A new distant object must not silently continue the tracked tape."""
    tracker = _tracker()
    assert tracker.process(_frame(45), 0.0).valid
    result = tracker.process(_frame(115), 0.1)
    assert not result.valid and result.ambiguous
    assert result.reason == "path_discontinuity"
    assert result.error_px is None


def test_reset_discards_previous_path_and_clock() -> None:
    """Explicit reset must allow a new stream to begin at time zero."""
    tracker = _tracker()
    assert tracker.process(_frame(45), 10.0).valid
    tracker.reset()
    result = tracker.process(_frame(115), 0.0)
    assert result.valid
    assert result.error_px == pytest.approx(34.5)


def test_long_gap_does_not_reuse_temporal_path() -> None:
    """A genuinely new frame after a gap must be reacquired from its pixels."""
    tracker = _tracker()
    assert tracker.process(_frame(45), 0.0).valid
    result = tracker.process(_frame(115), 1.0)
    assert result.valid
    assert result.error_px == pytest.approx(34.5)


@pytest.mark.parametrize("timestamp_s", [0.5, 1.0])
def test_nonmonotonic_frame_returns_no_observation(timestamp_s: float) -> None:
    """Repeated or backward time is invalid even if its pixels look usable."""
    tracker = _tracker()
    assert tracker.process(_frame(), 1.0).valid
    result = tracker.process(_frame(115), timestamp_s)
    assert not result.valid
    assert result.reason == "nonmonotonic_time"
    assert result.error_px is None and result.centers_px == ()


@pytest.mark.parametrize("invalid_time_s", [9.0, 10.0])
def test_clock_regression_preserves_the_accepted_high_water_mark(
    invalid_time_s: float,
) -> None:
    """A rejected timestamp must not open an older clock epoch implicitly."""
    tracker = _tracker()
    assert tracker.process(_frame(45), 10.0).valid
    result = tracker.process(_frame(115), invalid_time_s)
    assert not result.valid and result.reason == "nonmonotonic_time"
    still_old = tracker.process(_frame(115), 9.1)
    assert not still_old.valid and still_old.error_px is None
    recovered = tracker.process(_frame(115), 10.1)
    assert recovered.valid
    assert recovered.error_px == pytest.approx(34.5)


@pytest.mark.parametrize("bad_kind", ["image", "time"])
def test_malformed_input_cannot_reset_the_accepted_clock(bad_kind: str) -> None:
    """Image/time validation errors clear the path but preserve clock history."""
    tracker = _tracker()
    assert tracker.process(_frame(45), 10.0).valid
    with pytest.raises(ValueError):
        if bad_kind == "image":
            tracker.process(np.zeros((10, 10), np.uint8), 9.0)
        else:
            tracker.process(_frame(), float("nan"))
    still_old = tracker.process(_frame(115), 9.1)
    assert not still_old.valid and still_old.reason == "nonmonotonic_time"
    assert still_old.error_px is None
    assert tracker.process(_frame(115), 10.1).valid


def test_frame_size_change_does_not_reuse_pixel_reference() -> None:
    """A changed resolution must start with a new pixel-coordinate reference."""
    tracker = _tracker()
    assert tracker.process(_frame(45), 0.0).valid
    bigger = cv2.resize(_frame(115), (320, 240))
    result = tracker.process(bigger, 0.1)
    assert result.valid
    assert result.error_px is not None and result.error_px > 60


@pytest.mark.parametrize("shape", ["corner", "tee", "solid"])
def test_wide_corner_branch_and_solid_blobs_are_rejected(shape: str) -> None:
    """Broad horizontal geometry must not become a diagonal straight path."""
    frame = _frame()
    if shape == "corner":
        frame[58:65, 75:145] = 10
    elif shape == "tee":
        frame[58:65, 20:145] = 10
    else:
        frame[30:] = 10
    result = _tracker().process(frame, 0.0)
    assert not result.valid and result.ambiguous
    assert result.reason == "wide_region_or_corner"
    assert result.error_px is None


@pytest.mark.parametrize("method", ["fixed", "otsu", "adaptive"])
def test_wide_dark_region_edge_is_not_a_thin_tape(method: str) -> None:
    """Adaptive edge masks must not turn a large dark region into a tape."""
    frame = np.full((120, 160, 3), 240, np.uint8)
    frame[:, :100] = 10
    result = _tracker(method=method).process(frame, 0.0)
    assert not result.valid
    assert result.error_px is None
    if method == "adaptive":
        assert result.reason == "insufficient_contrast"
    else:
        assert result.reason == "wide_region_or_corner"


@pytest.mark.parametrize("edge_x", [2, 157])
def test_roi_edge_without_two_visible_shoulders_is_rejected(
    edge_x: int,
) -> None:
    """A partially visible boundary has insufficient bilateral evidence."""
    frame = _frame(edge_x, width_px=4)
    result = _tracker(blur_size=0).process(frame, 0.0)
    assert not result.valid and result.error_px is None


def test_aligned_disconnected_stripes_cannot_form_one_observed_path() -> None:
    """Five isolated fragments at sample rows must not masquerade as tape."""
    frame = np.full((120, 160, 3), 240, np.uint8)
    for row in (119, 107, 96, 85, 74):
        frame[max(0, row - 1) : min(120, row + 2), 75:85] = 10
    result = _tracker(blur_size=0).process(frame, 0.0)
    assert not result.valid and result.ambiguous
    assert result.reason == "disconnected_path"
    assert result.error_px is None


def test_configured_closing_can_reconnect_actual_mask_components() -> None:
    """Connectivity applies to the configured processed mask, not raw labels."""
    frame = np.full((120, 160, 3), 240, np.uint8)
    for row in (119, 107, 96, 85, 74):
        frame[max(0, row - 1) : min(120, row + 2), 75:85] = 10
    result = _tracker(blur_size=0, close_size=11).process(frame, 0.0)
    assert result.valid, result.reason
    assert result.support >= 5
    assert result.error_px == pytest.approx(-0.5)


def test_thin_seam_is_excluded_by_minimum_run_width() -> None:
    """A one-pixel seam must not become a second supported path."""
    frame = _frame(100)
    frame[:, 30] = 0
    result = _tracker(blur_size=0).process(frame, 0.0)
    assert result.valid
    assert result.error_px == pytest.approx(19.5)


@pytest.mark.parametrize(
    "method,expected_valid", [("otsu", False), ("adaptive", True)]
)
def test_comparison_methods_run_on_synthetic_illumination(
    method: str, expected_valid: bool
) -> None:
    """Reject an Otsu shadow region rather than reporting a false path."""
    frame = _frame(100)
    shading = np.linspace(0.5, 1.0, 160)[None, :, None]
    frame = (frame * shading).astype(np.uint8)
    result = _tracker(method=method).process(frame, 0.0)
    assert result.valid is expected_valid, result.reason
    if expected_valid:
        assert result.error_px == pytest.approx(19.5, abs=1)
    else:
        assert result.reason == "wide_region_or_corner"
        assert result.error_px is None


@pytest.mark.parametrize(
    "change",
    [
        {"method": "unknown"},
        {"method": []},
        {"threshold": -1},
        {"threshold": 256},
        {"threshold": True},
        {"threshold": 1.5},
        {"blur_size": 2},
        {"open_size": -1},
        {"close_size": 4},
        {"roi": (0, 0, 0, 1)},
        {"roi": (0, 0, 1.1, 1)},
        {"roi": (0, 0, float("nan"), 1)},
        {"roi": (0, 0, 1)},
        {"sample_count": 2},
        {"min_support": 10},
        {"min_run_px": 0},
        {"max_run_fraction": 0},
        {"max_step_fraction": float("inf")},
        {"ambiguity_margin_fraction": -0.1},
        {"max_gap_s": 0},
        {"adaptive_block_size": 2},
        {"adaptive_block_size": 6},
        {"adaptive_c": float("nan")},
        {"min_contrast_gray": 0},
        {"min_contrast_gray": 256},
        {"min_contrast_gray": float("nan")},
    ],
)
def test_invalid_configuration_is_rejected(change: dict[str, object]) -> None:
    """Bad configuration must fail before segmentation or device access."""
    with pytest.raises(ValueError):
        observation.ObservationConfig(**change)


def test_roi_list_is_canonicalized_to_immutable_tuple() -> None:
    """JSON-style bounds must not remain a mutable configuration value."""
    config = observation.ObservationConfig(roi=[0, 0.25, 1, 1])
    assert isinstance(config.roi, tuple)
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.threshold = 10


@pytest.mark.parametrize(
    "frame",
    [
        None,
        np.zeros((120, 160), np.uint8),
        np.zeros((120, 160, 4), np.uint8),
        np.zeros((120, 160, 3), np.float32),
        np.zeros((0, 160, 3), np.uint8),
        np.zeros((1, 160, 3), np.uint8),
    ],
)
def test_invalid_image_format_is_rejected(frame: object) -> None:
    """Unexpected external image formats must be rejected at the boundary."""
    with pytest.raises(ValueError):
        _tracker().process(frame, 0.0)


@pytest.mark.parametrize(
    "timestamp_s", [-1, float("nan"), float("inf"), "1", True]
)
def test_invalid_time_is_rejected(timestamp_s: object) -> None:
    """Nonfinite or malformed frame times must not enter temporal tracking."""
    with pytest.raises(ValueError):
        _tracker().process(_frame(), timestamp_s)
