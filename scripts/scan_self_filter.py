#!/usr/bin/env python3
"""Filter known home-pose self echoes; this cannot recover occluded returns."""
from copy import deepcopy
import math

INPUT_TOPIC = '/scan'
OUTPUT_TOPIC = '/scan_filtered'
SELF_FILTER_SECTORS = (
    (-142.0, -129.0, 0.22),
    (-98.0, -82.0, 0.34),
    (-51.0, -39.0, 0.22),
    (39.0, 51.0, 0.22),
    (82.0, 98.0, 0.34),
    (129.0, 142.0, 0.22),
)


def angle_degrees(angle_min, angle_increment, index):
    """Use the scan's actual angular metadata, normalized to [-180, 180)."""
    angle = angle_min + index * angle_increment
    return (math.degrees(angle) + 180.0) % 360.0 - 180.0


def in_sector(angle, start, end):
    """Inclusive bounds, including sectors that cross the +/-180 seam."""
    if start <= end:
        return start <= angle <= end
    return angle >= start or angle <= end


def self_echo_sector(angle, distance, sectors=SELF_FILTER_SECTORS):
    """Return a matching sector index; preserve nonfinite values as received."""
    if not math.isfinite(angle) or not math.isfinite(distance):
        return None
    for index, (start, end, threshold) in enumerate(sectors):
        if in_sector(angle, start, end) and distance < threshold:
            return index
    return None


def filter_scan(scan):
    """Copy the full message and modify only selected ranges in the copy."""
    filtered = deepcopy(scan)
    if not (math.isfinite(scan.angle_min) and math.isfinite(scan.angle_increment)):
        return filtered
    for index, distance in enumerate(scan.ranges):
        angle = angle_degrees(scan.angle_min, scan.angle_increment, index)
        if self_echo_sector(angle, distance) is not None:
            filtered.ranges[index] = float('inf')
    return filtered


def sensor_qos():
    # Lazy ROS imports allow offline tests to exercise the production algorithm.
    from rclpy.qos import QoSProfile, HistoryPolicy, ReliabilityPolicy, DurabilityPolicy
    return QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=5,
                      reliability=ReliabilityPolicy.BEST_EFFORT,
                      durability=DurabilityPolicy.VOLATILE)


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import LaserScan

    class ScanSelfFilter(Node):
        def __init__(self):
            super().__init__('scan_self_filter')
            self.publisher = self.create_publisher(LaserScan, OUTPUT_TOPIC, sensor_qos())
            self.subscription = self.create_subscription(
                LaserScan, INPUT_TOPIC, self.on_scan, sensor_qos())
            self.get_logger().info(
                'Filtering /scan -> /scan_filtered using six fixed home-pose sectors')

        def on_scan(self, scan):
            self.publisher.publish(filter_scan(scan))

    rclpy.init(args=args)
    node = ScanSelfFilter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
