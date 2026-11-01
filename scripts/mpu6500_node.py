#!/usr/bin/env python3
import math
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus

ADDR = 0x68
REG_SMPLRT_DIV = 0x19
REG_CONFIG = 0x1A
REG_GYRO_CONFIG = 0x1B
REG_ACCEL_CONFIG = 0x1C
REG_ACCEL_XOUT = 0x3B
REG_PWR_MGMT_1 = 0x6B

ACCEL_LSB_PER_G = 8192.0     # zakres plus minus 4 g
GYRO_LSB_PER_DPS = 65.5      # zakres plus minus 500 dps
G = 9.80665


def s16(high, low):
    v = (high << 8) | low
    return v - 65536 if v >= 32768 else v


class Mpu6500(Node):
    def __init__(self):
        super().__init__('imu_node')
        self.declare_parameter('bus', 1)
        self.declare_parameter('frame_id', 'imu_link')
        self.declare_parameter('rate', 50.0)
        self.declare_parameter('calib_samples', 300)

        bus_no = self.get_parameter('bus').value
        self.frame_id = self.get_parameter('frame_id').value
        rate = self.get_parameter('rate').value

        self.bus = SMBus(bus_no)
        self.bus.write_byte_data(ADDR, REG_PWR_MGMT_1, 0x00)
        time.sleep(0.1)
        self.bus.write_byte_data(ADDR, REG_CONFIG, 0x03)         # filtr dolnoprzepustowy ok. 41 Hz
        self.bus.write_byte_data(ADDR, REG_SMPLRT_DIV, 0x09)     # 100 Hz
        self.bus.write_byte_data(ADDR, REG_GYRO_CONFIG, 0x08)    # 500 dps
        self.bus.write_byte_data(ADDR, REG_ACCEL_CONFIG, 0x08)   # 4 g
        time.sleep(0.1)

        self.get_logger().info('Kalibracja zyroskopu, nie ruszaj robota')
        self.gyro_bias = self.calibrate(self.get_parameter('calib_samples').value)
        self.get_logger().info('Bias zyroskopu rad/s: %.5f %.5f %.5f' % tuple(self.gyro_bias))

        self.pub = self.create_publisher(Imu, 'imu/data_raw', 10)
        self.timer = self.create_timer(1.0 / rate, self.tick)

    def read_raw(self):
        d = self.bus.read_i2c_block_data(ADDR, REG_ACCEL_XOUT, 14)
        ax = s16(d[0], d[1]) / ACCEL_LSB_PER_G * G
        ay = s16(d[2], d[3]) / ACCEL_LSB_PER_G * G
        az = s16(d[4], d[5]) / ACCEL_LSB_PER_G * G
        k = math.pi / 180.0 / GYRO_LSB_PER_DPS
        gx = s16(d[8], d[9]) * k
        gy = s16(d[10], d[11]) * k
        gz = s16(d[12], d[13]) * k
        return ax, ay, az, gx, gy, gz

    def calibrate(self, n):
        sx = sy = sz = 0.0
        count = 0
        for _ in range(n):
            try:
                _, _, _, gx, gy, gz = self.read_raw()
                sx += gx
                sy += gy
                sz += gz
                count += 1
            except OSError:
                pass
            time.sleep(0.01)
        if count == 0:
            return [0.0, 0.0, 0.0]
        return [sx / count, sy / count, sz / count]

    def tick(self):
        try:
            ax, ay, az, gx, gy, gz = self.read_raw()
        except OSError:
            self.get_logger().warn('Blad odczytu I2C', throttle_duration_sec=2.0)
            return
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.orientation_covariance[0] = -1.0
        msg.linear_acceleration.x = ax
        msg.linear_acceleration.y = ay
        msg.linear_acceleration.z = az
        msg.angular_velocity.x = gx - self.gyro_bias[0]
        msg.angular_velocity.y = gy - self.gyro_bias[1]
        msg.angular_velocity.z = gz - self.gyro_bias[2]
        for i in (0, 4, 8):
            msg.angular_velocity_covariance[i] = 1.0e-4
            msg.linear_acceleration_covariance[i] = 1.0e-2
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = Mpu6500()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
