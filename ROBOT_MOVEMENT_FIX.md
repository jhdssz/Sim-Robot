# 机器人运动链路修复报告

## 修改概述

修复了机器人完全无法移动的问题，建立了完整的 ROS2 Jazzy ↔ Gazebo Harmonic 通信链路。

---

## 修改的文件

### 1. `urdf/dual_arm_mobile_robot.urdf`
**修改内容：**
- 添加 `odom` link（第4-5行）- DiffDrive 插件需要的里程计参考坐标系
- 添加 `laser_link` 和 LiDAR 传感器（第528-555行）
- 改进 DiffDrive 插件配置（第559-577行）
- 添加 LiDAR 传感器 Gazebo 配置（第593-619行）

### 2. `launch/nursing_home.launch.py`
**修改内容：**
- 添加 `cmd_vel_bridge` 节点（第72-77行）
- 添加 `odom_bridge` 节点（第79-84行）
- 添加 `scan_bridge` 节点（第86-91行）
- 更新 LaunchDescription 包含所有 bridge 节点（第131-142行）

### 3. 新增测试脚本
- `test_robot_movement.sh` - 完整的运动链路验证脚本

---

## 第一步：底盘运动配置

### DiffDrive 插件配置详情

```xml
<plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">
  <left_joint>left_front_wheel_joint</left_joint>
  <right_joint>right_front_wheel_joint</right_joint>
  <wheel_separation>0.5</wheel_separation>
  <wheel_radius>0.1</wheel_radius>
  <wheel_diameter>0.2</wheel_diameter>
  <max_linear_acceleration>1.0</max_linear_acceleration>
  <max_angular_acceleration>2.0</max_angular_acceleration>
  <max_linear_velocity>0.5</max_linear_velocity>
  <max_angular_velocity>1.0</max_angular_velocity>
  <topic>cmd_vel</topic>
  <odom_topic>odom</odom_topic>
  <frame_id>odom</frame_id>
  <child_frame_id>base_link</child_frame_id>
  <odom_publish_frequency>50</odom_publish_frequency>
</plugin>
```

**关键参数：**
- **左轮 joint**: `left_front_wheel_joint`
- **右轮 joint**: `right_front_wheel_joint`
- **轮间距**: 0.5m
- **轮半径**: 0.1m
- **最大线速度**: 0.5 m/s
- **最大角速度**: 1.0 rad/s
- **Gazebo topic**: `cmd_vel`, `odom`

---

## 第二步：ros_gz_bridge 配置

### /cmd_vel Bridge (ROS → Gazebo)

```python
cmd_vel_bridge = Node(
    package='ros_gz_bridge',
    executable='parameter_bridge',
    arguments=['/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist'],
    output='screen'
)
```

**方向**: ROS2 → Gazebo  
**ROS2 类型**: `geometry_msgs/msg/Twist`  
**Gazebo 类型**: `gz.msgs.Twist`

### /odom Bridge (Gazebo → ROS)

```python
odom_bridge = Node(
    package='ros_gz_bridge',
    executable='parameter_bridge',
    arguments=['/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry'],
    output='screen'
)
```

**方向**: Gazebo → ROS2  
**ROS2 类型**: `nav_msgs/msg/Odometry`  
**Gazebo 类型**: `gz.msgs.Odometry`

---

## 第三步：LiDAR 配置

### LiDAR Link 位置
- **父坐标系**: `base_link`
- **安装位置**: x=0.25m, y=0, z=0.15m（底盘前方）
- **Link 名称**: `laser_link`

### LiDAR 传感器配置

```xml
<sensor name="laser_sensor" type="gpu_lidar">
  <topic>scan</topic>
  <update_rate>10</update_rate>
  <lidar>
    <scan>
      <horizontal>
        <samples>360</samples>
        <resolution>1</resolution>
        <min_angle>-3.14159</min_angle>
        <max_angle>3.14159</max_angle>
      </horizontal>
    </scan>
    <range>
      <min>0.12</min>
      <max>10.0</max>
      <resolution>0.01</resolution>
    </range>
    <noise>
      <type>gaussian</type>
      <mean>0.0</mean>
      <stddev>0.01</stddev>
    </noise>
  </lidar>
  <always_on>1</always_on>
  <visualize>true</visualize>
</sensor>
```

