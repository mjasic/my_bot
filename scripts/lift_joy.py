#!/usr/bin/env python3
"""Pad -> podnosnik. Os krzyzaka (domyslnie 7): +1 = gora, -1 = dol, 0 = stop.

Publikuje std_msgs/Int16 (PWM) na /lift_cmd z czestotliwoscia 20 Hz.
Zabezpieczenie: jesli /joy nie przychodzi dluzej niz joy_timeout, wysyla 0.
Wymaga, zeby joy_node powtarzal wiadomosci (parametr autorepeat_rate).
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Int16


class LiftJoy(Node):
    def __init__(self):
        super().__init__('lift_joy')
        self.declare_parameter('axis', 7)
        self.declare_parameter('pwm', 255)
        self.declare_parameter('joy_timeout', 0.5)

        self.axis = self.get_parameter('axis').value
        self.pwm = int(self.get_parameter('pwm').value)
        self.joy_timeout = self.get_parameter('joy_timeout').value

        self.value = 0.0
        self.last_joy = None
        self.last_cmd = None

        self.pub = self.create_publisher(Int16, '/lift_cmd', 10)
        self.create_subscription(Joy, '/joy', self.joy_cb, 10)
        self.create_timer(0.05, self.tick)
        self.get_logger().info(
            f'Podnosnik: os {self.axis}, PWM {self.pwm}, timeout /joy {self.joy_timeout:.1f} s.')

    def joy_cb(self, msg):
        if self.axis < len(msg.axes):
            self.value = msg.axes[self.axis]
        self.last_joy = self.get_clock().now()

    def tick(self):
        cmd = 0
        if self.last_joy is not None:
            age = (self.get_clock().now() - self.last_joy).nanoseconds / 1e9
            if age <= self.joy_timeout:
                if self.value > 0.5:
                    cmd = self.pwm
                elif self.value < -0.5:
                    cmd = -self.pwm
        if cmd != self.last_cmd:
            self.last_cmd = cmd
            self.get_logger().info({0: 'Podnosnik: STOP'}.get(
                cmd, 'Podnosnik: GORA' if cmd > 0 else 'Podnosnik: DOL'))
        self.pub.publish(Int16(data=cmd))


def main():
    rclpy.init()
    node = LiftJoy()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
