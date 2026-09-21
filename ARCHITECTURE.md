# 养老院送药机器人系统架构

## 系统概述

本项目实现了一个完整的养老院送药机器人仿真系统，包括环境建模、机器人控制、自主导航和任务执行等模块。

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户交互层                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ ROS话题命令  │  │  键盘控制    │  │   RViz可视化  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       控制层 (ROS节点)                            │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  medicine_delivery_controller.py (主控制器)            │     │
│  │  - 任务调度与状态机                                     │     │
│  │  - 导航目标管理                                         │     │
│  │  - 机械臂动作协调                                       │     │
│  └────────────────────────────────────────────────────────┘     │
│                              │                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐      │
│  │door_controller│  │elevator_controller│  │arm_controller│      │
│  │    .py        │  │      .py          │  │     .py      │      │
│  └───────────────┘  └───────────────┘  └───────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    导航与运动规划层                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │move_base │  │   AMCL   │  │map_server│  │   TF     │       │
│  │路径规划  │  │  定位    │  │  地图    │  │坐标变换  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   仿真层 (Gazebo)                                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                   物理仿真引擎                          │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │     │
│  │  │养老院环境│  │双臂机器人│  │传感器模拟│            │     │
│  │  │  世界    │  │  模型    │  │(里程计)  │            │     │
│  │  └──────────┘  └──────────┘  └──────────┘            │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## 核心模块说明

### 1. 主控制器 (medicine_delivery_controller.py)

**功能**:
- 接收并解析送药任务
- 管理任务执行流程
- 协调各子系统工作

**状态机**:
```
待命 → 前往药架 → 抓取药品 → 前往房间 → 开门 → 进入 → 放置药品 → 返回 → 待命
```

**关键话题**:
- 订阅: `/medicine_delivery_task` (String)
- 发布: `/cmd_vel` (Twist), `/door_control` (String), `/elevator_control` (String)
- 关节控制: `/dual_arm_robot/*/command` (Float64)

### 2. 导航系统

**move_base**: 全局和局部路径规划
- 输入: 目标位置 (MoveBaseGoal)
- 输出: 速度命令到 `/cmd_vel`
- 使用DWA局部规划器避障

**AMCL**: 自适应蒙特卡洛定位
- 粒子滤波器定位
- 基于里程计和地图

**costmap**: 代价地图
- global_costmap: 静态地图
- local_costmap: 动态障碍物

### 3. 机器人模型 (URDF)

**组成部分**:
```
base_link (底盘)
├── left_front_wheel
├── right_front_wheel
├── left_rear_wheel
├── right_rear_wheel
└── torso (躯干)
    ├── left_shoulder → left_upper_arm → left_elbow → left_forearm → left_wrist → left_gripper
    └── right_shoulder → right_upper_arm → right_elbow → right_forearm → right_wrist → right_gripper
```

**自由度**:
- 移动底盘: 2 DOF (x, θ)
- 左臂: 3 DOF (肩、肘、腕)
- 右臂: 3 DOF (肩、肘、腕)
- **总计: 8 DOF**

### 4. 环境模型 (World)

**建筑结构**:
- 前台区域: 2m × 6m
- 走廊: 20m × 2m
- 房间: 每个 5m × 4m
- 电梯井: 2m × 2m

**家具模型**:
- 前台桌
- 药品架
- 床
- 床头柜
- 门

### 5. 门控制系统 (door_controller.py)

**功能**:
- 监听门控制命令
- 通过Gazebo关节控制开关门
- 维护门状态

**工作原理**:
```python
open_door() → apply_joint_effort() → 施加力矩 → 门打开
```

### 6. 电梯控制系统 (elevator_controller.py)

**功能**:
- 电梯楼层切换
- 电梯位置更新
- 多楼层支持

**楼层配置**:
```python
floor_heights = {
    1: 0.1,   # 1楼高度
    2: 3.1    # 2楼高度
}
```

## 数据流

### 送药任务执行流程

