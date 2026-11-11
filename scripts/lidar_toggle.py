#!/usr/bin/env python3
"""Steruje silnikiem lidaru: na zadanie (subskrybenci /scan) i z pada.

- Po starcie lidar jest wylaczany (usluga stop_motor).
- Gdy ktos zaczyna subskrybowac /scan (RViz, SLAM, Nav2...), lidar wlacza sie sam.
  Gdy ostatni subskrybent zniknie, po idle_off_seconds lidar wylacza sie sam
  (chyba ze wlaczono go z pada: wtedy zostaje wlaczony).
- Pad: przytrzymanie hold_on_seconds WLACZA lidar na stale,
  przytrzymanie hold_off_seconds WYLACZA. Krotkie klikniecia sa ignorowane.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_srvs.srv import Empty


class LidarToggle(Node):
    def __init__(self):
        super().__init__('lidar_toggle')
        self.declare_parameter('button', 3)
        self.declare_parameter('hold_on_seconds', 1.0)
        self.declare_parameter('hold_off_seconds', 2.0)
        self.declare_parameter('idle_off_seconds', 5.0)
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('start_service', '/start_motor')
        self.declare_parameter('stop_service', '/stop_motor')

        self.button = self.get_parameter('button').value
        self.hold_on = self.get_parameter('hold_on_seconds').value
        self.hold_off = self.get_parameter('hold_off_seconds').value
        self.idle_off = self.get_parameter('idle_off_seconds').value
        self.scan_topic = self.get_parameter('scan_topic').value
        self.start_cli = self.create_client(
            Empty, self.get_parameter('start_service').value)
        self.stop_cli = self.create_client(
            Empty, self.get_parameter('stop_service').value)

        self.lidar_on = None    # nieznany, dopoki nie wylaczymy go po starcie
        self.manual = False     # wlaczony z pada: nie wylaczaj automatycznie
        self.prev_subs = 0
        self.zero_since = None  # od kiedy nikt nie subskrybuje /scan
        self.prev = 0
        self.busy = False
        self.press_t = None     # moment wcisniecia przycisku
        self.consumed = False   # przytrzymanie juz wykonalo przelaczenie

        self.create_subscription(Joy, '/joy', self.joy_cb, 10)
        self.init_timer = self.create_timer(1.0, self.init_cb)
        self.hold_timer = self.create_timer(0.1, self.hold_cb)
        self.demand_timer = self.create_timer(1.0, self.demand_cb)
        self.get_logger().info(
            f'Lidar na zadanie ({self.scan_topic}, wylaczenie po {self.idle_off:.0f} s bez '
            f'subskrybentow). Przycisk {self.button}: wlaczenie po {self.hold_on:.1f} s, '
            f'wylaczenie po {self.hold_off:.1f} s przytrzymania.')

    # ---------- wywolania uslug ----------
    def init_cb(self):
        # Wylaczamy lidar zaraz po starcie, gdy tylko usluga jest dostepna.
        if self.busy:
            return
        if self.stop_cli.service_is_ready():
            self.call(self.stop_cli, False, 'start')

    def call(self, client, target_on, reason):
        self.busy = True
        future = client.call_async(Empty.Request())
        future.add_done_callback(lambda f: self.done(f, target_on, reason))

    def done(self, future, target_on, reason):
        self.busy = False
        try:
            future.result()
        except Exception as ex:
            self.get_logger().warn(f'Wywolanie uslugi nie powiodlo sie: {ex}')
            return
        self.lidar_on = target_on
        if self.init_timer is not None:
            self.init_timer.cancel()
            self.init_timer = None
        state = 'WLACZONY' if target_on else 'WYLACZONY'
        self.get_logger().info(f'Lidar {state} ({reason})')

    # ---------- na zadanie: subskrybenci /scan ----------
    def demand_cb(self):
        if self.lidar_on is None or self.busy:
            return
        subs = self.count_subscribers(self.scan_topic)
        now = self.get_clock().now()

        if subs > 0:
            self.zero_since = None
            if self.prev_subs == 0 and not self.lidar_on:
                self.prev_subs = subs
                self.call(self.start_cli, True, f'subskrybenci {self.scan_topic}: {subs}')
                return
        else:
            if self.zero_since is None:
                self.zero_since = now
            idle = (now - self.zero_since).nanoseconds / 1e9
            if self.lidar_on and not self.manual and idle >= self.idle_off:
                self.prev_subs = subs
                self.call(self.stop_cli, False, f'brak subskrybentow od {idle:.0f} s')
                return
        self.prev_subs = subs

    # ---------- pad ----------
    def hold_cb(self):
        # Przelaczenie po przytrzymaniu, jeszcze w trakcie trzymania przycisku.
        if self.press_t is None or self.consumed or self.busy:
            return
        if self.lidar_on is None:
            return
        held = (self.get_clock().now() - self.press_t).nanoseconds / 1e9
        needed = self.hold_off if self.lidar_on else self.hold_on
        if held >= needed:
            self.consumed = True
            if self.lidar_on:
                self.manual = False
                self.call(self.stop_cli, False, 'pad')
            else:
                self.manual = True
                self.call(self.start_cli, True, 'pad')

    def joy_cb(self, msg):
        if self.button >= len(msg.buttons):
            return
        cur = msg.buttons[self.button]
        if cur == 1 and self.prev == 0:
            self.press_t = self.get_clock().now()
            self.consumed = False
        elif cur == 0 and self.prev == 1:
            self.press_t = None
            self.consumed = False
        self.prev = cur


def main():
    rclpy.init()
    node = LidarToggle()
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
