#!/bin/bash
# ROS2 Jazzy + Gazebo Harmonic 快速启动脚本

echo "=========================================="
echo "养老院送药机器人仿真系统"
echo "ROS2 Jazzy + Gazebo Harmonic"
echo "=========================================="
echo ""

# 检查 ROS2 环境
if [ -z "$ROS_DISTRO" ]; then
    echo "❌ 错误: ROS2 环境未设置"
    echo "请运行: source /opt/ros/jazzy/setup.bash"
    exit 1
fi

if [ "$ROS_DISTRO" != "jazzy" ]; then
    echo "⚠️  警告: 当前 ROS 版本是 $ROS_DISTRO，推荐使用 Jazzy"
fi

echo "✓ ROS2 环境: $ROS_DISTRO"

# 检查 Gazebo Harmonic
if ! command -v gz &> /dev/null; then
    echo "❌ 错误: Gazebo Harmonic 未安装"
    echo "请运行: sudo apt install gz-harmonic"
    exit 1
fi

echo "✓ Gazebo Harmonic 已安装"

# 检查 ros_gz
if ! ros2 pkg list | grep -q "ros_gz_sim"; then
    echo "❌ 错误: ros_gz_sim 未安装"
    echo "请运行: sudo apt install ros-jazzy-ros-gz-sim"
    exit 1
fi

echo "✓ ros_gz_sim 已安装"

# 检查工作空间
if [ ! -d "$HOME/ros2_ws/install" ]; then
    echo "⚠️  警告: ROS2 工作空间未找到"
    echo "正在创建工作空间..."
    mkdir -p $HOME/ros2_ws/src
    cd $HOME/ros2_ws
    colcon build
fi

# Source 工作空间
if [ -f "$HOME/ros2_ws/install/setup.bash" ]; then
    source $HOME/ros2_ws/install/setup.bash
    echo "✓ ROS2 工作空间已加载"
else
    echo "❌ 错误: 工作空间未编译"
    echo "请运行: cd ~/ros2_ws && colcon build --packages-select nursing_home_sim"
    exit 1
fi

# 检查项目是否存在
if ! ros2 pkg list | grep -q "nursing_home_sim"; then
    echo "⚠️  警告: nursing_home_sim 包未找到"
    echo "请确保项目在 ~/ros2_ws/src/ 中并已编译"
    exit 1
fi

echo "✓ nursing_home_sim 包已找到"

# 设置脚本权限
if [ -d "$HOME/ros2_ws/src/nursing_home_sim/scripts" ]; then
    chmod +x $HOME/ros2_ws/src/nursing_home_sim/scripts/*.py
    echo "✓ 脚本权限已设置"
fi

echo ""
echo "=========================================="
echo "启动 Gazebo Harmonic 仿真环境..."
echo "=========================================="
echo ""

# 启动主仿真
ros2 launch nursing_home_sim nursing_home.launch.py

echo ""
echo "=========================================="
echo "系统已关闭"
echo "=========================================="
