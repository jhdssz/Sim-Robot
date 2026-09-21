#!/bin/bash

echo "================================"
echo "验证双机械臂补全"
echo "================================"
echo ""

echo "步骤 1: 检查 SDF 文件..."
LINK_COUNT=$(grep -c 'link name=' D:/Sim-Robot/models/dual_arm_robot/model.sdf)
JOINT_COUNT=$(grep -c 'joint name=' D:/Sim-Robot/models/dual_arm_robot/model.sdf)

echo "Links: $LINK_COUNT (期望: 19)"
echo "Joints: $JOINT_COUNT (期望: 18)"

if [ "$LINK_COUNT" -eq 19 ] && [ "$JOINT_COUNT" -eq 18 ]; then
    echo "✓ SDF 文件结构完整"
else
    echo "✗ SDF 文件结构不完整"
    exit 1
fi

echo ""
echo "步骤 2: 重新构建..."
cd /mnt/d/Sim-Robot
source /opt/ros/jazzy/setup.bash
colcon build --packages-select nursing_home_sim
source install/setup.bash

echo ""
echo "步骤 3: 启动仿真..."
ros2 launch nursing_home_sim nursing_home.launch.py &
LAUNCH_PID=$!
echo "等待仿真启动..."
sleep 15

echo ""
echo "================================"
echo "验证 1: 检查 Gazebo 模型结构"
echo "================================"
gz model -m dual_arm_robot -l

echo ""
echo "检查关键 links 是否存在..."
gz model -m dual_arm_robot -l | grep -E "left_upper_arm|left_gripper|right_upper_arm|right_gripper"

if [ $? -eq 0 ]; then
    echo "✓ 机械臂 links 存在"
else
    echo "✗ 机械臂 links 缺失"
fi

echo ""
echo "================================"
echo "验证 2: 检查 Joint States"
echo "================================"
ros2 topic echo /joint_states --once | grep -E "left_shoulder_joint|left_elbow_joint|right_shoulder_joint|right_elbow_joint"

if [ $? -eq 0 ]; then
    echo "✓ 机械臂关节状态正常发布"
else
    echo "✗ 机械臂关节状态未发布"
fi

echo ""
echo "================================"
echo "验证 3: 检查其他功能"
echo "================================"

echo "检查 /scan frame_id..."
SCAN_FRAME=$(ros2 topic echo /scan --once 2>/dev/null | grep "frame_id:" | head -1)
echo "$SCAN_FRAME"

echo ""
echo "检查机器人位置..."
gz model -m dual_arm_robot --pose

echo ""
echo "================================"
echo "验证总结"
echo "================================"
echo ""
echo "请在 Gazebo GUI 中确认："
echo "□ 能看到完整的左臂（shoulder -> upper_arm -> elbow -> forearm -> wrist -> gripper）"
echo "□ 能看到完整的右臂（shoulder -> upper_arm -> elbow -> forearm -> wrist -> gripper）"
echo "□ 底盘、轮子、躯干、LiDAR 仍然可见"
echo "□ 所有组件位置和连接正确"
echo ""

echo "清理..."
kill $LAUNCH_PID 2>/dev/null
echo "验证完成！"
