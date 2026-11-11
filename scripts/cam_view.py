#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage, Image
import numpy as np
import cv2


class CamView(Node):
    def __init__(self):
        super().__init__('cam_view')
        self.pub = self.create_publisher(Image, '/camera/image_view', 1)
        self.create_subscription(
            CompressedImage, '/camera/image_raw/compressed',
            self.cb, qos_profile_sensor_data)
        self.n = 0

    def cb(self, msg):
        img = cv2.imdecode(np.frombuffer(msg.data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return
        out = Image()
        out.header = msg.header
        out.height, out.width = img.shape[:2]
        out.encoding = 'bgr8'
        out.is_bigendian = 0
        out.step = out.width * 3
        out.data = img.tobytes()
        self.pub.publish(out)
        self.n += 1
        if self.n == 1:
            self.get_logger().info('Pierwsza klatka odebrana i opublikowana')


def main():
    rclpy.init()
    rclpy.spin(CamView())


if __name__ == '__main__':
    main()
