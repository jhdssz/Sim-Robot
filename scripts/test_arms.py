#!/usr/bin/env python3
"""Small, sequential joint smoke test with measured joint-state feedback."""
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64

PARTS = ('shoulder', 'upper_arm', 'elbow', 'forearm', 'wrist', 'gripper',
         'finger_left', 'finger_right')


class ArmTester(Node):
    def __init__(self):
        super().__init__('arm_tester')
        self.positions = {}
        self.received = {}
        self.pubs = {
            f'{side}_{part}_joint': self.create_publisher(
                Float64, f'/dual_arm_robot/{side}_{part}_joint/command', 10)
            for side in ('left', 'right') for part in PARTS
        }
        self.subscription = self.create_subscription(
            JointState, '/joint_states', self.on_state, 10)

    def on_state(self, msg):
        now = time.monotonic()
        for name, position in zip(msg.name, msg.position):
            self.positions[name] = position
            self.received[name] = now

    def move(self, name, target, timeout=8.0):
        start = time.monotonic()
        tolerance = 0.003 if 'finger' in name else 0.05
        stable = 0
        while rclpy.ok() and time.monotonic() - start < timeout:
            self.pubs[name].publish(Float64(data=float(target)))
            rclpy.spin_once(self, timeout_sec=0.1)
            fresh = self.received.get(name, 0) > start
            fresh = fresh and time.monotonic()-self.received[name] < 0.5
            if fresh and abs(self.positions[name]-target) < tolerance:
                stable += 1
                if stable >= 5:
                    self.get_logger().info(f'{name}: measured target {target:.3f}')
                    return
            else:
                stable = 0
        raise RuntimeError(f'{name}: no fresh feedback at target {target}; measured {self.positions.get(name)}')

    def run(self):
        deadline = time.monotonic() + 10
        while not set(self.pubs).issubset(self.positions) and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        missing = set(self.pubs)-set(self.positions)
        if missing:
            raise RuntimeError(f'Missing Gazebo joint feedback: {sorted(missing)}')
        for name in self.pubs:
            self.move(name, 0.0)
        for name in self.pubs:
            target = 0.015 if 'finger' in name else 0.15
            # Shoulder roll moves away from the torso on each side.
            if name == 'right_upper_arm_joint':
                target = -target
            self.move(name, target)
            self.move(name, 0.0)


def main(args=None):
    rclpy.init(args=args)
    tester = ArmTester()
    try:
        tester.run()
    finally:
        # Request rest even if a test failed; this is not an emergency stop.
        for pub in tester.pubs.values():
            pub.publish(Float64(data=0.0))
        tester.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
