#!/usr/bin/env python3
"""Pair raw/filtered ROS scans by stamp; run before Nav2 with the robot at rest."""
import argparse
from collections import OrderedDict
import math
import time

from scan_self_filter import (
    angle_degrees, filter_scan, INPUT_TOPIC, OUTPUT_TOPIC,
    SELF_FILTER_SECTORS, self_echo_sector, sensor_qos,
)


def same_value(a, b):
    return a == b or (math.isnan(a) and math.isnan(b))


def inspect_pair(raw, filtered, front_target=.50, front_tolerance=.10):
    """Validate each sample and all metadata, preserving NaN values."""
    for field in ('header', 'angle_min', 'angle_max', 'angle_increment',
                  'time_increment', 'scan_time', 'range_min', 'range_max'):
        a, b = getattr(raw, field), getattr(filtered, field)
        equal = a == b if field == 'header' else same_value(a, b)
        if not equal:
            raise ValueError(f'Metadata changed: {field}')
    if len(raw.ranges) != len(filtered.ranges):
        raise ValueError('Range count changed')
    if len(raw.intensities) != len(filtered.intensities) or any(
            not same_value(a, b) for a, b in zip(raw.intensities, filtered.intensities)):
        raise ValueError('Intensity/index structure changed')
    expected = filter_scan(raw)
    for index, (a, b) in enumerate(zip(expected.ranges, filtered.ranges)):
        if not same_value(a, b):
            raise ValueError(f'Unexpected output at index {index}: expected {a}, got {b}')
    if not raw.ranges or not math.isfinite(raw.angle_min) or not math.isfinite(raw.angle_increment):
        raise ValueError('Empty scan or invalid angle metadata')
    angles = [angle_degrees(raw.angle_min, raw.angle_increment, i)
              for i in range(len(raw.ranges))]
    front = min(range(len(angles)), key=lambda i: abs(angles[i]))
    if abs(angles[front]) > math.degrees(abs(raw.angle_increment))*.51+1e-6:
        raise ValueError('Scan does not cover forward 0 degrees')
    front_raw, front_filtered = raw.ranges[front], filtered.ranges[front]
    if not math.isfinite(front_raw) or abs(front_raw-front_target)>front_tolerance:
        raise ValueError(f'Front raw={front_raw:.3f} does not match stationary desk fixture')
    if front_raw != front_filtered:
        raise ValueError('Front desk return changed')
    counts = [0]*len(SELF_FILTER_SECTORS)
    for index, value in enumerate(raw.ranges):
        sector = self_echo_sector(angles[index], value)
        if sector is not None:
            counts[sector] += 1
            if filtered.ranges[index] != math.inf:
                raise ValueError(f'Self echo remains at index {index}')
    return counts, front_raw, front_filtered


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pairs', type=int, default=20)
    parser.add_argument('--timeout', type=float, default=30.0)
    parser.add_argument('--front-target', type=float, default=.50)
    parser.add_argument('--front-tolerance', type=float, default=.10)
    options, ros_args = parser.parse_known_args()
    if options.pairs <= 0 or options.timeout <= 0 or options.front_tolerance < 0:
        parser.error('pairs/timeout must be positive; front tolerance must be nonnegative')
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import LaserScan

    class ScanComparison(Node):
        def __init__(self):
            super().__init__('scan_filter_comparison')
            self.raw = OrderedDict()
            self.filtered = OrderedDict()
            self.pairs = 0
            self.sectors = [0]*len(SELF_FILTER_SECTORS)
            self.failure = None
            self.raw_sub = self.create_subscription(
                LaserScan, INPUT_TOPIC, lambda m: self.receive(m, True), sensor_qos())
            self.filtered_sub = self.create_subscription(
                LaserScan, OUTPUT_TOPIC, lambda m: self.receive(m, False), sensor_qos())

        def receive(self, msg, is_raw):
            if self.failure is not None:
                return
            key = (msg.header.stamp.sec, msg.header.stamp.nanosec, msg.header.frame_id)
            own, other = (self.raw, self.filtered) if is_raw else (self.filtered, self.raw)
            if key not in other:
                own[key] = msg
                while len(own)>100:
                    own.popitem(last=False)
                return
            partner = other.pop(key)
            raw, filtered = (msg, partner) if is_raw else (partner, msg)
            try:
                counts, front_raw, front_filtered = inspect_pair(
                    raw, filtered, options.front_target, options.front_tolerance)
                self.pairs += 1
                self.sectors = [a+b for a, b in zip(self.sectors, counts)]
                self.get_logger().info(
                    f'Pair {self.pairs}: RAW front={front_raw:.3f} m, '
                    f'FILTERED front={front_filtered:.3f} m; '
                    f'self samples -> inf={counts}')
            except ValueError as error:
                self.failure = str(error)

    rclpy.init(args=ros_args)
    node = ScanComparison()
    deadline = time.monotonic()+options.timeout
    try:
        while rclpy.ok() and time.monotonic()<deadline and node.failure is None and node.pairs<options.pairs:
            rclpy.spin_once(node, timeout_sec=.1)
        if node.failure:
            raise SystemExit('FAIL: '+node.failure)
        if node.pairs<options.pairs:
            raise SystemExit(f'FAIL: paired only {node.pairs}/{options.pairs}; check topics/QoS/clock')
        if not all(node.sectors):
            raise SystemExit(f'INCOMPLETE: did not observe all six raw clusters; totals={node.sectors}')
        print(f'PASS: {node.pairs} paired live scans; six self sectors filtered; front preserved; totals={node.sectors}')
        print('This test does not verify collision_monitor or recover physical blind sectors.')
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
