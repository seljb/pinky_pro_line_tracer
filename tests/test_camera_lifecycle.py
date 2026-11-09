"""Test camera cleanup contracts with mocked ROS and camera backends.

These tests do not validate an installed ROS runtime or physical devices.
"""

import importlib.util
import math
import pathlib
import sys
import types

import cv2
import pytest


@pytest.fixture
def camera_subject(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """Load the camera adapter against explicit, isolated ROS test doubles."""
    state = types.SimpleNamespace(
        parameters={},
        devices=[],
        nodes=[],
        opened=True,
        start_error=False,
        timer_error=False,
        close_error=False,
        ros_shutdowns=0,
    )

    class FakeNode:
        def __init__(self, name: str) -> None:
            self.parameters = dict(state.parameters)
            self.destroyed = 0
            state.nodes.append(self)

        def declare_parameter(self, name: str, default: object) -> None:
            self.parameters.setdefault(name, default)

        def get_parameter(self, name: str) -> types.SimpleNamespace:
            return types.SimpleNamespace(value=self.parameters[name])

        def create_publisher(self, *args: object) -> object:
            return object()

        def create_timer(self, period_s: float, callback: object) -> object:
            if state.timer_error:
                raise RuntimeError("timer creation failed")
            return object()

        def destroy_node(self) -> None:
            self.destroyed += 1

    class FakeCamera:
        def __init__(self, *args: object) -> None:
            self.starts = 0
            self.closes = 0
            self.releases = 0
            self.reads = 0
            state.devices.append(self)

        def start(self) -> None:
            self.starts += 1
            if state.start_error:
                raise RuntimeError("camera start failed")

        def isOpened(self) -> bool:
            return state.opened

        def close(self) -> None:
            self.closes += 1
            if state.close_error:
                raise RuntimeError("camera close failed")

        def release(self) -> None:
            self.releases += 1

        def get_frame(self) -> None:
            self.reads += 1
            return None

        def read(self) -> tuple[bool, None]:
            self.reads += 1
            return False, None

    def ros_shutdown() -> None:
        state.ros_shutdowns += 1

    stubs = {
        "rclpy": types.ModuleType("rclpy"),
        "rclpy.node": types.ModuleType("rclpy.node"),
        "sensor_msgs": types.ModuleType("sensor_msgs"),
        "sensor_msgs.msg": types.ModuleType("sensor_msgs.msg"),
        "cv_bridge": types.ModuleType("cv_bridge"),
        "pinkylib": types.ModuleType("pinkylib"),
    }
    stubs["rclpy.node"].Node = FakeNode
    stubs["sensor_msgs.msg"].Image = object
    stubs["cv_bridge"].CvBridge = object
    stubs["pinkylib"].Camera = FakeCamera
    stubs["rclpy"].init = lambda: None
    stubs["rclpy"].spin = lambda node: None
    stubs["rclpy"].ok = lambda: True
    stubs["rclpy"].shutdown = ros_shutdown
    for name, stub in stubs.items():
        monkeypatch.setitem(sys.modules, name, stub)
    monkeypatch.setattr(cv2, "VideoCapture", FakeCamera)
    module_path = (
        pathlib.Path(__file__).resolve().parents[1]
        / "pinky_line_alignment"
        / "camera_node.py"
    )
    spec = importlib.util.spec_from_file_location(
        "camera_lifecycle_subject", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load the camera lifecycle test subject")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    state.module = module
    return state


@pytest.mark.parametrize("fps", [0.0, -1.0, math.nan, math.inf, 31, True, "10"])
def test_invalid_frame_rate_opens_no_device(
    camera_subject: types.SimpleNamespace, fps: object
) -> None:
    """Bad frame rates fail before either camera factory is invoked."""
    camera_subject.parameters = {"fps": fps}
    with pytest.raises(ValueError, match="fps"):
        camera_subject.module.CameraNode()
    assert camera_subject.devices == []
    assert camera_subject.nodes[0].destroyed == 1


@pytest.mark.parametrize("device_index", [-1, 1.5, True, "0"])
def test_invalid_device_index_opens_no_device(
    camera_subject: types.SimpleNamespace, device_index: object
) -> None:
    """Device indices are validated before constructing a capture object."""
    camera_subject.parameters = {"source": "usb", "device_index": device_index}
    with pytest.raises(ValueError, match="device_index"):
        camera_subject.module.CameraNode()
    assert camera_subject.devices == []


def test_unknown_source_opens_no_device(
    camera_subject: types.SimpleNamespace,
) -> None:
    """An unsupported backend name cannot acquire either device."""
    camera_subject.parameters = {"source": "unsupported"}
    with pytest.raises(ValueError, match="source"):
        camera_subject.module.CameraNode()
    assert camera_subject.devices == []


def test_start_failure_closes_acquired_pinky_camera(
    camera_subject: types.SimpleNamespace,
) -> None:
    """A backend acquired before start fails is closed once."""
    camera_subject.start_error = True
    with pytest.raises(RuntimeError, match="camera start failed"):
        camera_subject.module.CameraNode()
    assert camera_subject.devices[0].starts == 1
    assert camera_subject.devices[0].closes == 1
    assert camera_subject.nodes[0].destroyed == 1


def test_unopened_usb_capture_is_released(
    camera_subject: types.SimpleNamespace,
) -> None:
    """An unopened capture is still an acquired object that needs release."""
    camera_subject.parameters = {"source": "usb"}
    camera_subject.opened = False
    with pytest.raises(RuntimeError, match="USB camera not opened"):
        camera_subject.module.CameraNode()
    assert camera_subject.devices[0].releases == 1
    assert camera_subject.nodes[0].destroyed == 1


@pytest.mark.parametrize("source", ["pinky", "usb"])
def test_timer_failure_closes_open_backend(
    camera_subject: types.SimpleNamespace, source: str
) -> None:
    """A ROS timer setup failure cannot leak an already opened camera."""
    camera_subject.parameters = {"source": source}
    camera_subject.timer_error = True
    with pytest.raises(RuntimeError, match="timer creation failed"):
        camera_subject.module.CameraNode()
    camera = camera_subject.devices[0]
    assert camera.closes + camera.releases == 1
    assert camera_subject.nodes[0].destroyed == 1


@pytest.mark.parametrize("source", ["pinky", "usb"])
def test_shutdown_is_idempotent_and_tick_after_close_is_inactive(
    camera_subject: types.SimpleNamespace, source: str
) -> None:
    """Repeated cleanup and a late timer callback do not reuse the backend."""
    camera_subject.parameters = {"source": source}
    node = camera_subject.module.CameraNode()
    camera = camera_subject.devices[0]
    node.shutdown()
    node.shutdown()
    node.tick()
    assert camera.closes + camera.releases == 1
    assert camera.reads == 0
    assert node.camera is None


def test_main_cleans_ros_even_if_camera_close_fails(
    camera_subject: types.SimpleNamespace,
) -> None:
    """Backend cleanup failure still permits node and ROS teardown."""
    camera_subject.close_error = True
    with pytest.raises(RuntimeError, match="camera close failed"):
        camera_subject.module.main()
    assert camera_subject.devices[0].closes == 1
    assert camera_subject.nodes[0].destroyed == 1
    assert camera_subject.ros_shutdowns == 1
