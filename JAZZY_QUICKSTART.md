# ROS2 Jazzy + Gazebo Harmonic 快速开始指南

## 🚀 快速启动（3步）

```bash
# 1. 编译项目
cd ~/ros2_ws
colcon build --packages-select nursing_home_sim

# 2. Source 环境
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

# 3. 启动仿真
ros2 launch nursing_home_sim nursing_home.launch.py
```

## 📦 依赖安装（首次运行）

```bash
# Gazebo Harmonic
sudo apt install gz-harmonic

# ros_gz 桥接
sudo apt install ros-jazzy-ros-gz ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge

# Nav2 导航
sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup

# 其他工具
sudo apt install ros-jazzy-robot-state-publisher ros-jazzy-xacro
```

## 🎮 发送任务

```bash
# 送药到 101 房间
ros2 topic pub /medicine_delivery_task std_msgs/msg/String "data: '阿司匹林,101'" --once

# 送药到 102 房间
ros2 topic pub /medicine_delivery_task std_msgs/msg/String "data: '降压药,102'" --once
```

## 🔍 调试命令

```bash
# 查看所有话题
ros2 topic list

# 查看节点
ros2 node list

# 查看机器人描述
ros2 topic echo /robot_description --once

# 查看机器人位置
ros2 topic echo /odom

# 手动控制机器人
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.0}}"
```

## 🧪 运行测试

```bash
# 测试送药系统
ros2 run nursing_home_sim test_delivery.py

# 测试机械臂
ros2 run nursing_home_sim test_arms.py

# 键盘控制
ros2 run nursing_home_sim keyboard_control.py
```

## ⚠️ 常见问题

### Q: PackageNotFoundError: "package 'gazebo_ros' not found"
**A:** 这个错误说明还有 ROS1 残留。确认：
```bash
# 检查 launch 文件
grep -r "gazebo_ros" ~/ros2_ws/src/nursing_home_sim/

# 应该没有输出，如果有，说明文件未更新
```

### Q: Gazebo 启动失败
```bash
# 检查 Gazebo Harmonic
gz sim --version

# 应该显示类似: Gazebo Sim, version 8.x.x
```

### Q: 机器人未出现
```bash
# 检查生成命令
ros2 run ros_gz_sim create --help

# 手动生成测试
ros2 run ros_gz_sim create -name test_robot -x 0 -y 0 -z 1
```

### Q: 编译错误
```bash
# 清理并重新编译
cd ~/ros2_ws
rm -rf build/ install/ log/
colcon build --packages-select nursing_home_sim
```

## 📊 验证检查清单

- [ ] ✅ `colcon build` 成功
- [ ] ✅ Gazebo Harmonic 窗口打开
- [ ] ✅ 机器人在 Gazebo 中显示
- [ ] ✅ `ros2 topic list` 显示 `/cmd_vel`, `/odom` 等话题
- [ ] ✅ `ros2 node list` 显示所有控制器节点
- [ ] ✅ 发送速度命令后机器人移动
- [ ] ✅ Nav2 导航正常工作

## 🆚 ROS1 vs ROS2 命令对比

| 功能 | ROS1 | ROS2 Jazzy |
|------|------|------------|
| 启动 | `roslaunch pkg file.launch` | `ros2 launch pkg file.launch.py` |
| 话题列表 | `rostopic list` | `ros2 topic list` |
| 发布话题 | `rostopic pub /topic ...` | `ros2 topic pub /topic ... --once` |
| 节点列表 | `rosnode list` | `ros2 node list` |
| 包查找 | `rospack find pkg` | `ros2 pkg prefix pkg` |
| Gazebo | `gazebo` | `gz sim` |

## 📁 项目结构（已更新）

```
nursing_home_sim/
├── launch/
│   ├── nursing_home.launch.py    ✅ ROS2 + ros_gz
│   └── navigation.launch.py      ✅ ROS2 + Nav2
├── urdf/
│   └── dual_arm_mobile_robot.urdf ✅ Gazebo Harmonic 插件
├── scripts/                       ✅ 全部使用 rclpy
├── config/
│   └── nav2_params.yaml          ✅ Nav2 参数
├── worlds/
│   └── nursing_home.world        ✅ Gazebo 世界文件
├── package.xml                    ✅ ros_gz 依赖
└── CMakeLists.txt                ✅ ament_cmake
```

## 🎯 下一步

1. **测试完整流程**：启动仿真 → 发送任务 → 观察执行
2. **调整参数**：根据需要修改 `nav2_params.yaml`
3. **扩展功能**：添加传感器、优化路径规划

## 📚 相关资源

- [Gazebo Harmonic 文档](https://gazebosim.org/docs/harmonic)
- [ros_gz 仓库](https://github.com/gazebosim/ros_gz)
- [Nav2 教程](https://navigation.ros.org/)
- [ROS2 Jazzy 发布说明](https://docs.ros.org/en/jazzy/)

---

**最后更新**: 2026-09-18  
**状态**: ✅ 完全兼容 ROS2 Jazzy + Gazebo Harmonic
