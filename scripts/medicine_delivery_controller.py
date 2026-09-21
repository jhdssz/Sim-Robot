#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import String, Float64
from geometry_msgs.msg import PoseStamped, Twist
from nav2_msgs.action import NavigateToPose
from sensor_msgs.msg import JointState
import time

class MedicineDeliveryController(Node):
    def __init__(self):
        super().__init__('medicine_delivery_controller')

        self.get_logger().info('送药机器人控制器启动中...')

        # 订阅任务话题
        self.task_subscription = self.create_subscription(
            String,
            '/medicine_delivery_task',
            self.task_callback,
            10)

        # 导航客户端 (Nav2)
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # 发布器
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.door_control_pub = self.create_publisher(String, '/door_control', 10)
        self.elevator_control_pub = self.create_publisher(String, '/elevator_control', 10)

        # 关节控制发布器
        self.joint_publishers = {}
        joint_names = [
            'left_shoulder_joint', 'left_elbow_joint', 'left_wrist_joint',
            'right_shoulder_joint', 'right_elbow_joint', 'right_wrist_joint'
        ]
        for joint in joint_names:
            topic = f'/dual_arm_robot/{joint}/command'
            self.joint_publishers[joint] = self.create_publisher(Float64, topic, 10)

        # 订阅关节状态
        self.joint_state_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_state_callback,
            10)

        self.current_joint_states = {}

        # 位置定义（与ROS1相同）
        self.locations = {
            'reception': (2.0, 0.0),
            'medicine_shelf': (1.5, -0.8),
            'room_101_door': (9.0, 5.0),
            'room_101': (10.0, 5.5),
            'room_101_nightstand': (10.5, 5.8),
            'room_102_door': (9.0, -5.0),
            'room_102': (10.0, -5.5),
            'room_102_nightstand': (10.5, -5.8),
            'elevator': (-5.0, 0.0)
        }

        # 状态
        self.current_state = 'idle'
        self.current_medicine = None
        self.current_room = None

        self.get_logger().info('送药机器人控制器已就绪！等待任务...')

    def joint_state_callback(self, msg):
        """关节状态回调"""
        for i, name in enumerate(msg.name):
            if i < len(msg.position):
                self.current_joint_states[name] = msg.position[i]

    def task_callback(self, msg):
        """接收送药任务"""
        try:
            data = msg.data.split(',')
            if len(data) == 2:
                medicine_name = data[0].strip()
                room_number = data[1].strip()

                self.get_logger().info(f'收到新任务: 送 {medicine_name} 到 {room_number} 房间')
                self.current_medicine = medicine_name
                self.current_room = room_number

                # 执行送药流程
                self.execute_delivery_task()
            else:
                self.get_logger().error('任务格式错误！应为: "药品名,房间号"')
        except Exception as e:
            self.get_logger().error(f'解析任务失败: {str(e)}')

    def execute_delivery_task(self):
        """执行完整的送药任务"""
        self.get_logger().info('开始执行送药任务...')

        # 1. 前往药品架
        self.current_state = 'going_to_shelf'
        self.get_logger().info('Step 1: 前往药品架')
        if not self.navigate_to_location('medicine_shelf'):
            self.get_logger().error('导航到药品架失败')
            return

        # 2. 抓取药品
        self.current_state = 'picking_medicine'
        self.get_logger().info('Step 2: 抓取药品')
        self.pick_medicine()
        time.sleep(2)

        # 3. 前往目标房间门口
        room_door = f'room_{self.current_room}_door'
        self.current_state = 'going_to_room'
        self.get_logger().info(f'Step 3: 前往 {self.current_room} 房间门口')
        if not self.navigate_to_location(room_door):
            self.get_logger().error('导航到房间门口失败')
            return

        # 4. 开门
        self.current_state = 'opening_door'
        self.get_logger().info('Step 4: 开门')
        self.open_door(self.current_room)
        time.sleep(3)

        # 5. 进入房间
        room_loc = f'room_{self.current_room}'
        self.current_state = 'entering_room'
        self.get_logger().info('Step 5: 进入房间')
        if not self.navigate_to_location(room_loc):
            self.get_logger().error('进入房间失败')
            return

        # 6. 前往床头柜
        nightstand = f'room_{self.current_room}_nightstand'
        self.current_state = 'going_to_nightstand'
        self.get_logger().info('Step 6: 前往床头柜')
        if not self.navigate_to_location(nightstand):
            self.get_logger().error('导航到床头柜失败')
            return

        # 7. 放置药品
        self.current_state = 'placing_medicine'
        self.get_logger().info('Step 7: 放置药品')
        self.place_medicine()
        time.sleep(2)

        # 8. 返回前台
        self.current_state = 'returning'
        self.get_logger().info('Step 8: 返回前台')
        if not self.navigate_to_location('reception'):
            self.get_logger().error('返回前台失败')
            return

        # 任务完成
        self.current_state = 'idle'
        self.get_logger().info(f'✅ 任务完成！{self.current_medicine} 已送达 {self.current_room} 房间')

    def navigate_to_location(self, location_name):
        """导航到指定位置 (使用Nav2)"""
        if location_name not in self.locations:
            self.get_logger().error(f'未知位置: {location_name}')
            return False

        x, y = self.locations[location_name]
        self.get_logger().info(f'导航到 {location_name}: ({x}, {y})')

        # 创建目标姿态
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.position.z = 0.0
        goal_msg.pose.pose.orientation.w = 1.0

        # 等待导航服务器
        if not self.nav_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('Nav2导航服务器未响应')
            return False

        # 发送目标
        self.get_logger().info('发送导航目标...')
        send_goal_future = self.nav_client.send_goal_async(goal_msg)

        rclpy.spin_until_future_complete(self, send_goal_future, timeout_sec=5.0)

        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            self.get_logger().error('导航目标被拒绝')
            return False

        self.get_logger().info('导航目标已接受，等待完成...')

        # 等待结果
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=60.0)

        result = result_future.result()
        if result:
            self.get_logger().info(f'✅ 到达 {location_name}')
            return True
        else:
            self.get_logger().error(f'导航超时或失败')
            return False

    def pick_medicine(self):
        """抓取药品（左臂）"""
        self.get_logger().info('🤖 左臂开始抓取药品...')

        # 左臂动作序列
        self.move_joint('left_shoulder_joint', 0.5, 2.0)
        time.sleep(2)
        self.move_joint('left_elbow_joint', 1.2, 2.0)
        time.sleep(2)
        self.move_joint('left_wrist_joint', -0.3, 2.0)
        time.sleep(2)

        self.get_logger().info('✅ 药品已抓取')

    def place_medicine(self):
        """放置药品（右臂）"""
        self.get_logger().info('🤖 右臂开始放置药品...')

        # 右臂动作序列
        self.move_joint('right_shoulder_joint', -0.5, 2.0)
        time.sleep(2)
        self.move_joint('right_elbow_joint', 1.5, 2.0)
        time.sleep(2)
        self.move_joint('right_wrist_joint', 0.3, 2.0)
        time.sleep(2)

        # 松开（复位）
        self.move_joint('right_wrist_joint', 0.0, 1.0)
        time.sleep(1)

        self.get_logger().info('✅ 药品已放置')

    def move_joint(self, joint_name, position, duration):
        """移动单个关节"""
        if joint_name in self.joint_publishers:
            msg = Float64()
            msg.data = position
            self.joint_publishers[joint_name].publish(msg)
            self.get_logger().info(f'移动关节 {joint_name} 到 {position} rad')

    def open_door(self, room_number):
        """开门"""
        msg = String()
        msg.data = f'open,door_{room_number}'
        self.door_control_pub.publish(msg)
        self.get_logger().info(f'发送开门命令: {room_number}')

    def go_to_floor(self, floor_number):
        """电梯控制"""
        msg = String()
        msg.data = str(floor_number)
        self.elevator_control_pub.publish(msg)
        self.get_logger().info(f'电梯前往 {floor_number} 楼')

def main(args=None):
    rclpy.init(args=args)
    controller = MedicineDeliveryController()

    try:
        rclpy.spin(controller)
    except KeyboardInterrupt:
        pass
    finally:
        controller.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
