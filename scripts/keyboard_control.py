#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import sys
import termios
import tty

class KeyboardControl(Node):
    def __init__(self):
        super().__init__('keyboard_control')

        self.get_logger().info('键盘控制节点启动...')

        # 发布速度命令
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # 速度设置
        self.linear_speed = 0.3
        self.angular_speed = 0.5

        self.get_logger().info('键盘控制已就绪')
        self.print_usage()

    def print_usage(self):
        """打印使用说明"""
        print('\n' + '='*50)
        print('机器人键盘控制')
        print('='*50)
        print('w - 前进')
        print('s - 后退')
        print('a - 左转')
        print('d - 右转')
        print('q - 停止')
        print('Ctrl+C - 退出')
        print('='*50 + '\n')

    def get_key(self):
        """获取键盘输入"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            key = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return key

    def run(self):
        """运行主循环"""
        try:
            while rclpy.ok():
                key = self.get_key()

                twist = Twist()

                if key == 'w':
                    twist.linear.x = self.linear_speed
                    self.get_logger().info('前进')
                elif key == 's':
                    twist.linear.x = -self.linear_speed
                    self.get_logger().info('后退')
                elif key == 'a':
                    twist.angular.z = self.angular_speed
                    self.get_logger().info('左转')
                elif key == 'd':
                    twist.angular.z = -self.angular_speed
                    self.get_logger().info('右转')
                elif key == 'q':
                    twist.linear.x = 0.0
                    twist.angular.z = 0.0
                    self.get_logger().info('停止')
                elif key == '\x03':  # Ctrl+C
                    break
                else:
                    continue

                self.cmd_vel_pub.publish(twist)

        except Exception as e:
            self.get_logger().error(f'错误: {str(e)}')

def main(args=None):
    rclpy.init(args=args)
    controller = KeyboardControl()

    try:
        controller.run()
    except KeyboardInterrupt:
        pass
    finally:
        # 发送停止命令
        twist = Twist()
        controller.cmd_vel_pub.publish(twist)
        controller.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
