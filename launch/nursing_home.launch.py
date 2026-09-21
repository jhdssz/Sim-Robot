#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import xacro

def generate_launch_description():
    # 获取包路径
    pkg_name = 'nursing_home_sim'
    pkg_share = get_package_share_directory(pkg_name)

    # 文件路径
    world_file = os.path.join(pkg_share, 'worlds', 'nursing_home.world')
    urdf_file = os.path.join(pkg_share, 'urdf', 'dual_arm_mobile_robot.urdf')
    sdf_file = os.path.join(pkg_share, 'models', 'dual_arm_robot', 'model.sdf')

    # 处理 URDF
    robot_description = xacro.process_file(urdf_file).toxml()

    # Gazebo Harmonic 启动 (使用 ros_gz_sim)
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            ])
        ]),
        launch_arguments={
            'gz_args': f'-r {world_file}',
            'on_exit_shutdown': 'True'
        }.items()
    )

    # 在 Gazebo 中生成机器人 (使用 SDF 文件)
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'dual_arm_robot',
            '-file', sdf_file,
            '-x', '0.5',
            '-y', '0.0',
            '-z', '0.2'
        ],
        output='screen'
    )

    # Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True
        }]
    )

    # ROS-Gazebo Bridge
    # Clock bridge
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen'
    )

    # cmd_vel bridge (ROS -> Gazebo only)
    cmd_vel_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist'],
        output='screen'
    )

    # odom bridge (Gazebo -> ROS)
    odom_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry'],
        output='screen'
    )

    # scan bridge (Gazebo -> ROS)
    scan_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan'],
        output='screen'
    )

    # 导航启动
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'navigation.launch.py')
        )
    )

    # 送药控制器
    medicine_delivery_controller = Node(
        package=pkg_name,
        executable='medicine_delivery_controller.py',
        name='medicine_delivery_controller',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    # 门控制器
    door_controller = Node(
        package=pkg_name,
        executable='door_controller.py',
        name='door_controller',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    # 电梯控制器
    elevator_controller = Node(
        package=pkg_name,
        executable='elevator_controller.py',
        name='elevator_controller',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    return LaunchDescription([
        gz_sim,
        clock_bridge,
        cmd_vel_bridge,
        odom_bridge,
        scan_bridge,
        robot_state_publisher,
        spawn_robot,
        navigation,
        medicine_delivery_controller,
        door_controller,
        elevator_controller
    ])
