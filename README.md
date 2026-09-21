# 养老院送药机器人仿真系统 (ROS2)

这是一个基于ROS2和Gazebo的养老院双臂送药机器人仿真项目。机器人可以接收指令，自主导航到药品架抓取药品，然后送到指定房间的床头柜。

## 功能特点

- ✅ 完整的养老院环境（前台、房间、电梯、走廊）
- ✅ 轮式双臂机器人模型
- ✅ 自主导航系统（Nav2）
- ✅ 自动开门功能
- ✅ 药品抓取和放置
- ✅ 电梯控制（支持多楼层）

## 系统要求

- Ubuntu 20.04 / 22.04
- ROS2 Foxy / Galactic / Humble
- Gazebo 11+
- Python 3.8+

## 项目结构

```
D:\Sim-Robot\
├── worlds/                    # Gazebo世界文件
│   └── nursing_home.world    # 养老院环境
├── urdf/                      # 机器人模型
│   └── dual_arm_mobile_robot.urdf
├── launch/                    # 启动文件 (Python)
│   ├── nursing_home.launch.py   # 主启动文件
│   └── navigation.launch.py     # 导航启动文件
├── scripts/                   # Python脚本
│   ├── medicine_delivery_controller.py  # 主控制器
│   ├── door_controller.py              # 门控制
│   ├── elevator_controller.py          # 电梯控制
│   ├── keyboard_control.py             # 键盘控制
│   ├── test_delivery.py                # 送药测试
│   └── test_arms.py                    # 机械臂测试
├── config/                    # 配置文件
│   └── nav2_params.yaml      # Nav2导航参数
├── maps/                      # 地图文件
│   └── nursing_home_map.yaml
├── package.xml
└── CMakeLists.txt
```

## 安装步骤

### 1. 安装依赖

```bash
sudo apt update
sudo apt install ros-humble-gazebo-ros-pkgs
sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup
sudo apt install ros-humble-robot-state-publisher
sudo apt install ros-humble-joint-state-publisher
sudo apt install ros-humble-xacro
```

### 2. 创建工作空间并编译

```bash
# 创建ROS2工作空间
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

# 复制项目到src目录
cp -r /mnt/d/Sim-Robot ./nursing_home_sim

# 编译
cd ~/ros2_ws
colcon build --packages-select nursing_home_sim

# 添加到环境变量
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 3. 设置脚本权限

```bash
cd ~/ros2_ws/src/nursing_home_sim/scripts
chmod +x *.py
```

## 使用方法

### 启动仿真环境

```bash
# 启动完整仿真系统
ros2 launch nursing_home_sim nursing_home.launch.py
```

这将启动：
- Gazebo仿真环境
- 养老院世界
- 双臂机器人
- Nav2导航系统
- 所有控制器

### 发送送药任务

```bash
# 格式: "药品名称,房间号"
# 送阿司匹林到101房间
ros2 topic pub /medicine_delivery_task std_msgs/msg/String "data: '阿司匹林,101'" --once

# 送降压药到102房间
ros2 topic pub /medicine_delivery_task std_msgs/msg/String "data: '降压药,102'" --once
```

### 运行测试脚本

```bash
# 测试送药系统
ros2 run nursing_home_sim test_delivery.py

# 测试机械臂
ros2 run nursing_home_sim test_arms.py
```

### 键盘控制

```bash
# 使用键盘控制机器人
ros2 run nursing_home_sim keyboard_control.py
```

### 手动控制电梯

```bash
# 前往2楼
ros2 topic pub /elevator_control std_msgs/msg/String "data: '2'" --once

# 返回1楼
ros2 topic pub /elevator_control std_msgs/msg/String "data: '1'" --once
```

### 手动控制门

```bash
# 打开101房间的门
ros2 topic pub /door_control std_msgs/msg/String "data: 'open,door_101'" --once

# 关闭101房间的门
ros2 topic pub /door_control std_msgs/msg/String "data: 'close,door_101'" --once
```

## 工作流程

1. **接收任务**: 机器人在前台待命，接收送药任务
2. **获取药品**: 导航到药品架，使用左臂抓取指定药品
3. **前往房间**: 使用Nav2导航到目标房间门口
4. **开门**: 发送开门命令
5. **进入房间**: 进入房间并导航到床头柜
6. **放置药品**: 使用机械臂将药品放在床头柜上
7. **返回前台**: 返回前台等待下一个任务

## 机器人控制

### 速度控制
```bash
# 手动控制机器人移动
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

### 关节控制
```bash
# 控制左肩关节
ros2 topic pub /dual_arm_robot/left_shoulder_joint/command std_msgs/msg/Float64 "data: 0.5"

# 控制左肘关节
ros2 topic pub /dual_arm_robot/left_elbow_joint/command std_msgs/msg/Float64 "data: 1.0"
```

## 环境说明

### 房间布局
- **前台区域**: 坐标 (2, 0)，包含药品架
- **101房间**: 坐标 (10, 5)，包含床和床头柜
- **102房间**: 坐标 (10, -5)，包含床和床头柜
- **电梯**: 坐标 (-5, 0)，支持多楼层移动

### 机器人规格
- **底盘**: 四轮差速驱动，尺寸 0.6m × 0.4m × 0.2m
- **左臂**: 3自由度（肩、肘、腕）
- **右臂**: 3自由度（肩、肘、腕）
- **最大速度**: 0.26 m/s
- **最大旋转速度**: 1.0 rad/s

## 故障排除

### 问题：机器人不移动
```bash
# 检查Nav2导航状态
ros2 topic echo /navigate_to_pose/_action/status

# 检查速度命令
ros2 topic echo /cmd_vel
```

### 问题：门无法打开
```bash
# 检查门控制器是否运行
ros2 node list | grep door

# 手动发送开门命令
ros2 topic pub /door_control std_msgs/msg/String "data: 'open,door_101'" --once
```

### 问题：机械臂不动
```bash
# 检查关节控制话题
ros2 topic list | grep joint

# 手动测试关节
ros2 topic pub /dual_arm_robot/left_shoulder_joint/command std_msgs/msg/Float64 "data: 0.3"
```

## 扩展功能

### 添加新房间
1. 在 `nursing_home.world` 中添加房间模型
2. 在 `medicine_delivery_controller.py` 的 `locations` 字典中添加坐标
3. 添加对应的床头柜偏移量

### 添加新药品
任务命令中的药品名称可以是任意字符串，系统会记录并执行相应的抓取动作。

### 多楼层支持
系统已包含电梯控制，可以扩展到多楼层场景。修改 `elevator_controller.py` 中的楼层高度配置。

## 调试技巧

### 查看所有话题
```bash
ros2 topic list
```

### 查看机器人位置
```bash
ros2 topic echo /odom
```

### 可视化导航
```bash
ros2 run rviz2 rviz2
```

在RViz2中添加：
- Map
- Path
- RobotModel
- LaserScan
- TF

## 性能优化

- 调整 `nav2_params.yaml` 以优化路径规划
- 修改代价地图参数调整障碍物检测
- 在 `nursing_home.world` 中调整物理参数以提高仿真速度

## ROS2特性

本项目使用以下ROS2特性：
- **Nav2导航栈**: 替代ROS1的move_base
- **Python Launch文件**: 更灵活的启动配置
- **rclpy**: ROS2的Python客户端库
- **Action客户端**: 用于导航目标

## 贡献

欢迎提交问题和改进建议！

## 许可证

MIT License

## 联系方式

如有问题，请通过GitHub Issues联系。
