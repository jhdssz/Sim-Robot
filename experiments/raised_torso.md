# 躯干加高与双臂滤波移除（2026-10-19）

已将“拉长身体”实施为竖直加高躯干上部 **0.30 m**，保持底盘和激光雷达高度不变，左右双臂与相机安装点同步上移。

仅加高 0.20 m 时，home 姿态的最低手指仍位于 base_link z≈0.24～0.32 m，会跨过 z=0.27 m 的扫描平面。因此采用 0.30 m：最低手指提高到 z≈0.34 m，与扫描平面有约 **0.07 m** 高度间隔。

| 几何量（base_link 坐标） | 修改前 | 修改后 |
|---|---:|---:|
| 躯干上部 box 高度 | 0.48 m | 0.78 m |
| 躯干上部顶面 | 0.80 m | 1.10 m |
| 左右肩关节安装高度 | 0.70 m | 1.00 m |
| 相机安装高度 | 0.85 m | 1.15 m |
| 激光扫描平面高度 | 0.27 m | 0.27 m |
| home 双臂最低碰撞体 | 0.04 m | 0.34 m |

下方扫描舱、四个支撑柱、雷达支座和底盘几何保持原样；不是把整段躯干悬空上移。URDF、正常 Gazebo SDF、实验 SDF 的 visual/collision 与安装位置一致。躯干质量保持 10 kg，按新组合 box 的均匀密度分布重新计算质心和惯量，URDF/SDF 同步。平面 footprint 不变，仍包含双臂宽度。

## 滤波变化

已移除原双臂区域：

- `[-98°, -82°]，r<0.34 m`
- `[82°, 98°]，r<0.34 m`

这两个方向不再按旧双臂规则删除近距离环境返回。

保留四个仍穿过扫描平面的支撑柱区域，距离均严格小于 0.22 m 才过滤：

`[-142°,-129°]、[-51°,-39°]、[39°,51°]、[129°,142°]`。

原始 `/scan` 与输出 `/scan_filtered` 两条链路保留。比较器的统计长度已从硬编码6改为当前区域数4。原六区合成fixture现应过滤26点、保留原双臂区域22点；旧版48点/六区测试数据不能作为本版预期。

## 验证结果

- 更新后的滤波单元测试 **14/14 PASS**，新增原双臂区域近距离返回保持测试。
- 新增模型几何回归 **6/6 PASS**：正常/实验模型的双臂碰撞与可视几何、URDF/SDF安装点、扫描舱和支撑柱、质心惯量，以及包含关节限位的保守机械臂长度界。
- home 几何间隔约7 cm；另用链段长度、碰撞体包围球和最大手指行程的三角不等式界，验证理想关节限位内的保守最低高度也高于扫描平面。此结果仍不替代 Gazebo 动力学、关节约束误差与实际 GPU lidar 渲染验证。
- Git diff --check 通过，仅有已有行尾转换提示；保留本轮修改前的源文件备份，未 Commit/Push。
- 已尝试 WSL 构建，但在入口返回 `Wsl/E_ACCESSDENIED`，未进入 colcon。当前没有实际 Gazebo、Nav2 或扫描消息实测结果。

## 修改文件

- `urdf/dual_arm_mobile_robot.urdf`
- `models/dual_arm_robot/model.sdf`
- `models/dual_arm_robot/experiment.sdf`
- `scripts/scan_self_filter.py`
- `scripts/compare_scan_filter.py`
- `scripts/validate_robot.py`
- `tests/test_scan_self_filter.py`
- `tests/test_model_scan_clearance.py`（新增）
- `scripts/run_repro_experiment.sh`、`CMakeLists.txt`：加入新的离线模型测试。

## 重建和运行

先停止旧仿真，在 Ubuntu 运行：

```bash
source /opt/ros/jazzy/setup.bash
cd /mnt/d/Sim-Robot
python3 tests/test_scan_self_filter.py -v
python3 tests/test_model_scan_clearance.py -v
cd ~/ros2_ws
colcon build --base-paths /mnt/d/Sim-Robot --packages-select nursing_home_sim --symlink-install
source install/setup.bash
ros2 launch nursing_home_sim nursing_home.launch.py \
  world:=/mnt/d/Sim-Robot/worlds/nursing_home.world navigation:=false task_controllers:=false
```

先在固定双臂home姿态下检查真实原始扫描：

```bash
ros2 topic echo /scan sensor_msgs/msg/LaserScan --once
python3 /mnt/d/Sim-Robot/scripts/compare_scan_filter.py \
  --pairs 20 --timeout 90 --no-front-fixture \
  --output "$HOME/raised-torso-scan-$(date +%Y%m%d_%H%M%S)" --ros-args -p use_sim_time:=true
```

RViz 同时显示 `/scan` 和 `/scan_filtered`：原双臂左右方向应不再出现对应自身近回波；同角度真实近障碍应原样保留。四个支撑柱的短距离回波仍由剩余四区处理。若实际仍有双臂回波，需要先核对加载的模型路径、关节姿态及安装资源是否更新，不能扩大滤波盲区来掩盖。

确认扫描后，再使用 `navigation:=true` 启动导航并重复窄通道实验。起点仍为 `(-2,0)`，障碍物中心仍为 `(1.4,-2.26,0.5)`、净空0.76 m，本轮未调整它们。
