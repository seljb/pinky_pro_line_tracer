"""Optional ROS Image bridge to the officially documented pinkylib.Camera.

No camera model or resolution is assumed. Set actual ROS parameters on Pinky.
"""

import math

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


class CameraNode(Node):
    """Own a Pinky or USB camera and publish BGR ROS images."""

    def __init__(self) -> None:
        """Validate parameters before opening and own camera cleanup.

        Raises:
            ValueError: If source, frame rate, or device index is invalid.
            RuntimeError: If a backend is unavailable or cannot be opened.
        """
        super().__init__("pinky_camera_bridge")
        self.camera = None
        self.source = ""
        initialized = False
        try:
            self.declare_parameter("source", "pinky")
            self.declare_parameter("device_index", 0)
            self.declare_parameter("fps", 10.0)
            self.declare_parameter(
                "output_topic", "/line_align/camera/image_raw"
            )
            source = self.get_parameter("source").value
            if source not in ("pinky", "usb"):
                raise ValueError("source must be pinky or usb")
            self.source = source
            fps = self.get_parameter("fps").value
            if (
                isinstance(fps, bool)
                or not isinstance(fps, (int, float))
                or not math.isfinite(fps)
                or not 0 < fps <= 30
            ):
                raise ValueError("fps must be finite and in (0,30]")
            device_index = self.get_parameter("device_index").value
            if type(device_index) is not int or device_index < 0:
                raise ValueError("device_index must be a nonnegative integer")
            self.bridge = CvBridge()
            self.pub = self.create_publisher(
                Image, str(self.get_parameter("output_topic").value), 2
            )
            if self.source == "pinky":
                try:
                    from pinkylib import Camera
                except ImportError as error:
                    raise RuntimeError(
                        "pinkylib.Camera missing: install official Pinky "
                        "environment"
                    ) from error
                self.camera = Camera()
                self.camera.start()
            else:
                self.camera = cv2.VideoCapture(device_index)
                if not self.camera.isOpened():
                    raise RuntimeError("USB camera not opened")
            self.create_timer(1.0 / fps, self.tick)
            initialized = True
        finally:
            # 생성 도중 실패하면 main이 객체를 받기 전에 획득한 자원을 정리한다.
            if not initialized:
                try:
                    self.shutdown()
                finally:
                    self.destroy_node()

    def tick(self) -> None:
        """Publish one available camera frame without requesting motion."""
        camera = self.camera
        if camera is None:
            return
        if self.source == "pinky":
            frame = camera.get_frame()
        else:
            ok, frame = camera.read()
            if not ok:
                return
        if frame is None:
            return
        if frame.ndim != 3 or frame.shape[2] != 3:
            self.get_logger().warning("Expected 3-channel OpenCV image")
            return
        msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        # Timestamp is receipt after get_frame; not the hardware exposure
        # timestamp.
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "pinky_camera"
        self.pub.publish(msg)

    def shutdown(self) -> None:
        """Close an acquired backend at most once, including partial setup."""
        camera = self.camera
        self.camera = None
        if camera is None:
            return
        if self.source == "pinky":
            camera.close()
        else:
            camera.release()


def main() -> None:
    """Run the camera bridge and release the camera on normal shutdown."""
    rclpy.init()
    node = None
    try:
        node = CameraNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if node is not None:
                try:
                    node.shutdown()
                finally:
                    node.destroy_node()
        finally:
            if rclpy.ok():
                rclpy.shutdown()


if __name__ == "__main__":
    main()
