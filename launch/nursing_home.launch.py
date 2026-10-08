#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.conditions import IfCondition
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
            '-x', '-1.0',
            '-y', '0.0',
            '-Y', '0.0',
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

    # Explicit one-way bridges; only DiffDrive owns odom -> base_link TF.
    robot_bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge',
        parameters=[{'config_file': os.path.join(pkg_share, 'config', 'ros_gz_bridge.yaml'),
                     'use_sim_time': True}], output='screen'
    )

    # Always keep the raw bridge and filter independent of Nav2 startup.
    scan_self_filter = Node(
        package=pkg_name, executable='scan_self_filter.py',
        name='scan_self_filter', output='screen',
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    # 导航启动
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'navigation.launch.py')
        ),
        condition=IfCondition(LaunchConfiguration('navigation'))
    )

    # 送药控制器
    medicine_delivery_controller = Node(
        package=pkg_name,
        executable='medicine_delivery_controller.py',
        name='medicine_delivery_controller',
        output='screen',
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('task_controllers'))
    )

    # 101/102 entrances are temporarily open; keep door_controller.py dormant.

    # 电梯控制器
    elevator_controller = Node(
        package=pkg_name,
        executable='elevator_controller.py',
        name='elevator_controller',
        output='screen',
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('task_controllers'))
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('navigation', default_value='false',
                              description='Enable Nav2 after model/sensor validation'),
        DeclareLaunchArgument('task_controllers', default_value='false',
                              description='Enable delivery, door and elevator demos'),
        gz_sim,
        robot_bridge,
        scan_self_filter,
        robot_state_publisher,
        spawn_robot,
        navigation,
        medicine_delivery_controller,
        elevator_controller
    ])
