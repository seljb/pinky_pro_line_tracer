"""ROS 2 integration. Motion is disabled unless explicitly configured and calibrated."""
import json
import math
import time
from pathlib import Path
import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger
from .vision import Calibration, LineDetector
from .control import AlignmentController, Pose, State


class AlignNode(Node):
    def __init__(self):
        super().__init__('pinky_line_alignment')
        self.declare_parameter('calibration_file', '')
        self.declare_parameter('camera_topic', '/line_align/camera/image_raw')
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('cmd_vel_topic', '/line_align/cmd_vel')
        self.declare_parameter('allow_drive', False)
        self.declare_parameter('threshold', 100)
        self.declare_parameter('max_calibration_rmse_m', 0.015)
        self.declare_parameter('max_ros_header_age_s', 0.4)
        path = str(self.get_parameter('calibration_file').value)
        if not path or not Path(path).exists():
            raise RuntimeError('Set calibration_file to a measured calibration JSON')
        self.cal = Calibration.load(path)
        self.drive_requested = bool(self.get_parameter('allow_drive').value)
        output_topic = str(self.get_parameter('cmd_vel_topic').value)
        if output_topic.rstrip('/') in ('/cmd_vel', 'cmd_vel'):
            raise RuntimeError('Direct /cmd_vel output is forbidden; use a safety-rated external mux')
        limit = float(self.get_parameter('max_calibration_rmse_m').value)
        self.drive_enabled = (self.drive_requested and self.cal.kind == 'real'
                              and self.cal.validated and self.cal.rmse is not None
                              and self.cal.rmse <= limit)
        if self.drive_requested and not self.drive_enabled:
            raise RuntimeError('Motion denied: require REAL, independently validated calibration and low RMSE')
        self.detector = LineDetector(self.cal, threshold=int(self.get_parameter('threshold').value))
        self.controller = AlignmentController()
        self.bridge = CvBridge()
        self.seq = 0
        self.follower_ready_at = -1e9
        self.follower_ready = False
        self.stop_requested = False
        self.pub_cmd = self.create_publisher(Twist, output_topic, 10)
        self.pub_state = self.create_publisher(String, '/line_align/status', 10)
        self.pub_ready = self.create_publisher(Bool, '/line_align/ready', 10)
        self.pub_debug = self.create_publisher(Image, '/line_align/debug_image', 2)
        self.create_subscription(Image, str(self.get_parameter('camera_topic').value),
                                 self.on_camera, qos_profile_sensor_data)
        self.create_subscription(Odometry, str(self.get_parameter('odom_topic').value),
                                 self.on_odom, qos_profile_sensor_data)
        self.create_subscription(Bool, '/line_follower/ready', self.on_follower, 10)
        self.create_service(Trigger, '/line_align/start', self.on_start)
        self.create_service(Trigger, '/line_align/stop', self.on_stop)
        self.create_service(Trigger, '/line_align/handoff_ack', self.on_handoff)
        self.create_timer(0.1, self.on_timer)
        self.get_logger().warning('OUTPUT TOPIC=%s; drive=%s; calibration=%s. '
                                  'No obstacle avoidance or certified E-stop included.' %
                                  (str(self.get_parameter('cmd_vel_topic').value),
                                   str(self.drive_enabled), self.cal.kind))

    def source_stamp_fresh(self, stamp) -> bool:
        # Guard against delayed ROS transport when timestamps are present.
        # A zero stamp is unsupported for transport-age validation: receipt-age
        # checks in the controller remain active, but true capture time is unknown.
        if stamp.sec == 0 and stamp.nanosec == 0:
            # No known source time: monitoring is possible, but driving is denied.
            return not self.drive_enabled
        age_s = (self.get_clock().now().nanoseconds
                 - (int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec))) / 1e9
        max_age = float(self.get_parameter('max_ros_header_age_s').value)
        return 0.0 <= age_s <= max_age

    def on_camera(self, msg):
        now = time.monotonic()
        if not self.source_stamp_fresh(msg.header.stamp):
            self.seq += 1
            self.controller.update_line(None, now, self.seq)
            self.get_logger().warning('Dropped stale/future-stamped camera frame')
            return
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            line = self.detector.detect(frame)
        except Exception as exc:
            self.get_logger().error('Camera invalid: ' + str(exc))
            line = None
            frame = None
        self.seq += 1
        self.controller.update_line(line, now, self.seq)
        if frame is not None and line is not None:
            # Overlay numerical offsets; display only, not geometric proof.
            out = frame.copy()
            cv2.putText(out, 'ey: %.3f m, yaw: %.1f deg' %
                        (line.lateral_m, math.degrees(line.heading_rad)), (12, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 140, 255), 2)
            debug = self.bridge.cv2_to_imgmsg(out, encoding='bgr8')
            debug.header = msg.header
            self.pub_debug.publish(debug)

    def on_odom(self, msg):
        if not self.source_stamp_fresh(msg.header.stamp):
            self.get_logger().warning('Dropped stale/future-stamped odometry')
            return
        q = msg.pose.pose.orientation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        pose = Pose(float(msg.pose.pose.position.x), float(msg.pose.pose.position.y), yaw)
        self.controller.update_pose(pose, time.monotonic())

    def on_follower(self, msg):
        self.follower_ready = bool(msg.data)
        self.follower_ready_at = time.monotonic()

    def on_start(self, request, response):
        now = time.monotonic()
        if not self.drive_enabled:
            response.success = False
            response.message = ('Motion disabled. Use allow_drive:=true only with validated real '
                                'calibration, safety controls and exclusive command ownership.')
            return response
        response.success, response.message = self.controller.start(now)
        return response

    def on_stop(self, request, response):
        self.controller.stop(time.monotonic())
        self.publish_zero()
        response.success, response.message = True, 'alignment stopped, zero commanded'
        return response

    def on_handoff(self, request, response):
        now = time.monotonic()
        ready = self.follower_ready and 0 <= now-self.follower_ready_at < 0.5
        response.success, response.message = self.controller.handoff_ack(ready, now)
        return response

    def publish_zero(self):
        self.pub_cmd.publish(Twist())

    def on_timer(self):
        now = time.monotonic()
        cmd = self.controller.tick(now)
        msg = Twist()
        if self.drive_enabled:
            msg.linear.x = float(cmd.linear)
            msg.angular.z = float(cmd.angular)
        self.pub_cmd.publish(msg)
        self.pub_ready.publish(Bool(data=self.controller.state == State.READY))
        s = self.controller
        status = {
            'state': s.state.value, 'reason': s.reason, 'drive_enabled': self.drive_enabled,
            'line_visible': s.line is not None and now-s.line_time < s.max_vision_age_s,
            'odom_fresh': s.pose is not None and now-s.pose_time < s.max_odom_age_s,
            'lateral_m': None if s.line is None else round(s.line.lateral_m, 5),
            'heading_deg': None if s.line is None else round(math.degrees(s.line.heading_rad), 2),
            'replans': s.replans, 'handoff_requires_external_mux': True
        }
        self.pub_state.publish(String(data=json.dumps(status, ensure_ascii=False)))

    def shutdown(self):
        self.controller.stop(time.monotonic(), 'shutdown')
        for _ in range(3):
            self.publish_zero()


def main():
    rclpy.init()
    node = None
    try:
        node = AlignNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if node is not None:
            node.shutdown()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
