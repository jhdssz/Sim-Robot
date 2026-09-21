#!/bin/bash

echo "================================"
echo "验证 /cmd_vel 单向 bridge 修复"
echo "================================"
echo ""

echo "步骤 1: 重新构建..."
cd /mnt/d/Sim-Robot
source /opt/ros/jazzy/setup.bash
colcon build --packages-select nursing_home_sim
source install/setup.bash

echo ""
echo "步骤 2: 启动仿真..."
ros2 launch nursing_home_sim nursing_home.launch.py &
LAUNCH_PID=$!
echo "等待仿真启动..."
sleep 15

echo ""
echo "================================"
echo "验证 1: 记录初始位置"
echo "================================"
echo "查询机器人初始 pose..."
INITIAL_POSE=$(gz model -m dual_arm_robot --pose 2>&1)
echo "初始位置："
echo "$INITIAL_POSE"
echo ""

# 提取初始 x 和 y 坐标
INITIAL_X=$(echo "$INITIAL_POSE" | grep -oP 'x: \K[0-9.-]+' | head -1)
INITIAL_Y=$(echo "$INITIAL_POSE" | grep -oP 'y: \K[0-9.-]+' | head -1)
echo "初始 X: $INITIAL_X"
echo "初始 Y: $INITIAL_Y"

echo ""
echo "================================"
echo "验证 2: 等待 10 秒观察位置变化"
echo "================================"
echo "等待中..."
sleep 10

echo "10 秒后查询机器人 pose..."
FINAL_POSE=$(gz model -m dual_arm_robot --pose 2>&1)
echo "最终位置："
echo "$FINAL_POSE"
echo ""

# 提取最终 x 和 y 坐标
FINAL_X=$(echo "$FINAL_POSE" | grep -oP 'x: \K[0-9.-]+' | head -1)
FINAL_Y=$(echo "$FINAL_POSE" | grep -oP 'y: \K[0-9.-]+' | head -1)
echo "最终 X: $FINAL_X"
echo "最终 Y: $FINAL_Y"

# 计算位置变化
X_DIFF=$(echo "$FINAL_X - $INITIAL_X" | bc -l)
Y_DIFF=$(echo "$FINAL_Y - $INITIAL_Y" | bc -l)
echo ""
echo "位置变化："
echo "ΔX: $X_DIFF"
echo "ΔY: $Y_DIFF"

# 检查位置是否稳定（容差 0.01m）
X_STABLE=$(echo "$X_DIFF < 0.01 && $X_DIFF > -0.01" | bc -l)
Y_STABLE=$(echo "$Y_DIFF < 0.01 && $Y_DIFF > -0.01" | bc -l)

if [ "$X_STABLE" -eq 1 ] && [ "$Y_STABLE" -eq 1 ]; then
    echo "✓ 机器人位置稳定，没有意外移动"
else
    echo "✗ 警告：机器人位置发生变化！"
fi

echo ""
echo "================================"
echo "验证 3: 检查 /cmd_vel 话题内容"
echo "================================"
echo "监听 /cmd_vel 5 秒..."
timeout 5 ros2 topic echo /cmd_vel 2>&1 | head -20 &
ECHO_PID=$!
sleep 5
kill $ECHO_PID 2>/dev/null

echo ""
echo "如果没有看到持续的 'linear.x = 0.2' 或其他非零值，说明正常"

echo ""
echo "================================"
echo "验证 4: 检查 /cmd_vel 话题信息"
echo "================================"
ros2 topic info /cmd_vel -v

echo ""
echo "================================"
echo "验证 5: 检查 bridge 日志"
echo "================================"
echo "检查 parameter_bridge 是否只订阅 ROS /cmd_vel..."
ps aux | grep parameter_bridge | grep -v grep

echo ""
echo "================================"
echo "验证总结"
echo "================================"
echo ""
echo "请确认："
echo "□ 机器人位置没有变化（ΔX 和 ΔY 接近 0）"
echo "□ /cmd_vel 话题没有持续的非零速度命令"
echo "□ ros2 topic info 显示 ros_gz_bridge 只作为 Subscriber，不是 Publisher"
echo "□ 日志显示 'Creating ROS->GZ Bridge: /cmd_vel'，没有 'Creating GZ->ROS Bridge: /cmd_vel'"
echo ""

echo "清理..."
kill $LAUNCH_PID 2>/dev/null
sleep 2
echo "测试完成！"
