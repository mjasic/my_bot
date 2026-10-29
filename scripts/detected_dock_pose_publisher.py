#!/usr/bin/env python3
"""
Nasłuchuje transformacji TF od ramki optycznej kamery do ramki AprilTaga
(dock_tag) i republikuje ją jako geometry_msgs/PoseStamped na topiku
'detected_dock_pose', którego oczekuje wtyczka SimpleChargingDock w
docking_server (Nav2). apriltag_ros publikuje tylko /tf i /detections,
NIE publikuje bezpośrednio na detected_dock_pose - stąd ten most.
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from geometry_msgs.msg import PoseStamped
import tf2_ros
from tf2_ros import TransformException


def quat_angle_diff(q1, q2):
    """Kąt (w radianach) między dwoma kwaternionami, przez iloczyn skalarny."""
    dot = q1.x * q2.x + q1.y * q2.y + q1.z * q2.z + q1.w * q2.w
    dot = max(-1.0, min(1.0, abs(dot)))  # abs() bo q i -q to ta sama orientacja
    return 2.0 * math.acos(dot)


class DetectedDockPosePublisher(Node):
    def __init__(self):
        super().__init__('detected_dock_pose_publisher')

        self.declare_parameter('camera_frame', 'camera_link_optical')
        self.declare_parameter('tag_frame', 'dock_tag')
        self.declare_parameter('publish_rate', 20.0)
        # Próg odrzucania nagłych skoków orientacji (typowy objaw AprilTag
        # "pose ambiguity flip" - fałszywe rozwiązanie estymacji pozy przy
        # patrzeniu na płaski tag niemal prostopadle). Realny ruch robota
        # między klatkami przy 20Hz nie generuje aż tak dużych skoków.
        self.declare_parameter('max_angle_jump_deg', 15.0)
        # Po tylu kolejnych odrzuconych próbkach z rzędu i tak akceptujemy
        # nową wartość - zabezpieczenie przed permanentnym "zablokowaniem
        # się" filtra, gdyby to jednak był prawdziwy, gwałtowny ruch.
        self.declare_parameter('max_consecutive_rejects', 5)

        self.camera_frame = self.get_parameter('camera_frame').value
        self.tag_frame = self.get_parameter('tag_frame').value
        rate = self.get_parameter('publish_rate').value
        self.max_angle_jump = math.radians(
            self.get_parameter('max_angle_jump_deg').value
        )
        self.max_consecutive_rejects = self.get_parameter(
            'max_consecutive_rejects'
        ).value

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.pub = self.create_publisher(PoseStamped, 'detected_dock_pose', 10)

        self.last_orientation = None
        self.reject_streak = 0

        self.timer = self.create_timer(1.0 / rate, self.timer_callback)

        self.get_logger().info(
            f"Nasłuchuję transformacji '{self.camera_frame}' -> '{self.tag_frame}', "
            f"publikuję na 'detected_dock_pose' z częstotliwością {rate} Hz "
            f"(odrzucanie skoków orientacji > {self.get_parameter('max_angle_jump_deg').value}°)"
        )

    def timer_callback(self):
        try:
            t = self.tf_buffer.lookup_transform(
                self.camera_frame,
                self.tag_frame,
                rclpy.time.Time(),
                timeout=Duration(seconds=0.1)
            )
        except TransformException as ex:
            # Tag chwilowo niewidoczny - to normalne, nie logujemy co klatkę
            return

        new_orientation = t.transform.rotation

        if self.last_orientation is not None:
            angle_diff = quat_angle_diff(self.last_orientation, new_orientation)
            if angle_diff > self.max_angle_jump:
                self.reject_streak += 1
                if self.reject_streak <= self.max_consecutive_rejects:
                    # Odrzucamy tę próbkę jako prawdopodobny "flip" ambiguity -
                    # nie publikujemy nic, czekamy na kolejną klatkę.
                    self.get_logger().debug(
                        f"Odrzucono skok orientacji {math.degrees(angle_diff):.1f}° "
                        f"(seria: {self.reject_streak})"
                    )
                    return
                else:
                    # Zbyt długa seria odrzuceń - akceptujemy, to mógł być
                    # prawdziwy gwałtowny ruch, nie chcemy się zablokować.
                    self.get_logger().warn(
                        "Akceptuję duży skok orientacji po serii odrzuceń - "
                        "reset filtra."
                    )
                    self.reject_streak = 0

        self.last_orientation = new_orientation
        self.reject_streak = 0

        msg = PoseStamped()
        msg.header.stamp = t.header.stamp
        msg.header.frame_id = self.camera_frame
        msg.pose.position.x = t.transform.translation.x
        msg.pose.position.y = t.transform.translation.y
        msg.pose.position.z = t.transform.translation.z
        msg.pose.orientation = new_orientation

        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = DetectedDockPosePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
