"""Resolve calibration data in a checkout or an installed ROS package."""

import importlib.metadata
import pathlib
import sys


def calibration_file(name: str) -> pathlib.Path:
    """Return an existing packaged calibration file without downloading data.

    Args:
        name: A JSON basename, not a path supplied by a remote source.

    Returns:
        A readable path in this checkout or the installed package data.

    Raises:
        ValueError: If name contains directory components or lacks .json.
        FileNotFoundError: If the package data cannot be located.
    """
    if (
        not name
        or pathlib.Path(name).name != name
        or "/" in name
        or "\\" in name
        or not name.endswith(".json")
    ):
        raise ValueError("Calibration name must be a JSON basename")
    candidates = [
        pathlib.Path(__file__).resolve().parents[1] / "config" / name,
        pathlib.Path(sys.prefix)
        / "share"
        / "pinky_line_alignment"
        / "config"
        / name,
    ]
    # pip의 --target 설치에서는 share 경로도 distribution 메타데이터로 찾는다.
    try:
        distribution = importlib.metadata.distribution("pinky_line_alignment")
    except importlib.metadata.PackageNotFoundError:
        distribution = None
    if distribution is not None:
        for item in distribution.files or ():
            if str(item).endswith(f"share/pinky_line_alignment/config/{name}"):
                candidates.append(pathlib.Path(distribution.locate_file(item)))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    # ROS overlay의 설치 prefix는 현재 Python sys.prefix와 다를 수 있다.
    try:
        from ament_index_python import packages
    except ImportError:
        packages = None
    if packages is not None:
        try:
            share = packages.get_package_share_directory("pinky_line_alignment")
        except packages.PackageNotFoundError:
            share = None
        if share is not None:
            candidate = pathlib.Path(share) / "config" / name
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(f"Packaged calibration not found: {name}")
