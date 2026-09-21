#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试脚本 - 自动发送一系列送药任务来测试系统
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time

class DeliveryTester(Node):
    def __init__(self):
        super().__init__('test_medicine_delivery')

        # 创建发布器
        self.task_pub = self.create_publisher(String, '/medicine_delivery_task', 10)

        self.get_logger().info("等待系统启动...")
        time.sleep(5)

    def run_tests(self):
        # 测试任务列表
        test_tasks = [
            ('阿司匹林', '101'),
            ('降压药', '102'),
            ('维生素', '101'),
            ('感冒药', '102')
        ]

        self.get_logger().info("========================================")
        self.get_logger().info("开始测试送药系统")
        self.get_logger().info("========================================")

        for i, (medicine, room) in enumerate(test_tasks, 1):
            self.get_logger().info(f"\n测试 {i}/{len(test_tasks)}: 送 {medicine} 到 {room} 房间")

            # 发送任务
            task_msg = String()
            task_msg.data = f"{medicine},{room}"
            self.task_pub.publish(task_msg)

            # 等待任务完成（实际应该订阅完成状态，这里简化为固定等待）
            self.get_logger().info("等待任务完成...")
            time.sleep(60)  # 根据实际情况调整

        self.get_logger().info("\n========================================")
        self.get_logger().info("所有测试任务已发送完成")
        self.get_logger().info("========================================")

def main(args=None):
    rclpy.init(args=args)
    tester = DeliveryTester()

    try:
        tester.run_tests()
    except KeyboardInterrupt:
        pass
    finally:
        tester.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
