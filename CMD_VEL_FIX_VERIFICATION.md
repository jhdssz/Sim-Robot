# /cmd_vel 单向 Bridge 修复验证

## 问题诊断

**症状：** 机器人自动移动到地图边界 (x=14.6, y=9.625)

**根本原因：** `/cmd_vel` bridge 配置为双向（`@` 表示双向），可能导致：
1. 速度命令循环
2. 某个节点持续发布速度命令
3. Gazebo -> ROS 方向不必要的数据流

## 应用的修复

**文件：** `launch/nursing_home.launch.py`

**修改内容：**
```python
# 之前（双向）
arguments=['/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist'],

# 修复后（单向：ROS -> Gazebo）
arguments=['/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist'],
```

**说明：**
- `@` = 双向 bridge
- `]` = 单向 bridge（只从 ROS 到 Gazebo）
- 控制命令只需要 ROS -> Gazebo 方向
- 不需要 Gazebo -> ROS 方向（DiffDrive 直接发布 `/odom`）

---

## 手动验证步骤

### 步骤 1: 重新构建

```bash
cd /mnt/d/Sim-Robot
source /opt/ros/jazzy/setup.bash
colcon build --packages-select nursing_home_sim
source install/setup.bash
```

### 步骤 2: 启动仿真

```bash
ros2 launch nursing_home_sim nursing_home.launch.py
```

**检查 launch 日志：**
应该只看到：
```
[INFO] [ros_gz_bridge]: Creating ROS->GZ Bridge: [/cmd_vel ...]
```

不应该看到：
```
[INFO] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/cmd_vel ...]
```

### 步骤 3: 记录初始位置（新终端）

```bash
source /mnt/d/Sim-Robot/install/setup.bash
gz model -m dual_arm_robot --pose
```

**记录输出：**
```
Pose:
  x: 0.5
  y: 0.0
  z: 0.2
  roll: ...
  pitch: ...
  yaw: ...
```

**记录初始坐标：**
- 初始 X: _______
- 初始 Y: _______

### 步骤 4: 等待 10 秒

不发送任何命令，等待 10 秒。

### 步骤 5: 再次查询位置

```bash
gz model -m dual_arm_robot --pose
```

**记录最终坐标：**
- 最终 X: _______
- 最终 Y: _______

**计算位置变化：**
- ΔX = |最终X - 初始X| = _______
- ΔY = |最终Y - 初始Y| = _______

**期望结果：**
- ✅ ΔX < 0.01m
- ✅ ΔY < 0.01m
- ✅ 机器人位置基本没有变化

**失败情况：**
- ❌ ΔX 或 ΔY > 0.1m
- ❌ 机器人持续移动

### 步骤 6: 监听 /cmd_vel 话题

```bash
ros2 topic echo /cmd_vel
```

等待 5-10 秒，观察输出。

**期望结果：**
- ✅ 没有任何输出（话题无数据）
- ✅ 或者只有偶尔的零速度命令

**失败情况：**
- ❌ 持续看到 `linear.x: 0.2` 或其他非零值
- ❌ 高频率的速度命令

按 `Ctrl+C` 退出。

### 步骤 7: 检查话题信息

```bash
ros2 topic info /cmd_vel -v
```

**期望输出：**
```
Type: geometry_msgs/msg/Twist

Publishers:
  * /controller_server (可选)
  * /velocity_smoother (可选)
  * 其他 Nav2 节点

Subscribers:
  * /ros_gz_bridge (必须存在)
  * 其他节点
```

**关键检查：**
- ✅ `/ros_gz_bridge` 出现在 **Subscribers** 列表中
- ✅ `/ros_gz_bridge` **不应该** 出现在 **Publishers** 列表中
- ✅ 如果没有导航任务，Publishers 应该很少或没有

**失败情况：**
- ❌ `/ros_gz_bridge` 同时是 Publisher 和 Subscriber
- ❌ 看到不明来源的持续 Publisher

### 步骤 8: 测试手动控制（可选）

发送一个测试命令：

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.1}, angular: {z: 0.0}}"
```

等待 1-2 秒，机器人应该短暂移动然后停止。

再次查询位置：
```bash
gz model -m dual_arm_robot --pose
```

位置应该有小幅变化（约 0.1-0.2m）。

---

## 自动化验证脚本

### Linux/WSL:
```bash
cd /mnt/d/Sim-Robot
chmod +x test_cmd_vel_fix.sh
./test_cmd_vel_fix.sh
```

### Windows PowerShell:
```powershell
cd D:\Sim-Robot
.\test_cmd_vel_fix.ps1
```

---

## 成功标准

### ✅ 修复成功的指标：

1. **Launch 日志：**
   - 只看到 `Creating ROS->GZ Bridge: /cmd_vel`
   - 没有 `Creating GZ->ROS Bridge: /cmd_vel`

2. **机器人位置：**
   - 10 秒内位置变化 < 0.01m
   - 机器人保持在初始位置（x≈0.5, y≈0）

3. **/cmd_vel 话题：**
   - 没有持续的非零速度命令
   - 只在手动控制或导航时有数据

4. **Topic Info：**
   - ros_gz_bridge 只是 Subscriber（ROS -> GZ）
   - 不是 Publisher（GZ -> ROS）

### ❌ 仍有问题的指标：

1. 机器人继续自动移动
2. /cmd_vel 持续有非零速度
3. ros_gz_bridge 仍然作为 Publisher
4. Launch 日志显示双向 bridge

---

## 未修改的部分

根据要求，以下部分保持不变：
- ✅ DiffDrive 插件配置
- ✅ `/odom` bridge（Gazebo -> ROS，正确）
- ✅ `/scan` bridge（Gazebo -> ROS，正确）
- ✅ Nav2 配置
- ✅ World 场景
- ✅ SDF 模型

---

## 额外排查（如果问题仍然存在）

如果修复后机器人仍然移动，需要检查：

### 1. 检查所有 /cmd_vel Publishers
```bash
ros2 topic info /cmd_vel -v
```
查看哪个节点在发布命令。

### 2. 检查 velocity_smoother
```bash
ros2 topic echo /cmd_vel_smoothed
```
velocity_smoother 可能在输出命令。

### 3. 检查 Nav2 navigation stack
```bash
ros2 node list | grep -E "controller|planner|bt_navigator"
```
确认导航节点状态。

### 4. 检查 Gazebo 内部话题
```bash
gz topic -l | grep cmd_vel
gz topic -e -t /cmd_vel
```
确认 Gazebo 接收的命令。

### 5. 查看完整话题流
```bash
ros2 run rqt_graph rqt_graph
```
可视化所有节点和话题连接。

---

## 联系信息

如果验证失败，请提供：
1. Launch 日志（前 50 行）
2. `ros2 topic info /cmd_vel -v` 完整输出
3. 两次 `gz model --pose` 的完整输出
4. 机器人是否在 Gazebo GUI 中可见移动
