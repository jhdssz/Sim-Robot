> 2026-10-19 更新：躯干已加高30 cm，原双臂两区滤波已移除，当前保留四个支撑柱滤波区域。详见 [模型与滤波更新](raised_torso.md)。下文的六区测试结论属于旧模型。

> 最新起点调整：机器人及 AMCL 初始位置已从 (-1,0) 后移到 (-2,0)。碰撞日志结论和只读检查命令见 [起点与碰撞诊断](collision_diagnosis.md)。下文中的旧起点路线仅为上一版记录。

# 间隔按包含双机械臂的宽度调整

本轮按明确要求，将净空基准改为 **机器人当前 home 姿态的全部碰撞体投影宽度，包含两条机械臂**。不再用底盘本体或轮胎宽度代替。

读取实际 `models/dual_arm_robot/model.sdf`，解析各 link/joint 的 home 位姿并合成 primitive collision 包络：y_min=-0.38 m、y_max=+0.38 m，完整宽度为 **0.76 m**。作为区分：底盘本体宽 0.40 m、轮胎外宽约 0.550019 m；它们都不是本轮设置值。若机械臂关节离开 home，须重新计算动态包络。

## 实际修改

两个世界 `worlds/nursing_home.world` 和 `worlds/nursing_home_narrow.world` 的现有障碍物，都从 `(1.4,-1.9,0.5)` 移到 **`(1.4,-2.26,0.5)` m**，尺寸保持 **0.8×1.0×1.0 m**，仍为同一个可见、可碰撞的静态橙红色方块。

- 柜子南侧边缘 y=-1.0。
- 方块北侧边缘 y=-2.26+0.5=-1.76。
- 实际净空为 `-1.0-(-1.76)=0.76 m`。
- 狭缝范围 x=[1,1.8]、y=[-1.76,-1.0]。
- 这次相对上版再向外移了 0.36 m，净空从 0.40 m 增至 0.76 m。
- 最近参考物体是桌前的柜子 medicine_shelf；桌子本体南边缘为 -0.5，与方块之间的 y 净空是 1.26 m，不能把“桌子”和“柜子”的边缘混用。

`experiment_geometry.py` 同步输出完整双臂宽度、缝宽与其差值、缝宽与导航 footprint 正向宽度的差值，以及任意转角投影是否都被阻挡。备用几何路线下沿改为 y=-3.6，导航采集器从几何结果读取新的 ROI，未硬编码旧位置。

## “正正好过不去”的准确含义

物理 home 宽度=缝宽=0.76 m，正向经过时横向余量为零；这不是安全通道。Nav2 footprint 的正向宽度为 0.80 m，比缝宽多 0.04 m，完整 footprint 的正向通过应被拒绝。

但该 footprint 的最小旋转投影为 0.64 m，小于 0.76 m，因此**不能仅用宽度比较证明所有旋转、斜行或绕角姿态都无法通过**。新的 geometry.json 明确记录 `all_yaw_projection_blocked=false`，不把正向不满足碰撞条件扩写成任意姿态不可通行。精确穿越可行性仍需按完整轨迹、碰撞体、差速运动约束与离散 Costmap 验证。

默认和独立实验配置已使用 ObstacleFootprint。Costmap resolution=0.05 m，0.76 m 约为 15.2 个格子；0.04 m 的正向差额小于一格，因此必须观察实际栅格化边缘与完整 footprint 检查结果，不能把格数四舍五入当成通过证明。Inflation 参数本轮未改变。

## 为什么加宽后仍不保证走右边

Nav2 在两侧都可行时会综合路径长度、障碍代价和控制可行性选择路线。把中间缝隙加宽，只改变缝隙几何，不会给“右侧”自动增加偏好。若门口目标在另一侧方向，左绕仍可能更便宜。

本轮只调整物体间隔，不擅自移动你通过 RViz 点击的门口目标，不新增左侧挡墙，也不把实验脚本预设目标发送给机器人。若要强制验证右侧路线，需要把右侧中间点作为独立的受约束实验；这应与“只给门口目标、由 Nav2 自主选择绕行”的实验分别报告。已有被动诊断脚本仍可采集 RViz 点击导航，不会发送或取消 goal。

## 使用与验证

先退出旧 Gazebo/launch，重新构建并 source 当前 workspace，再启动：

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
colcon build --base-paths /mnt/d/Sim-Robot --packages-select nursing_home_sim --symlink-install
source install/setup.bash
ros2 launch nursing_home_sim nursing_home.launch.py \
  world:=/mnt/d/Sim-Robot/worlds/nursing_home.world navigation:=true task_controllers:=false
```

Gazebo 中选中 `narrow_gap_obstacle`，应看到中心 Position `(1.4,-2.26,0.5)`；仅修改磁盘文件不会更新正在运行的仿真。

本轮离线：两个 XML 有且仅有一个该物体，visual/collision 尺寸一致、其余世界实体不变；完整模型宽度与净空计算一致；备用外接圆路径有正余量；Python 语法通过；原 13 项测试全部 PASS。地图与导航参数本轮均未修改。

当前没有实际 Gazebo/Nav2 实测结果，也未证明右侧路线已被选中。此前 WSL 返回 E_ACCESSDENIED，仍需在用户 Ubuntu 中完成实测；本轮不会把离线几何数据写成运行时结果。前几版的 0.40 m 间隔及物体 y=-1.9 坐标已过时，以本说明和本轮 geometry.json 为准。
