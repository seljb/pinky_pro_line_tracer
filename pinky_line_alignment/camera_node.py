"""Optional ROS Image bridge to the officially documented pinkylib.Camera.

No camera model or resolution is assumed. Set actual ROS parameters on Pinky.
"""

import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class CameraNode(Node):
    """Own a Pinky or USB camera and publish BGR ROS images."""

    def __init__(self):
        """Initialize owned state and explicit runtime dependencies."""
        super().__init__("pinky_camera_bridge")
        self.declare_parameter("source", "pinky")
        self.declare_parameter("device_index", 0)
        self.declare_parameter("fps", 10.0)
        self.declare_parameter("output_topic", "/line_align/camera/image_raw")
        self.source = str(self.get_parameter("source").value)
        self.bridge = CvBridge()
        self.pub = self.create_publisher(
            Image, str(self.get_parameter("output_topic").value), 2
        )
        if self.source == "pinky":
            try:
                from pinkylib import Camera
            except ImportError as e:
                raise RuntimeError(
                    (
                        "pinkylib.Camera missing: install official Pinky "
                        "environment"
                    )
                ) from e
            self.camera = Camera()
            self.camera.start()
        elif self.source == "usb":
            self.camera = cv2.VideoCapture(
                int(self.get_parameter("device_index").value)
            )
            if not self.camera.isOpened():
                raise RuntimeError("USB camera not opened")
        else:
            raise ValueError("source must be pinky or usb")
        fps = float(self.get_parameter("fps").value)
        if fps <= 0 or fps > 30:
            raise ValueError("fps must be in (0,30]")
        self.create_timer(1.0 / fps, self.tick)

    def tick(self):
        """Publish one available camera frame without requesting motion."""
        if self.source == "pinky":
            frame = self.camera.get_frame()
        else:
            ok, frame = self.camera.read()
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

    def shutdown(self):
        """Close the selected camera backend."""
        if self.source == "pinky":
            self.camera.close()
        else:
            self.camera.release()


def main():
    """Run the camera bridge and release the camera on normal shutdown."""
    rclpy.init()
    node = None
    try:
        node = CameraNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.shutdown()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
