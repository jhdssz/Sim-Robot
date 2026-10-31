# 起点后移 1 m 与本次碰撞拒绝诊断

按最新要求，先实施起点调整：机器人从 `(-1,0,yaw=0)` 改为 **`(-2,0,yaw=0)`**，沿其初始朝向的反方向后移 1 m。

同步修改了 `launch/nursing_home.launch.py` 中 Gazebo spawn x，以及 `nav2_params.yaml`、`nav2_narrow.yaml`、`nav2_narrow_raw.yaml` 中 AMCL initial_pose.x；避免物理机器人与定位初值相差 1 m。实验几何起点、备用路线和导航采集器的起点校验也已同步。障碍物中心仍为 `(1.4,-2.26,0.5)`，包含双臂的缝宽仍为 0.76 m，未修改地图、滤波规则、footprint 或导航目标。

这是起点缓解措施，**不是路径规划问题已经修复**，也不是已经命令当前运行中的机器人倒退。当前代理无法进入 WSL 操作 Gazebo，修改在重启仿真后生效。

## 重新启动

先在原终端 Ctrl+C，停止旧 Gazebo 和 Nav2，再执行：

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
colcon build --base-paths /mnt/d/Sim-Robot --packages-select nursing_home_sim --symlink-install
source install/setup.bash
ros2 launch nursing_home_sim nursing_home.launch.py \
  world:=/mnt/d/Sim-Robot/worlds/nursing_home.world navigation:=true task_controllers:=false
```

随后在 RViz 正常点击门口目标。不要在机器人实际尚未重启时，只把 RViz 的 2D Pose Estimate 改到新起点：那只是改变定位估计，不会移动 Gazebo 机器人。

## 日志实际证明了什么

用户提供的 495 行日志覆盖约 30.915 s 的摘录，出现：

- 每轮 DWB 419 条候选轨迹全部无效，133 条具体 critic 错误均为 `ObstacleFootprint/Trajectory Hits Obstacle`。
- 14 条 `Controller patience exceeded`，13 条清理 Costmap 请求。
- 3 次 Spin，均以 `Collision Ahead - Exiting Spin` 退出。
- 2 次 BackUp，均以 `Collision Ahead - Exiting DriveOnHeading` 退出。
- 最终 `Goal failed` / ActionServer abort；没有独立采集 Action 状态码。

因此已知的主要失败是**局部轨迹被碰撞检查拒绝**，随后清图、重规划与恢复反复触发。路径左右变化可以是这些重试的结果，不能等同于全局规划器完全找不到路径。控制/规划循环掉频也存在，但日志里的直接否决原因是碰撞。

你提出“转向时同时前进，离墙越来越近，最后没有转身空间”是合理候选原因；日志支持机器人当时已被 Costmap 判定没有安全动作。但仅凭日志不能证明靠近过程真实发生，也不能区分真实接触、残留障碍或定位偏差。

DWB 标准轨迹包含起始姿态；ObstacleFootprint 会将 polygon 边界离散到原始 Costmap 格子。如果当前边界已经覆盖 lethal=254 格子，不同速度候选也可能从起点一起失败，连原地 Spin 或 BackUp 也无法通过碰撞校验。原始 253 膨胀格与 254 致命格含义不同，不能只看 RViz 的彩色区域判断。[Jazzy 轨迹生成源码](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_dwb_controller/dwb_plugins/src/standard_traj_generator.cpp)、[Jazzy footprint critic 源码](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_dwb_controller/dwb_critics/src/obstacle_footprint.cpp)

此前改为 ObstacleFootprint 后，检查比原中心代价检查更贴近完整机械臂包络，可能暴露全局路径与局部可执行性不一致。当前不能把这归咎于滤波器，也未退回更弱碰撞检查。

## 滤波盲区是否会“变成墙”

当前滤波代码只将六个角度区域内、距离小于 0.22/0.34 m 的候选点改为 `inf`，不会凭空生成有限距离障碍点，超过阈值的距离不因所在扇区而删除。

但滤波不会恢复被机械臂或真实物体遮住的后方测距。若旧障碍格没有被新的有效射线清除，可以留下残影；也可能仍有未过滤的自身回波。它们都需要扫描和格子数据证实。Costmap 中真实桌柜、静态图错位或 TF/AMCL 偏差也会导致同样错误。

当前配置没有显式设置 `inf_is_valid`，Jazzy ObstacleLayer 默认值为 false（实际运行参数仍应查询确认）。这种情况下，过滤产生的 inf 不等于“前方直到量程上限都为空”，也不直接构成墙。[Jazzy ObstacleLayer 源码](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_costmap_2d/plugins/obstacle_layer.cpp)

本轮没有启用 `inf_is_valid=true` 来强行清出盲区：滤掉近处自身回波并不能证明机械臂后方没有真实物体，不能用一条假空闲射线代替未观测区域。

## 已提供的只读检查工具

新增 `scripts/audit_footprint_costmap.py`。机器人再次停住时，先不要清图或重启，在另一个已 source ROS/workspace 的 Ubuntu 终端运行：

```bash
python3 /mnt/d/Sim-Robot/scripts/audit_footprint_costmap.py \
  --output "$HOME/footprint-audit-$(date +%Y%m%d_%H%M%S)"
```

工具不发送运动/导航命令，不取消目标，不清图；保存三组时间接近的实际 `/local_costmap/costmap_raw` 与 `/local_costmap/published_footprint`，列出边界上的 254 致命格、255 未知格、253 膨胀格及越界情况，并将阻挡位置映射到静态 `/map` 对照。

- **当前边界有 254 格**：支持“起点已处于碰撞判定”的解释，检查这些格子究竟落在真实桌柜还是机器人附近残留点上。
- **静态图对应格也占据**：更应检查真实桌柜、地图配准和定位。
- **静态图自由、局部图致命**：更应检查实时/残留观测、未过滤自身回波和 TF；单凭此项还不能归因滤波。
- **当前边界无致命格**：不能排除未来预测姿态发生碰撞，也不能反证 earlier 日志发生时的状态。

边界 raster 为只读近似复核，角点 tie cell 可能与 DWB LineIterator 有差异，且不替代完整 419 条未来轨迹评分。工具严格限制 footprint/grid 时间差（默认 0.1 s）；拿不到对齐数据会报告不完整，不伪造结果。

要采集“边前进边旋转”的过程，可继续使用之前的被动记录器：

```bash
python3 /mnt/d/Sim-Robot/scripts/capture_nav_diagnostics.py \
  --output "$HOME/door-debug-$(date +%Y%m%d_%H%M%S)" --duration 180 --bag
```

看到 PASSIVE ready 后通过 RViz 发送一次门口目标。此脚本不会把你的目标换成固定实验点。

## 本轮完成与限制

起点、三份 AMCL 初值、实验起点检查已同步；离线几何验证新起点周围的完整旋转外接圆余量和静态地图区域；原有 13 项测试再次全部 PASS。新的只读审计工具通过语法和 free/lethal/inflated/unknown/off-grid 五类合成离线检查；这些不是仿真实测。尚未在 Ubuntu 运行审计器、重新构建、重启 Gazebo 或证明路径恢复。
