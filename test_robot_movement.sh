#!/bin/bash

# ROS2 Jazzy + Gazebo Harmonic 机器人运动测试脚本

echo "================================================"
echo "机器人运动链路验证测试"
echo "================================================"

echo ""
echo "第一步：检查 ROS2 topics"
echo "------------------------"
ros2 topic list | grep -E "cmd_vel|scan|odom"

echo ""
echo "第二步：检查 Gazebo topics"
echo "------------------------"
gz topic -l | grep -E "cmd_vel|scan|odom"

echo ""
echo "第三步：检查 /cmd_vel topic 详情"
echo "------------------------"
ros2 topic info /cmd_vel -v

echo ""
echo "第四步：检查 /odom topic 详情"
echo "------------------------"
ros2 topic info /odom -v

echo ""
echo "第五步：检查 /scan topic 详情"
echo "------------------------"
ros2 topic info /scan -v

echo ""
echo "第六步：测试机器人前进 (5秒)"
echo "------------------------"
echo "发送前进命令..."
timeout 5 ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.0}}"

echo ""
echo "第七步：测试机器人旋转 (5秒)"
echo "------------------------"
echo "发送旋转命令..."
timeout 5 ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.5}}"

echo ""
echo "第八步：检查 /odom 数据"
echo "------------------------"
ros2 topic echo /odom --once

echo ""
echo "第九步：检查 /scan 数据"
echo "------------------------"
ros2 topic echo /scan --once

echo ""
echo "================================================"
echo "测试完成"
echo "================================================"
