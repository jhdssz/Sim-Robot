#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
手臂测试脚本 - 测试机器人双臂的各个关节
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import time

class ArmTester(Node):
    def __init__(self):
        super().__init__('arm_tester')

        # 创建关节控制发布器
        self.joint_pubs = {
            'left_shoulder': self.create_publisher(Float64, '/dual_arm_robot/left_shoulder_joint/command', 10),
            'left_elbow': self.create_publisher(Float64, '/dual_arm_robot/left_elbow_joint/command', 10),
            'left_wrist': self.create_publisher(Float64, '/dual_arm_robot/left_wrist_joint/command', 10),
            'right_shoulder': self.create_publisher(Float64, '/dual_arm_robot/right_shoulder_joint/command', 10),
            'right_elbow': self.create_publisher(Float64, '/dual_arm_robot/right_elbow_joint/command', 10),
            'right_wrist': self.create_publisher(Float64, '/dual_arm_robot/right_wrist_joint/command', 10),
        }

        time.sleep(1)  # 等待发布器初始化

    def move_joint(self, joint_name, angle):
        """移动单个关节到指定角度"""
        if joint_name in self.joint_pubs:
            self.get_logger().info(f"移动 {joint_name} 到 {angle} 弧度")
            msg = Float64()
            msg.data = angle
            self.joint_pubs[joint_name].publish(msg)
        else:
            self.get_logger().warn(f"未知关节: {joint_name}")

    def reset_all(self):
        """重置所有关节到零位"""
        self.get_logger().info("重置所有关节...")
        for joint_name in self.joint_pubs.keys():
            msg = Float64()
            msg.data = 0.0
            self.joint_pubs[joint_name].publish(msg)
        time.sleep(2)

    def test_left_arm(self):
        """测试左臂"""
        self.get_logger().info("\n=== 测试左臂 ===")

        self.get_logger().info("测试左肩...")
        self.move_joint('left_shoulder', 0.5)
        time.sleep(2)
        self.move_joint('left_shoulder', -0.5)
        time.sleep(2)
        self.move_joint('left_shoulder', 0.0)
        time.sleep(1)

        self.get_logger().info("测试左肘...")
        self.move_joint('left_elbow', 1.5)
        time.sleep(2)
        self.move_joint('left_elbow', 0.5)
        time.sleep(2)
        self.move_joint('left_elbow', 0.0)
        time.sleep(1)

        self.get_logger().info("测试左手腕...")
        self.move_joint('left_wrist', 1.0)
        time.sleep(2)
        self.move_joint('left_wrist', -1.0)
        time.sleep(2)
        self.move_joint('left_wrist', 0.0)
        time.sleep(1)

    def test_right_arm(self):
        """测试右臂"""
        self.get_logger().info("\n=== 测试右臂 ===")

        self.get_logger().info("测试右肩...")
        self.move_joint('right_shoulder', 0.5)
        time.sleep(2)
        self.move_joint('right_shoulder', -0.5)
        time.sleep(2)
        self.move_joint('right_shoulder', 0.0)
        time.sleep(1)

        self.get_logger().info("测试右肘...")
        self.move_joint('right_elbow', 1.5)
        time.sleep(2)
        self.move_joint('right_elbow', 0.5)
        time.sleep(2)
        self.move_joint('right_elbow', 0.0)
        time.sleep(1)

        self.get_logger().info("测试右手腕...")
        self.move_joint('right_wrist', 1.0)
        time.sleep(2)
        self.move_joint('right_wrist', -1.0)
        time.sleep(2)
        self.move_joint('right_wrist', 0.0)
        time.sleep(1)

    def test_pick_motion(self):
        """测试抓取动作"""
        self.get_logger().info("\n=== 测试抓取动作 ===")

        # 伸展右臂
        self.move_joint('right_shoulder', 0.5)
        time.sleep(1)
        self.move_joint('right_elbow', 1.2)
        time.sleep(1)
        self.move_joint('right_wrist', -0.3)
        time.sleep(2)

        self.get_logger().info("抓取位置保持...")
        time.sleep(2)

        # 收回
        self.reset_all()

    def test_place_motion(self):
        """测试放置动作"""
        self.get_logger().info("\n=== 测试放置动作 ===")

        # 移动到放置位置
        self.move_joint('right_shoulder', 0.3)
        time.sleep(1)
        self.move_joint('right_elbow', 0.8)
        time.sleep(1)
        self.move_joint('right_wrist', -0.5)
        time.sleep(2)

        self.get_logger().info("放置位置保持...")
        time.sleep(2)

        # 收回
        self.reset_all()

    def run_full_test(self):
        """运行完整测试"""
        self.get_logger().info("========================================")
        self.get_logger().info("开始机械臂完整测试")
        self.get_logger().info("========================================")

        self.reset_all()
        time.sleep(2)

        self.test_left_arm()
        time.sleep(2)

        self.test_right_arm()
        time.sleep(2)

        self.test_pick_motion()
        time.sleep(2)

        self.test_place_motion()
        time.sleep(2)

        self.reset_all()

        self.get_logger().info("========================================")
        self.get_logger().info("测试完成！")
        self.get_logger().info("========================================")

def main(args=None):
    rclpy.init(args=args)
    tester = ArmTester()

    try:
        tester.run_full_test()
    except KeyboardInterrupt:
        pass
    finally:
        tester.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