**关键参数：**
- **扫描角度**: 360度 (-π 到 π)
- **采样点数**: 360
- **更新频率**: 10 Hz
- **最小距离**: 0.12m
- **最大距离**: 10.0m
- **噪声**: 高斯噪声，标准差 0.01

### /scan Bridge (Gazebo → ROS)

```python
scan_bridge = Node(
    package='ros_gz_bridge',
    executable='parameter_bridge',
    arguments=['/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan'],
    output='screen'
)
```

**方向**: Gazebo → ROS2  
**ROS2 类型**: `sensor_msgs/msg/LaserScan`  
**Gazebo 类型**: `gz.msgs.LaserScan`

---

## 验证命令

### 1. 重新编译
```bash
cd /mnt/d/Sim-Robot
colcon build --packages-select nursing_home_sim
source install/setup.bash
```

### 2. 启动仿真
```bash
ros2 launch nursing_home_sim nursing_home.launch.py
```

### 3. 检查 ROS2 Topics
```bash
ros2 topic list | grep -E "cmd_vel|scan|odom"
```
**预期输出：**
```
/cmd_vel
/cmd_vel_nav
/cmd_vel_smoothed
/odom
/scan
```

### 4. 检查 Gazebo Topics
```bash
gz topic -l | grep -E "cmd_vel|scan|odom"
```
**预期输出：**
```
/cmd_vel
/odom
/scan
```

### 5. 检查 /cmd_vel 详情
```bash
ros2 topic info /cmd_vel -v
```
**预期输出：**
```
Type: geometry_msgs/msg/Twist
Publisher count: X
Subscription count: Y (至少1个 - ros_gz_bridge)
```

### 6. 检查 Gazebo /cmd_vel
```bash
gz topic -i -t /cmd_vel
```
**预期输出：** 显示 `gz.msgs.Twist` 类型和订阅者

### 7. 测试前进运动
```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}"
```
**预期结果：** 机器人在 Gazebo 中向前移动

### 8. 测试旋转运动
```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.5}}"
```
**预期结果：** 机器人在 Gazebo 中原地旋转

### 9. 验证 /odom 数据
```bash
ros2 topic echo /odom --once
```
**预期输出：** 显示 `nav_msgs/msg/Odometry` 消息，包含位置和速度数据

### 10. 验证 /scan 数据
```bash
ros2 topic echo /scan --once
```
**预期输出：** 显示 `sensor_msgs/msg/LaserScan` 消息，包含 360 个距离测量值

### 11. 使用测试脚本
```bash
bash test_robot_movement.sh
```
**功能：** 自动执行上述所有检查和测试

---

## 问题排查

### 如果机器人仍然不移动：

1. **检查 bridge 是否运行：**
   ```bash
   ros2 node list | grep bridge
   ```

2. **检查 cmd_vel 是否真的进入 Gazebo：**
   ```bash
   gz topic -e -t /cmd_vel
   ```
   发送命令后应该看到数据

3. **检查轮子 joint 是否可转动：**
   ```bash
   gz model -m dual_arm_robot -j
   ```

4. **查看 Gazebo 日志：**
   检查终端输出是否有 DiffDrive 插件错误

### 如果 /scan 没有数据：

1. **检查 LiDAR 传感器是否加载：**
   ```bash
   gz topic -l | grep scan
   ```

2. **在 Gazebo 中可视化激光：**
   传感器配置中已设置 `<visualize>true</visualize>`

3. **检查 scan_bridge 是否运行：**
   ```bash
   ros2 node info /parameter_bridge
   ```

---

## 不会影响的部分

✅ Gazebo Harmonic world  
✅ 场景材质和光照  
✅ ROS2 Jazzy 环境  
✅ Nav2 配置  
✅ 当前机器人 spawn 流程  
✅ 双臂、夹爪结构（暂时保留但未启用）

---

## 下一步（在验证通过后）

只有在以下四项全部通过后才进行：

1. ✅ /cmd_vel 能让机器人前进
2. ✅ /cmd_vel 能让机器人旋转
3. ✅ /odom 有持续变化的数据
4. ✅ /scan 有有效 LaserScan 数据

**才可以考虑：**
- 优化机器人外观
- 添加摄像头
- 配置 MoveIt
- 手臂控制优化
