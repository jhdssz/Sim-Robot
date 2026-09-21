# ROS2 Jazzy + Gazebo Harmonic 命令速查表

## 🚀 启动命令

```bash
# 快速启动（推荐）
cd /mnt/d/Sim-Robot
./start_simulation.sh

# 完整测试启动
./full_test.sh

# 手动启动
ros2 launch nursing_home_sim nursing_home.launch.py
```

## 📦 依赖安装

```bash
# 一键安装所有依赖
sudo apt install -y \
  gz-harmonic \
  ros-jazzy-ros-gz \
  ros-jazzy-ros-gz-sim \
  ros-jazzy-ros-gz-bridge \
  ros-jazzy-navigation2 \
  ros-jazzy-nav2-bringup \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-xacro
```

## 🔨 编译命令

```bash
# 编译项目
cd ~/ros2_ws
colcon build --packages-select nursing_home_sim

# 仅编译（不安装）
colcon build --packages-select nursing_home_sim --cmake-args -DBUILD_TESTING=OFF

# 清理重编译
rm -rf build/ install/ log/
colcon build --packages-select nursing_home_sim

# 符号链接模式（开发用）
colcon build --packages-select nursing_home_sim --symlink-install
```

## 🎮 控制命令

### 送药任务
```bash
# 送药到 101 房间
ros2 topic pub /medicine_delivery_task std_msgs/msg/String "data: '阿司匹林,101'" --once

# 送药到 102 房间
ros2 topic pub /medicine_delivery_task std_msgs/msg/String "data: '降压药,102'" --once
```

### 手动控制
```bash
# 前进
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# 后退
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: -0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# 左转
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"

# 右转
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: -0.5}}"

# 停止
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

### 门控制
```bash
# 开门 101
ros2 topic pub /door_control std_msgs/msg/String "data: 'open,door_101'" --once

# 关门 101
ros2 topic pub /door_control std_msgs/msg/String "data: 'close,door_101'" --once

# 开门 102
ros2 topic pub /door_control std_msgs/msg/String "data: 'open,door_102'" --once
```

### 电梯控制
```bash
# 前往 2 楼
ros2 topic pub /elevator_control std_msgs/msg/String "data: '2'" --once

# 返回 1 楼
ros2 topic pub /elevator_control std_msgs/msg/String "data: '1'" --once
```

### 机械臂控制
```bash
# 左肩
ros2 topic pub /dual_arm_robot/left_shoulder_joint/command std_msgs/msg/Float64 "data: 0.5"

# 左肘
ros2 topic pub /dual_arm_robot/left_elbow_joint/command std_msgs/msg/Float64 "data: 1.2"

# 左手腕
ros2 topic pub /dual_arm_robot/left_wrist_joint/command std_msgs/msg/Float64 "data: -0.3"

# 右肩
ros2 topic pub /dual_arm_robot/right_shoulder_joint/command std_msgs/msg/Float64 "data: -0.5"

# 右肘
ros2 topic pub /dual_arm_robot/right_elbow_joint/command std_msgs/msg/Float64 "data: 1.5"

# 右手腕
ros2 topic pub /dual_arm_robot/right_wrist_joint/command std_msgs/msg/Float64 "data: 0.3"
```

## 🔍 调试命令

### 话题操作
```bash
# 列出所有话题
ros2 topic list

# 查看话题详情
ros2 topic info /cmd_vel

# 监听话题
ros2 topic echo /odom

# 查看话题频率
ros2 topic hz /cmd_vel

# 查看话题带宽
ros2 topic bw /scan
```

### 节点操作
```bash
# 列出所有节点
ros2 node list

# 查看节点详情
ros2 node info /medicine_delivery_controller

# 查看节点参数
ros2 param list /robot_state_publisher
```

### 服务操作
```bash
# 列出所有服务
ros2 service list

# 调用服务
ros2 service call /service_name std_srvs/srv/Empty
```

### TF 调试
```bash
# 查看 TF 树
ros2 run tf2_tools view_frames

# 查看 TF 变换
ros2 run tf2_ros tf2_echo map base_link

# 监听 TF
ros2 topic echo /tf
```

### Gazebo 命令
```bash
# 启动 Gazebo
gz sim

# 带世界文件启动
gz sim -r /path/to/world.sdf

# 列出模型
gz model --list

# 查看插件
gz plugin --list
```

## 🧪 测试命令

```bash
# 运行送药测试
ros2 run nursing_home_sim test_delivery.py

# 运行机械臂测试
ros2 run nursing_home_sim test_arms.py

# 键盘控制
ros2 run nursing_home_sim keyboard_control.py
```

## 📊 性能监控

```bash
# 查看 CPU 使用
top -p $(pgrep -d',' gz_sim)

# 查看内存使用
free -h

# 查看 ROS2 进程
ros2 daemon status

# 查看日志
journalctl -f | grep ros2
```

## 🐛 故障排查

```bash
# 检查 ROS1 残留
cd /mnt/d/Sim-Robot
./check_ros1_residue.sh

# 清理日志
rm -rf ~/.ros/log/*

# 重启 ROS2 守护进程
ros2 daemon stop
ros2 daemon start

# 杀死所有 Gazebo 进程
killall -9 gz_sim ruby

# 查看错误日志
cat ~/.ros/log/latest/roslaunch-*.log
```

## 🎯 快捷别名（可选）

添加到 `~/.bashrc`:

```bash
# ROS2 Jazzy 快捷命令
alias r2='source /opt/ros/jazzy/setup.bash'
alias ws='cd ~/ros2_ws && source install/setup.bash'
alias cb='cd ~/ros2_ws && colcon build --packages-select nursing_home_sim'
alias tl='ros2 topic list'
alias nl='ros2 node list'
alias nursing='ros2 launch nursing_home_sim nursing_home.launch.py'

# Gazebo 快捷命令
alias gzs='gz sim'
alias gzk='killall -9 gz_sim ruby'

# 导航到项目
alias cdnursing='cd /mnt/d/Sim-Robot'
```

使用方法：
```bash
source ~/.bashrc
r2        # Source ROS2
ws        # 进入工作空间并 source
cb        # 编译项目
nursing   # 启动仿真
```

## 📚 常用查询

```bash
# 查找包
ros2 pkg list | grep nursing

# 查找可执行文件
ros2 pkg executables nursing_home_sim

# 查找 launch 文件
ros2 launch --show-args nursing_home_sim nursing_home.launch.py

# 查看接口定义
ros2 interface show geometry_msgs/msg/Twist
```

## 🔄 版本信息

```bash
# ROS2 版本
ros2 --version

# Gazebo 版本
gz sim --version

# Python 版本
python3 --version

# 系统版本
lsb_release -a
```

## 💾 数据记录

```bash
# 录制所有话题
ros2 bag record -a -o my_bag

# 录制特定话题
ros2 bag record /cmd_vel /odom -o my_bag

# 播放录制
ros2 bag play my_bag

# 查看包信息
ros2 bag info my_bag
```

---

**快捷键提示**:
- `Ctrl+C` - 停止当前进程
- `Ctrl+Z` - 暂停当前进程
- `fg` - 恢复后台进程
- `Tab` - 自动补全

**提示**: 建议将常用命令保存为脚本或别名，提高开发效率！
