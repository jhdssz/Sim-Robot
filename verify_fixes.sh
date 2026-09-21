#!/bin/bash

echo "================================"
echo "验证修复结果"
echo "================================"

echo ""
echo "步骤 1: 重新构建包..."
cd /mnt/d/Sim-Robot
colcon build --packages-select nursing_home_sim

echo ""
echo "步骤 2: Source 环境..."
source install/setup.bash

echo ""
echo "步骤 3: 启动仿真..."
ros2 launch nursing_home_sim nursing_home.launch.py &
LAUNCH_PID=$!
sleep 15

echo ""
echo "================================"
echo "验证 1: 检查 collision_monitor"
echo "================================"
echo "检查 collision_monitor 是否成功配置..."
ros2 node list | grep collision_monitor
if [ $? -eq 0 ]; then
    echo "✓ collision_monitor 节点存在"
else
    echo "✗ collision_monitor 节点未找到"
fi

echo ""
echo "================================"
echo "验证 2: 检查 /scan frame_id"
echo "================================"
echo "检查 LaserScan 的 frame_id..."
ros2 topic echo /scan --once | grep frame_id
echo "期望: frame_id: laser_link"

echo ""
echo "================================"
echo "验证 3: 检查 TF 树"
echo "================================"
echo "检查 laser_link 是否在 TF 树中..."
ros2 run tf2_ros tf2_echo base_link laser_link
if [ $? -eq 0 ]; then
    echo "✓ base_link -> laser_link transform 存在"
else
    echo "✗ base_link -> laser_link transform 不存在"
fi

echo ""
echo "================================"
echo "验证 4: 检查 AMCL 错误"
echo "================================"
echo "等待 10 秒，检查是否还有 AMCL transform 错误..."
sleep 10
echo "如果没有看到 'timestamp on the message is earlier' 错误，说明修复成功"

echo ""
echo "================================"
echo "验证 5: 检查机器人可见性"
echo "================================"
echo "打开 Gazebo GUI 检查机器人是否可见"
echo "期望位置: x=0.5, y=0, z=0.2"

echo ""
echo "================================"
echo "验证 6: 测试运动控制"
echo "================================"
echo "发送速度命令..."
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.0}}"
sleep 2
echo "检查 odometry..."
ros2 topic echo /odom --once | grep "position:"

echo ""
echo "================================"
echo "清理"
echo "================================"
kill $LAUNCH_PID
echo "验证完成！"
