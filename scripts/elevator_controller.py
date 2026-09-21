#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float64

class ElevatorController(Node):
    def __init__(self):
        super().__init__('elevator_controller')

        self.get_logger().info('电梯控制器启动...')

        # 订阅电梯控制命令
        self.subscription = self.create_subscription(
            String,
            '/elevator_control',
            self.control_callback,
            10)

        # 发布器 - 控制电梯平台的垂直位置
        self.elevator_pub = self.create_publisher(
            Float64,
            '/nursing_home/elevator_joint/command',
            10)

        self.current_floor = 1

        # 楼层高度
        self.floor_heights = {
            1: 0.0,
            2: 3.0
        }

        self.get_logger().info('电梯控制器已就绪')

    def control_callback(self, msg):
        """处理电梯控制命令
        格式: "floor_number"
        例如: "1" 或 "2"
        """
        try:
            floor = int(msg.data.strip())

            if floor not in self.floor_heights:
                self.get_logger().error(f'无效楼层: {floor}')
                return

            self.go_to_floor(floor)

        except ValueError:
            self.get_logger().error(f'无效的楼层号: {msg.data}')
        except Exception as e:
            self.get_logger().error(f'处理命令失败: {str(e)}')

    def go_to_floor(self, floor):
        """移动电梯到指定楼层"""
        if floor == self.current_floor:
            self.get_logger().info(f'已经在 {floor} 楼')
            return

        self.get_logger().info(f'电梯从 {self.current_floor} 楼前往 {floor} 楼')

        # 发布电梯高度
        msg = Float64()
        msg.data = self.floor_heights[floor]
        self.elevator_pub.publish(msg)

        self.current_floor = floor
        self.get_logger().info(f'✅ 电梯已到达 {floor} 楼')

def main(args=None):
    rclpy.init(args=args)
    controller = ElevatorController()

    try:
        rclpy.spin(controller)
    except KeyboardInterrupt:
        pass
    finally:
        controller.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