```
1. 用户发送任务
   rostopic pub /medicine_delivery_task "药品名,房间号"
   ↓
2. 主控制器接收
   task_callback() 解析任务
   ↓
3. 导航到药架
   move_to_location('medicine_shelf')
   → move_base发送目标
   → 机器人移动
   ↓
4. 抓取药品
   pick_medicine()
   → 发布关节命令
   → 机械臂运动
   ↓
5. 导航到房间
   move_to_location('room_XXX_door')
   ↓
6. 开门
   open_door()
   → 发布到 /door_control
   → door_controller执行
   ↓
7. 进入房间
   move_to_location('room_XXX')
   ↓
8. 移动到床头柜
   move_to_nightstand()
   ↓
9. 放置药品
   place_medicine()
   → 机械臂动作序列
   ↓
10. 返回前台
    move_to_location('reception')
```

## 坐标系统

```
map (世界坐标系)
├── odom (里程计坐标系)
│   └── base_link (机器人底盘)
│       ├── left_front_wheel
│       ├── right_front_wheel
│       ├── left_rear_wheel
│       ├── right_rear_wheel
│       └── torso
│           ├── left_arm_links...
│           └── right_arm_links...
```

## 配置参数

### 导航参数

**速度限制**:
```yaml
max_vel_x: 0.45 m/s      # 最大线速度
min_vel_x: 0.1 m/s       # 最小线速度
max_vel_theta: 1.0 rad/s # 最大角速度
```

**代价地图**:
```yaml
obstacle_range: 2.5 m     # 障碍物检测范围
inflation_radius: 0.55 m  # 膨胀半径
```

### 机器人参数

**物理属性**:
```
底盘质量: 20 kg
单臂质量: ~3 kg
总质量: ~26 kg
```

**机械臂范围**:
```
肩关节: -1.57 ~ 1.57 rad
肘关节: 0 ~ 2.5 rad
腕关节: -1.57 ~ 1.57 rad
```

## 扩展点

### 1. 添加感知系统
```python
# 可以添加摄像头和激光雷达
- sensor_msgs/Image (相机)
- sensor_msgs/LaserScan (激光)
- sensor_msgs/PointCloud2 (深度相机)
```

### 2. 增强抓取控制
```python
# 添加力传感器和精确抓取
- 力反馈控制
- 视觉伺服
- MoveIt!运动规划
```

### 3. 多机器人协作
```python
# 命名空间隔离
- robot1/cmd_vel
- robot2/cmd_vel
```

### 4. 任务调度系统
```python
# 优先级队列
class TaskScheduler:
    - priority_queue
    - task_assignment()
    - load_balancing()
```

## 性能指标

**导航精度**: ±0.15m (xy_goal_tolerance)
**角度精度**: ±0.25rad (yaw_goal_tolerance)
**平均任务时间**: ~60秒/任务
**最大速度**: 0.45 m/s
**避障距离**: 0.55m

## 安全机制

1. **碰撞检测**: Gazebo物理引擎
2. **速度限制**: 配置文件约束
3. **超时保护**: 60秒导航超时
4. **状态监控**: 实时状态检查

## 调试工具

```bash
# 查看TF树
rosrun tf view_frames

# 监控话题
rostopic hz /cmd_vel
rostopic echo /odom

# 可视化
rosrun rviz rviz

# 计算图
rqt_graph
```

## 已知限制

1. 简化的抓取模型（无实际夹爪）
2. 门控制为模拟（实际机器人需要力控）
3. 无视觉感知系统
4. 单机器人系统
5. 固定的房间布局

## 未来改进方向

1. ✅ 集成MoveIt!用于机械臂规划
2. ✅ 添加RGB-D相机进行目标识别
3. ✅ 实现语音交互界面
4. ✅ 支持动态障碍物避障
5. ✅ 多机器人协同送药
6. ✅ 云端任务管理系统
7. ✅ 机器学习优化路径规划

## 参考资源

- ROS Navigation: http://wiki.ros.org/navigation
- Gazebo: http://gazebosim.org/
- MoveIt!: https://moveit.ros.org/
- URDF: http://wiki.ros.org/urdf
