#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float64

class DoorController(Node):
    def __init__(self):
        super().__init__('door_controller')

        self.get_logger().info('门控制器启动...')

        # 订阅门控制命令
        self.subscription = self.create_subscription(
            String,
            '/door_control',
            self.control_callback,
            10)

        # 发布器 - 控制门的旋转关节
        self.door_publishers = {
            'door_101': self.create_publisher(Float64, '/nursing_home/door_101_joint/command', 10),
            'door_102': self.create_publisher(Float64, '/nursing_home/door_102_joint/command', 10)
        }

        self.door_states = {
            'door_101': 'closed',
            'door_102': 'closed'
        }

        self.get_logger().info('门控制器已就绪')

    def control_callback(self, msg):
        """处理门控制命令
        格式: "action,door_name"
        例如: "open,door_101" 或 "close,door_101"
        """
        try:
            parts = msg.data.split(',')
            if len(parts) != 2:
                self.get_logger().error(f'命令格式错误: {msg.data}')
                return

            action = parts[0].strip()
            door_name = parts[1].strip()

            if door_name not in self.door_publishers:
                self.get_logger().error(f'未知门: {door_name}')
                return

            if action == 'open':
                self.open_door(door_name)
            elif action == 'close':
                self.close_door(door_name)
            else:
                self.get_logger().error(f'未知动作: {action}')

        except Exception as e:
            self.get_logger().error(f'处理命令失败: {str(e)}')

    def open_door(self, door_name):
        """开门"""
        self.get_logger().info(f'开门: {door_name}')

        # 发布旋转角度 (1.57 rad = 90度)
        msg = Float64()
        msg.data = 1.57
        self.door_publishers[door_name].publish(msg)

        self.door_states[door_name] = 'open'
        self.get_logger().info(f'✅ {door_name} 已打开')

    def close_door(self, door_name):
        """关门"""
        self.get_logger().info(f'关门: {door_name}')

        # 发布旋转角度 (0 rad = 关闭)
        msg = Float64()
        msg.data = 0.0
        self.door_publishers[door_name].publish(msg)

        self.door_states[door_name] = 'closed'
        self.get_logger().info(f'✅ {door_name} 已关闭')

def main(args=None):
    rclpy.init(args=args)
    controller = DoorController()

    try:
        rclpy.spin(controller)
    except KeyboardInterrupt:
        pass
    finally:
        controller.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
