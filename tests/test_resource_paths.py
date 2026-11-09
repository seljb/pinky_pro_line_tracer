"""Check packaged calibration lookup without requiring ROS installation."""

import pathlib

import pytest

from pinky_line_alignment import resource_paths


def test_source_calibration_is_found() -> None:
    """Source checkouts expose the same named calibration as installed tools."""
    path = resource_paths.calibration_file("synthetic_calibration.json")
    assert path.is_file()


@pytest.mark.parametrize(
    "name", ["../secret.json", "a/b.json", "a\\b.json", ""]
)
def test_lookup_rejects_paths(name: str) -> None:
    """Only a calibration basename can be resolved through package metadata."""
    with pytest.raises(ValueError):
        resource_paths.calibration_file(name)


def test_missing_calibration_is_explicit() -> None:
    """Unknown package data is an error rather than an invented calibration."""
    with pytest.raises(FileNotFoundError):
        resource_paths.calibration_file("missing_fixture.json")
