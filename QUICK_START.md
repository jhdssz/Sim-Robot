# 养老院送药机器人 - 快速参考指南 (ROS2)

## 快速启动

### 方法1：使用启动脚本（推荐）
```bash
cd /mnt/d/Sim-Robot
chmod +x start_simulation.sh
./start_simulation.sh
```

### 方法2：手动启动
```bash
# 启动完整仿真系统（包含所有控制器）
ros2 launch nursing_home_sim nursing_home.launch.py
```

## 常用命令

### 发送送药任务
```bash
# 送药到101房间
ros2 topic pub /medicine_delivery_task std_msgs/msg/String "data: '阿司匹林,101'" --once

# 送药到102房间
ros2 topic pub /medicine_delivery_task std_msgs/msg/String "data: '降压药,102'" --once
```

### 控制电梯
```bash
# 前往2楼
ros2 topic pub /elevator_control std_msgs/msg/String "data: '2'" --once

# 返回1楼
ros2 topic pub /elevator_control std_msgs/msg/String "data: '1'" --once
```

### 控制门
```bash
# 打开门
ros2 topic pub /door_control std_msgs/msg/String "data: 'open,door_101'" --once

# 关闭门
ros2 topic pub /door_control std_msgs/msg/String "data: 'close,door_101'" --once
```

### 手动控制机器人
```bash
# 方法1：使用键盘控制脚本
ros2 run nursing_home_sim keyboard_control.py

# 方法2：直接发布速度命令
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

### 控制机械臂
```bash
# 左肩
ros2 topic pub /dual_arm_robot/left_shoulder_joint/command std_msgs/msg/Float64 "data: 0.5"

# 左肘
ros2 topic pub /dual_arm_robot/left_elbow_joint/command std_msgs/msg/Float64 "data: 1.2"

# 右肩
ros2 topic pub /dual_arm_robot/right_shoulder_joint/command std_msgs/msg/Float64 "data: 0.3"

# 右肘
ros2 topic pub /dual_arm_robot/right_elbow_joint/command std_msgs/msg/Float64 "data: 0.8"
```

## 位置坐标

| 位置 | X | Y | 说明 |
|------|---|---|------|
| 前台 | 2.0 | 0.0 | 机器人初始位置 |
| 药品架 | 1.5 | -0.8 | 药品存放处 |
| 101房间 | 10.0 | 5.0 | 病人房间 |
| 102房间 | 10.0 | -5.0 | 病人房间 |
| 电梯 | -5.0 | 0.0 | 电梯位置 |
| 101门 | 9.0 | 5.0 | 101房间门口 |
| 102门 | 9.0 | -5.0 | 102房间门口 |

## 调试命令

### 查看所有话题
```bash
ros2 topic list
```

### 查看机器人位置
```bash
ros2 topic echo /odom
```

### 查看导航状态
```bash
ros2 topic echo /navigate_to_pose/_action/status
```

### 查看关节状态
```bash
ros2 topic echo /joint_states
```

### 查看TF树
```bash
ros2 run tf2_tools view_frames
evince frames.pdf
```

### 查看节点列表
```bash
ros2 node list
```

### 查看节点信息
```bash
ros2 node info /medicine_delivery_controller
```

## 常见问题

### Q: Gazebo启动失败
```bash
# 清理Gazebo缓存
rm -rf ~/.gazebo/
# 重新启动
ros2 launch nursing_home_sim nursing_home.launch.py
```

### Q: 机器人不移动
```bash
# 检查Nav2导航节点
ros2 node list | grep bt_navigator
# 检查速度话题
ros2 topic hz /cmd_vel
# 检查Nav2状态
ros2 topic echo /navigate_to_pose/_action/status
```

### Q: 找不到包
```bash
# 重新编译
cd ~/ros2_ws
colcon build --packages-select nursing_home_sim
source install/setup.bash
```

### Q: 权限错误
```bash
# 设置脚本权限
chmod +x ~/ros2_ws/src/nursing_home_sim/scripts/*.py
```

### Q: Launch文件错误
```bash
# 确保使用Python launch文件
ls ~/ros2_ws/src/nursing_home_sim/launch/*.py
# 重新安装
cd ~/ros2_ws
colcon build --packages-select nursing_home_sim --symlink-install
source install/setup.bash
```

## 测试流程

### 运行测试脚本
```bash
# 送药测试
ros2 run nursing_home_sim test_delivery.py

# 机械臂测试
ros2 run nursing_home_sim test_arms.py
```

### 手动测试步骤
1. 启动仿真系统
2. 发送任务：`ros2 topic pub /medicine_delivery_task std_msgs/msg/String "data: '药品,101'" --once`
3. 观察机器人执行以下步骤：
   - 移动到药品架
   - 抓取药品
   - 移动到房间门口
   - 开门
   - 进入房间
   - 放置药品到床头柜
   - 返回前台

## RViz2可视化

```bash
# 启动RViz2
ros2 run rviz2 rviz2

# 添加以下显示项：
# - RobotModel (robot_description)
# - Map (/map)
# - Path (/plan)
# - LaserScan (/scan)
# - TF
```

## 性能监控

### 查看CPU使用
```bash
htop
```

### 查看话题带宽
```bash
ros2 topic bw /cmd_vel
ros2 topic bw /odom
```

### 查看话题频率
```bash
ros2 topic hz /cmd_vel
ros2 topic hz /scan
```

### 查看节点计算图
```bash
rqt_graph
```

## 录制和回放

### 录制
```bash
ros2 bag record -a -o medicine_delivery_test
```

### 回放
```bash
ros2 bag play medicine_delivery_test
```

### 查看bag信息
```bash
ros2 bag info medicine_delivery_test
```

## 扩展开发

### 添加新房间
1. 编辑 `worlds/nursing_home.world` 添加房间模型
2. 在 `medicine_delivery_controller.py` 中添加坐标
3. 更新地图文件

### 修改机器人模型
1. 编辑 `urdf/dual_arm_mobile_robot.urdf`
2. 重新启动仿真

### 调整导航参数
1. 编辑 `config/nav2_params.yaml`
2. 调整速度、加速度等参数
3. 重新启动导航

## 关闭系统

```bash
# 按 Ctrl+C 或者
killall -9 gazebo gzserver gzclient
```

## 日志位置

```bash
# ROS2日志
~/.ros/log/

# Gazebo日志
~/.gazebo/
```

## ROS2常用命令对比

| ROS1 | ROS2 |
|------|------|
| `rostopic list` | `ros2 topic list` |
| `rostopic echo /topic` | `ros2 topic echo /topic` |
| `rosnode list` | `ros2 node list` |
| `roslaunch pkg file.launch` | `ros2 launch pkg file.launch.py` |
| `rosrun pkg node` | `ros2 run pkg node` |
| `rosparam list` | `ros2 param list` |
| `rosbag` | `ros2 bag` |

## Nav2特定命令

### 发送导航目标（命令行）
```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}"
```

### 查看Nav2状态
```bash
# 查看lifecycle节点状态
ros2 lifecycle list

# 查看地图
ros2 topic echo /map --once
```

## 键盘控制说明

使用 `keyboard_control.py` 时的按键：
- `w` - 前进
- `s` - 后退
- `a` - 左转
- `d` - 右转
- `q` - 停止
- `Ctrl+C` - 退出

## 故障排查清单

1. ✅ ROS2环境已source
2. ✅ 工作空间已编译
3. ✅ Gazebo正常启动
4. ✅ 所有节点运行中
5. ✅ TF树完整
6. ✅ 地图已加载
7. ✅ Nav2正常工作
