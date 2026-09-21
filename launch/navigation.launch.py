#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    # 获取包路径
    pkg_name = 'nursing_home_sim'
    pkg_share = get_package_share_directory(pkg_name)
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    # 配置文件路径
    map_file = os.path.join(pkg_share, 'maps', 'nursing_home_map.yaml')
    nav2_params_file = os.path.join(pkg_share, 'config', 'nav2_params.yaml')

    # Nav2 启动 (禁用 collision_monitor)
    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': map_file,
            'yaml_filename': map_file,
            'params_file': nav2_params_file,
            'use_sim_time': 'True',
            'autostart': 'True',
            'use_composition': 'False',
            'use_respawn': 'False'
        }.items()
    )

    return LaunchDescription([
        nav2_bringup
    ])
