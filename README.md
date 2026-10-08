# 养老院送药机器人仿真系统 (ROS2)
## 2026-10-08 暂时移除101、102房间门

101、102入口现保持常开。本轮完整移除world中的 `door_101`、`door_102`：每扇门的 `frame` 和 `door_panel` 两个link、两组visual/collision、门板惯性及 `door_hinge` 铰链全部删除。原frame是实心长方体，存在和门板类似的第二层视觉/碰撞几何，随模型一同移除。未发现额外独立重复门模型或外部Gazebo门插件引用。

`room_101`、`room_102`、建筑墙壁、家具和原门洞均保留。原门洞位于世界 x=7.55–9.50 m、y=+2.50 m（101）和−2.50 m（102）；静态检查确认这两处通道没有残留门体、视觉固体或高于地面的碰撞固体。房间及其他world节点与本轮开始快照一致，未改墙壁来扩大入口。

### 修改文件

| 文件 | 修改内容 |
| --- | --- |
| `worlds/nursing_home.world` | 删除两个完整门模型，共4个link、4个visual、4个collision和2个铰链；其他world结构不变。 |
| `maps/nursing_home_map.pgm` | 两个实际门洞的栅格局部修正，每个92像素，共184像素由占用值0改为自由值254。其他像素及PGM头不变。 |
| `launch/nursing_home.launch.py` | 移除door_controller的Node和启动列表项，task_controllers=true时也不再启动它；机器人出生点及其他节点参数不变。 |
| `scripts/medicine_delivery_controller.py` | 送药演示跳过开门命令和3秒等待，直接进入房间；原open_door方法和门控制源代码保留。 |
| `README.md` | 更新常开入口说明、门功能状态和验收流程。 |

`scripts/door_controller.py` 和安装配置保留以便后续恢复。其原有ROS命令话题定义、送药控制器的发布器/开门方法仅为保留代码，当前启动和送药流程不再执行门控制；没有在运行world中保留对已删除Gazebo门实体的插件/关节引用。

### 地图为什么需要局部修改

原地图横墙从 x≈8.40 m开始，占据了world实际门洞的一部分；单独删除Gazebo门模型后，Nav2静态层仍会把部分敞开通道当成墙。本轮仅在 x=7.55–9.50 m、y=2.40–2.60 m 和 y=−2.60–−2.40 m 两块区域清除误标像素。

地图仍为600×400、0.05 m/格；`maps/nursing_home_map.yaml`（包括origin、分辨率及阈值）字节未变。基础地图两处门洞现为自由栅格；其他地图区域、房间墙壁及导航膨胀参数均未调整。本次仅核对入口局部，未声称完整静态地图与全场景完全一致。

### 实际验证结果

- Windows下world XML解析通过；SDF根节点/version、world/model结构和局部几何检查通过。两个门实体及其panel/hinge不存在；其他world XML节点逐项比较一致。
- 对保留的全部world box visual/collision计算世界包围盒，两处原门洞穿越区域均无地面以上的固体遮挡；这是静态几何检查，不能替代运行渲染和碰撞验证。
- 原/新PGM逐像素比较通过：仅184个入口像素改变，均由0→254；两处门洞栅格通过map YAML的free_thresh判断；地图尺寸、头部及其他像素不变。
- launch和送药脚本AST/语法检查通过；不再启动door_controller，execute_delivery_task不再调用open_door。
- `python scripts/validate_robot.py` 在Windows运行通过，四轮DiffDrive、雷达、扫描过滤、出生点和AMCL检查仍通过。
- 已尝试WSL命令 `gz sdf -k ... && colcon build ...`，WSL直接返回 `Wsl/E_ACCESSDENIED`。**官方gz sdf校验、colcon构建、Gazebo启动及RViz实际显示均未实测/未完成，不能记为通过。** 本机Windows也没有gz。
- 文件哈希检查确认只改变本节5个文件；机器人SDF/URDF、四轮驱动、扫描过滤、Nav2参数、AMCL、DWB、出生点和其他场景模型未改。未提交Git，未push。

### 重新编译、重启和验收操作

需要重新执行colcon构建/安装，并重启当前Gazebo和Nav2，让安装目录中的world/地图/脚本生效。即使某些资源由symlink-install链接，也不能让已经加载的旧world自动移除门。先在原启动终端按Ctrl+C停止本项目Gazebo/Nav2，关闭原RViz，再运行下面命令；不要在旧实例还运行时另起第二个Gazebo。

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
# 仅确认既有链接，不重新创建或复制项目：
readlink -f src/nursing_home_sim
# 应输出 /mnt/d/Sim-Robot
python3 src/nursing_home_sim/scripts/validate_robot.py
gz sdf -k src/nursing_home_sim/worlds/nursing_home.world
colcon build --symlink-install --packages-select nursing_home_sim
source install/setup.bash
ros2 launch nursing_home_sim nursing_home.launch.py navigation:=true use_sim_time:=true
```

若任何校验或构建失败，先处理错误再启动。构建后也可先用 `navigation:=false` 只检查新场景，再停止该实例并用navigation=true重启，始终只保留一个Gazebo实例。

第二终端加载同一环境，查看实体并启动RViz：

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
gz model --list
ros2 node list
ros2 run rviz2 rviz2 --ros-args -p use_sim_time:=true
```

实体列表中应有room_101/room_102而没有door_101/door_102；节点列表不应有本launch启动的door_controller。RViz中Fixed Frame设为map，添加Map（/map）和LaserScan（/scan_filtered），检查 x≈8.5、y≈±2.5 的入口为白色自由通道，不存在门体对应的静态障碍；Gazebo中确认两处没有门框或门板，并保留房间墙壁和家具。运行导航/碰撞通行测试仍须在WSL/Gazebo恢复后实测，本轮未发送导航目标或移动命令。


## 2026-10-05 四轮底盘驱动连接修复

之前四轮底盘只有前轮连接到 Gazebo DiffDrive，左右后轮未加入驱动插件。本轮在实际使用的 `models/dual_arm_robot/model.sdf` 中分别补充 `left_rear_wheel_joint` 和 `right_rear_wheel_joint`，改为四轮差速/skid drive；每侧前后轮共同参与驱动。

只新增两条驱动关节引用。wheel_separation=0.5、wheel_radius=0.1、轮子axis/geometry、摩擦/slip以及其他插件参数保持原样。URDF、导航、扫描过滤、world、地图和出生参数未修改。validator现在检查DiffDrive每侧同时包含前后两个轮子。没有启动Gazebo，也没有提交Git或push；真实车体旋转与odom一致性需要运行复测，不能由关节配置静态检查替代。


## 2026-10-05 默认出生点调整

默认机器人出生/定位点统一为 **(-1.0, 0.0)，yaw=0.0**，用于给机器人提供足够的初始转向空间，减少出生时紧邻前台导致的转向受限。Gazebo spawn z 仍为原值 **0.2 m**；这是生成高度，不是稳定落地后的高度。AMCL initial_pose 为 `(x=-1.0, y=0.0, z=0.0, yaw=0.0)`。

本轮仅改出生点、AMCL初始位姿、对应静态验证和相关位置提示；没有调整地图、障碍物、雷达、过滤器、footprint或导航控制参数。validator 从launch AST读取create参数并检查spawn与AMCL的x/y均为(-1.0,0.0)，同时检查yaw=0及原spawn z未变。

下方历史扫描测试中的前台0.50 m回波是旧测试位置的测量/合成fixture，不是新默认出生点的预期距离；在新出生点使用compare_scan_filter.py时，需要根据实际前向距离指定 `--front-target`，不可仍以0.50 m作为默认位置验收值。测试脚本和历史fixture本轮不修改。


## 2026-10-04 LaserScan 自身回波过滤

本轮只增加软件过滤链，机器人几何、雷达高度、原始扫描桥接及导航其他参数均未修改。未提交Git，未push。

修改文件：

| 文件 | 本轮修改 |
| --- | --- |
| `launch/nursing_home.launch.py` | 无条件启动 scan_self_filter；新增 use_sim_time 参数，默认true，过滤器使用该参数。navigation=false时也运行。 |
| `config/nav2_params.yaml` | 只改AMCL、local/global obstacle_layer和collision_monitor的扫描topic，共4处。 |
| `CMakeLists.txt` | 将两个新节点脚本通过install(PROGRAMS)安装到lib/nursing_home_sim；BUILD_TESTING下增加13项单元测试入口。 |
| `package.xml` | 现有rclpy/sensor_msgs已足够运行节点；为导航YAML静态验证显式声明python3-yaml依赖。 |
| `scripts/validate_robot.py` | 检查节点文件、6个sector、输入/输出topic、QoS、原始桥接、4处Nav2输入、无条件启动、use_sim_time及安装配置。只做静态检查。 |
| `README.md` | 本轮修改、验收命令和限制记录。 |

新增文件：

- `scripts/scan_self_filter.py`：生产过滤节点。
- `scripts/compare_scan_filter.py`：运行时原始/过滤扫描对比节点，不发布速度、不发送导航目标。
- `tests/test_scan_self_filter.py`：13项标准库unittest离线测试，CTest可执行。

最终链路：`Gazebo → ros_gz_bridge → /scan → scan_self_filter → /scan_filtered → Nav2`。原始桥接文件、雷达sensor和frame_id保持原样。

过滤窗口（角度端点包含，距离阈值严格小于）：

| 起始角度 | 结束角度 | 自身距离阈值 |
| --- | --- | --- |
| -142° | -129° | <0.22 m |
| -98° | -82° | <0.34 m |
| -51° | -39° | <0.22 m |
| 39° | 51° | <0.22 m |
| 82° | 98° | <0.34 m |
| 129° | 142° | <0.22 m |

完整过滤逻辑：先deepcopy整个LaserScan；对每个index使用 `angle_min + index * angle_increment` 计算角度，转换为degree并归一化到[-180,180)。只有角度落入窗口且range有限、严格小于对应阈值时，才把复制消息中的这个range改为正inf。窗口内更远的点保留；窗口外近点保留；NaN、正/负inf原样保留。角度元数据非有限时整帧原样复制。header/frame/stamp、所有扫描元数据、ranges长度及intensities都不变，输入消息不修改。所有窗口集中定义在SELF_FILTER_SECTORS，不依赖硬编码采样索引。

过滤器订阅和发布QoS均为 **BEST_EFFORT / VOLATILE / KEEP_LAST / depth=5**。raw /scan bridge仍配置SENSOR_DATA；其运行时实际QoS尚未观测。参考：[rclpy Jazzy QoS定义](https://github.com/ros2/rclpy/blob/jazzy/rclpy/rclpy/qos.py)。

| 导航输入 | 修改前 | 修改后 |
| --- | --- | --- |
| AMCL scan_topic | scan | /scan_filtered |
| local_costmap obstacle_layer.scan.topic | /scan | /scan_filtered |
| global_costmap obstacle_layer.scan.topic | /scan | /scan_filtered |
| collision_monitor.scan.topic | /scan | /scan_filtered |

没有改变observation source名称scan，没有改static_layer、global其他结构、footprint、inflation、raytrace/obstacle范围、DWB、容差、AMCL初始pose、collision polygon/min_points、docking或velocity_smoother。

启动新增节点片段：

```python
scan_self_filter = Node(
    package=pkg_name, executable='scan_self_filter.py',
    name='scan_self_filter', output='screen',
    parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
)
```

该Node直接加入LaunchDescription，未附加navigation条件；use_sim_time启动参数默认true。

### 本轮实际结果

- **离线测试通过：13项。** 包含用户实测cluster区间对应的合成360样本扫描、严格距离阈值和角度边界、非360分辨率和负增量、±π/多圈归一化、NaN/inf、元数据/intensities/输入保留、近环境点与窗口内远点保留，以及运行对比器对错误消息的检出。
- **合成测试：48个自身样本变成inf，合成前向0.504 m返回保持不变。** 这是根据用户数据构造的离线fixture，不是此次Gazebo实测。
- XML/YAML解析、生产Python语法及validator静态检查通过。与本轮开始快照比对，模型、world、地图、原始bridge等文件字节未变；Nav2 YAML仅上述4个字段变化。
- 已尝试指定WSL验收/构建命令，但WSL在创建实例时返回 `Wsl/Service/CreateInstance/E_ACCESSDENIED`。**colcon build没有成功执行。gz sdf -k未执行。**
- **实际RAW vs FILTERED、前台是否仍约0.50 m、6个cluster是否消失、collision_monitor是否active/是否仍APPROACH及0.02 m/s速度链均未实测。** 不将静态或合成测试当作这些运行验收结果。

### 运行验收命令

WSL恢复后，使用原workspace，在终端1执行（若有缺依赖，先rosdep安装源码声明的依赖）：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
python3 src/nursing_home_sim/scripts/validate_robot.py
python3 src/nursing_home_sim/tests/test_scan_self_filter.py -v
gz sdf -k src/nursing_home_sim/models/dual_arm_robot/model.sdf
colcon build --symlink-install --packages-select nursing_home_sim
source install/setup.bash
ros2 launch nursing_home_sim nursing_home.launch.py navigation:=false use_sim_time:=true
```

终端2加载同一环境后：

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 topic info /scan -v
ros2 topic info /scan_filtered -v
ros2 run nursing_home_sim compare_scan_filter.py --pairs 20 --timeout 30 \
  --front-target 0.50 --front-tolerance 0.10 --ros-args -p use_sim_time:=true
```

运行对比脚本按stamp秒/纳秒和frame_id严格配对，两端到达顺序均可；BEST_EFFORT丢帧时保留有界待配对缓存。逐元素核对过滤结果和全部元数据/intensities，报告RAW与FILTERED前向距离、各sector被过滤样本数。只有配对20帧、前向0.50±0.10 m原样保留、六个raw cluster全部被观测到、所有输出符合规则才PASS；错误/超时/未观测到所有cluster会非零退出。机器人需静止在用户原前台测试位置、手臂保持home姿态。它不会证明collision_monitor已通过。

过滤验收通过后，停止原launch再启动Nav2，保持只有一个Gazebo实例，不发送NavigateToPose：

```bash
ros2 launch nursing_home_sim nursing_home.launch.py navigation:=true use_sim_time:=true
ros2 lifecycle get /collision_monitor
ros2 param get /collision_monitor scan.topic
ros2 topic echo /collision_monitor_state
ros2 topic info /cmd_vel_smoothed -v
ros2 topic info /cmd_vel -v
ros2 topic type /cmd_vel_smoothed
```

必须确认collision_monitor为active [3]、订阅/scan_filtered、静止且无真实危险时不因自身回波持续APPROACH。项目通过官方Nav2 bringup启动导航，本轮没有另起重复collision_monitor；用户机器上的实际版本/生命周期仍需上述检查。参考：[Nav2 Jazzy导航启动源码](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_bringup/launch/navigation_launch.py)。

在速度话题类型确认是geometry_msgs/msg/Twist、上述验收通过且机器人前方畅通时，在另一个终端观察/cmd_vel。下面命令向/cmd_vel_smoothed发0.02 m/s持续约3秒，然后发零速；若实际topic为TwistStamped，先按实际接口调整，不直接执行Twist命令：

```bash
timeout 3s ros2 topic pub -r 10 /cmd_vel_smoothed geometry_msgs/msg/Twist \
  '{linear: {x: 0.02}, angular: {z: 0.0}}'
ros2 topic pub --once /cmd_vel_smoothed geometry_msgs/msg/Twist \
  '{linear: {x: 0.0}, angular: {z: 0.0}}'
```

验证 `/cmd_vel_smoothed → collision_monitor → /cmd_vel`，不能以节点启动成功替代速度链验收。

### 剩余限制

自身回波改成inf，只是让导航不把它当成环境障碍；激光先命中立柱/前臂后，真实障碍物的距离已经不可见，过滤器无法穿透结构或恢复后方距离。这些方向仍是物理盲区。若真实近障碍落入同一窗口且低于对应阈值，也无法仅凭这条range区分，可能被过滤。

当前sector只适用于固定navigation/home手臂姿态。机械臂移动或姿态改变后静态窗口可能不准确；本轮没有解决动态手臂遮挡，也没有强制控制手臂回home。导航前必须保持已测量的固定姿态。


## 2026-10-04 低位雷达扫描空隙与局部静态地图层

本节替代 2026-10-01 的高位雷达安装方案。本次经用户确认采用下部四周开放的躯干结构，接受立柱和前臂产生的分散自遮挡。

| 本轮文件 | 修改内容 |
| --- | --- |
| `models/dual_arm_robot/model.sdf` | torso 改为上部箱体、下连接板、4 根细立柱；同步碰撞几何；重算 torso 质心和惯性。降低雷达，缩短支架并将其固定到 base_link。 |
| `urdf/dual_arm_mobile_robot.urdf` | 同步 torso 的 visual/collision/惯性、雷达和支架的关节位姿，保证 TF 与模型一致。 |
| `config/nav2_params.yaml` | 只修改 local_costmap：启用 static_layer，并补齐插件类型。 |
| `scripts/validate_robot.py` | 将旧“雷达高于躯干”的检查替换为扫描空隙、壳体间隙、支架及 torso 两模型一致性检查。 |
| `README.md` | 记录本轮结构、实际检查结果和构建限制。 |

本轮没有修改轮子、双臂、夹爪、相机、world、地图、spawn、launch、global_costmap、AMCL、DWB、导航容差、footprint、collision_monitor、BT 或 docking_server。仓库在本轮开始时已有上一轮的未提交修改，不能将 Git 总差异全部归为本轮。

原雷达相对 base_link：`0 0 0.94 0 0 0`。新雷达：`0 0 0.27 0 0 0`。按用户实际观测的机器人世界 z=0.120002 m，扫描高度由 **1.060002 m** 降到 **0.390002 m**。若新结构导致实际落地高度变化，需以运行中的 model pose 重新核算。

torso 的原点仍为 base z=0.20 m，上边界仍为 z=0.80 m。新的扫描空隙位于 base z=0.22–0.32 m（按上述观测值约离地0.34–0.44 m）。雷达壳体范围 z=0.25–0.29 m，完整位于空隙内；支架中心 z=0.235 m，长0.03 m，从下连接板上表面 z=0.22 延伸到雷达底面 z=0.25。

躯干的6个几何体如下，坐标均相对 torso；所有 visual 与 collision 对应一致：

| 部件 | 尺寸（m） | 中心 xyz（m） | 惯性计算分配质量（kg） |
| --- | --- | --- | --- |
| 上部箱体 | 0.30 × 0.30 × 0.48 | 0, 0, 0.36 | 9.0 |
| 下连接板 | 0.30 × 0.30 × 0.02 | 0, 0, 0.01 | 0.7 |
| 4 根立柱（各） | 0.015 × 0.015 × 0.10 | ±0.125, ±0.125, 0.07 | 0.075 |

torso 总质量保持10 kg；各部件质量是仿真的质量分布假设，不是实体材料强度验证。通过长方体惯性和并轴定理计算，质心相对 torso 为 `(0, 0, 0.3268)`；`ixx=iyy=0.350474058333`、`izz=0.15488625`，非对角项为0。支架保持0.1 kg，缩短后惯性为 `ixx=iyy=0.000023125`、`izz=0.00003125`。

扫描平面低于1.0 m的 reception_desk 顶部，并穿过其实体箱体，几何上可返回前台轮廓；同样可扫描 medicine_shelf。对于小凳子，凳面或凳腿必须与约0.39 m扫描面相交才可能被检测，整体更低的凳子仍会漏检。不能据此宣称已完成全部低障碍物防撞。

扫描平面没有穿过上部箱体或下连接板，雷达壳体与立柱不相交。对模型 visual 的零位水平射线检查（0.1°采样，不计传感器自身原有壳体）得到：正前/正后射线畅通；4 根立柱各遮挡约6.9°，左右前臂各约10.7°；合计约49°，最大连续扇区约10.7°。**仍存在自遮挡，不是完全无遮挡360°**。手臂移动、机器人倾斜和 Gazebo 实际渲染可能改变结果，AMCL 对自回波的响应仍需运行验证。

雷达仍为原2D gpu_lidar：360 samples、0.12–10 m、10 Hz；`scan` topic、`laser_link` frame 和 `<gz_frame_id>` 全部保留。

关键SDF配置：

```xml
<link name="laser_link">
  <pose relative_to="laser_joint">0 0 0 0 0 0</pose>
  <!-- 原传感器与壳体配置保持 -->
</link>
<joint name="laser_joint" type="fixed">
  <pose relative_to="base_link">0 0 0.27 0 0 0</pose>
  <parent>base_link</parent>
  <child>laser_link</child>
</joint>
<joint name="laser_support_joint" type="fixed">
  <pose relative_to="base_link">0 0 0.235 0 0 0</pose>
  <parent>base_link</parent>
  <child>laser_support</child>
</joint>
```

对应URDF配置：

```xml
<joint name="laser_joint" type="fixed">
  <parent link="base_link"/>
  <child link="laser_link"/>
  <origin xyz="0 0 0.27" rpy="0 0 0"/>
</joint>
<joint name="laser_support_joint" type="fixed">
  <parent link="base_link"/>
  <child link="laser_support"/>
  <origin xyz="0 0 0.235" rpy="0 0 0"/>
</joint>
```

local_costmap 原 plugins 为 `["obstacle_layer", "inflation_layer"]`，现在为：

```yaml
local_costmap:
  local_costmap:
    ros__parameters:
      plugins: ["static_layer", "obstacle_layer", "inflation_layer"]
      static_layer:
        plugin: "nav2_costmap_2d::StaticLayer"
        map_subscribe_transient_local: True
```

本轮实际验证：模型和URDF XML解析通过；nav2_params.yaml 经 PyYAML 解析通过；全模型关节位姿、惯性、控制桥检查通过；扫描空隙检查通过；与本轮开始快照逐节点比较，确认只有 torso/支架/雷达关节改变，其他模型节点和传感器参数未改；Nav2 参数只改变上述两个local_costmap字段。

`gz sdf -k` 未执行（Windows环境没有gz）；XML检查不等同于SDF官方校验。已尝试通过 WSL 执行指定构建命令，WSL 在创建实例时返回 `Wsl/Service/CreateInstance/E_ACCESSDENIED`，因此 **colcon build 未成功执行，不能标记构建通过**。未启动新的Gazebo实例。静止物理稳定性、实际扫描、TF时间同步和定位效果均未实测。

Ubuntu/WSL服务恢复后，在正式workspace执行：

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
python3 src/nursing_home_sim/scripts/validate_robot.py
gz sdf -k src/nursing_home_sim/models/dual_arm_robot/model.sdf
colcon build --symlink-install --packages-select nursing_home_sim
source install/setup.bash
ros2 launch nursing_home_sim nursing_home.launch.py
```

先只运行一个Gazebo实例，静止30秒确认姿态与实际雷达高度。用 `ros2 run tf2_ros tf2_echo base_link laser_link` 验证 `(0,0,0.27)`；在RViz核实前台轮廓、自遮挡角度，并放置/移动实际凳子测试各方向检测。通过模型检查后再重启带 `navigation:=true` 的启动，检查local_costmap静态层、map→odom TF及AMCL对自回波的影响。

静态地图层配置参考：[Nav2 Jazzy StaticLayer源码](https://api.nav2.org/nav2-jazzy/html/static__layer_8cpp_source.html)。


这是一个基于 ROS2 Jazzy 和 Gazebo Harmonic 的养老院双臂机器人仿真项目。当前具备机器人模型、传感器、关节控制与导航配置；送药脚本是动作演示，尚未实现经验证的物体抓取、交接及完整送药闭环。

## 功能特点

- ✅ 完整的养老院环境（前台、房间、电梯、走廊）
- ✅ 轮式双臂机器人模型
- ✅ 自主导航系统（Nav2）
- 101、102房间入口暂时常开，门控制源代码保留
- 双指夹爪与抓取/放置姿态演示（物体接触、抓取成功判定尚未完成）
- ✅ 电梯控制（支持多楼层）

## 系统要求

- Ubuntu 24.04（WSL2 需先完成安装及 WSLg/GPU 支持）
- ROS2 Jazzy
- Gazebo Harmonic / ros_gz
- Python 3；离线静态验证仅依赖标准库


## 2026-10-01 模型、双臂与传感器更新

以本节为当前版本说明；下方历史示例及其他旧文档中的三关节控制、旧版 ROS/Gazebo 参数不作为当前验收依据。

- `models/dual_arm_robot/model.sdf` 是主启动文件实际生成的物理模型。`models/dual_arm_robot_gazebo.sdf` 为历史文件，本轮未使用或更新。
- 修复所有机械臂和雷达子 link 的 semantic pose：joint 相对 parent；child link 相对对应 joint 的 pose 为零。消除机械臂默认落在模型原点的问题。
- 每臂六个旋转自由度：shoulder（Y）、upper_arm（X）、elbow（Y）、forearm（Z）、wrist（Y）、gripper（Z）；额外两根独立滑动手指，各行程 0–0.025 m。保留原关节命名。
- 肩部位于 torso 的 `(0, ±0.32, 0.5)`，增大与躯干、底盘及轮子的零位间隙。上臂 0.30 m、前臂 0.24 m；夹爪改为掌部和双指，仍为简化几何。
- 雷达位于 base_link 的 `(0, 0, 0.94)`，增加短支架，使水平扫描面高于躯干和零位双臂；`/scan` frame 为 `laser_link`。此高度不能看到低于扫描面的障碍，需要后续低位/深度感知。
- 前向 RGB 相机位于 torso 的 `(0.20, 0, 0.65)`；640×480、15 Hz、约 60° 水平视野。输出 `/camera/image_raw` 和 `/camera/camera_info`；光学坐标系 `camera_optical_frame`，固定旋转 `(-π/2, 0, -π/2)`。本轮没有加入深度相机。
- 同步 URDF/SDF 的关节位姿、轴、限位和双臂惯性；新增 16 个 Gazebo 原生力矩/力 PID 控制器，接入原有 Float64 命令 API。PID 参数仅为起始值，待目标物理引擎调参。
- `config/ros_gz_bridge.yaml` 明确定义 24 条单向桥接；加入 `/joint_states`、相机、16 路关节命令和 `/odom_tf` → ROS `/tf`。只有 DiffDrive 发布 odom→base_link；robot_state_publisher 发布模型关节 TF。新配置采用 JSON 语法（合法 YAML），可直接由 YAML 解析器读取。
- 删除未启动且类型错误的 ros2_control 配置，`robot_controllers.yaml` 仅记录原生控制器关节清单，不是 controller_manager 参数文件。
- AMCL 初始位置与生成位置统一为 `(-1.0, 0)`（2026-10-05 更新），雷达范围为 0.12–10 m；costmap 使用包含底盘、轮子及零位手臂的多边形轮廓。手臂伸出时需要后续动态轮廓或锁定导航时收臂。
- 2D 激光的局部代价地图改用 ObstacleLayer，避免高位雷达超出旧 0.8 m 体素网格导致射线清除失败。
- 更新 Jazzy progress checker 参数，移除旧版 BT 内置插件列表。
- 默认启动只开模型、传感器及控制桥；导航和任务演示分别用 `navigation:=true`、`task_controllers:=true` 开启。先验证静止模型，再启动导航。
- 更新 `test_arms.py`：顺序小幅运动所有旋转关节和手指，以新鲜 joint_states 判断到位，缺反馈或超时返回失败。仅检查关节运动，不代表避碰或真实抓取验证。
- 送药演示可访问全部新关节，并将“已抓取/已放置”提示改为未验证的姿态命令提示。该演示仍未实现 IK、MoveIt、双臂交接和接触反馈。

### 本次实际验证与限制

Windows 标准库静态验证通过：XML 可解析、连通无环关节树、两模型 link/joint 清单一致、关节位姿/轴/限位一致、正质量及惯量检查、每臂 6 自由度和 2 指、16 个控制器与命令桥对应、传感器 frame、Python 语法检查。`git diff --check` 通过。

本机 WSL 查询返回 `Wsl/EnumerateDistros/Service/E_ACCESSDENIED`；`gz` 不可用，Docker daemon 未启动。本轮没有执行 `gz sdf -k`、colcon、30 秒静止物理验收、图像显示或 AMCL 定位验收；未声称已验证不侧翻。没有修改 build/install/log，没有新建第二套 ROS workspace，也没有修改或重装 WSL。

### Ubuntu 就绪后的验收步骤

使用 Ubuntu 24.04 + ROS2 Jazzy + Gazebo Harmonic。正式 workspace 仍为 `~/ros2_ws`，源码路径应链接到 `/mnt/d/Sim-Robot`。确认安装 ros_gz、Nav2、xacro、robot_state_publisher 和 colcon/rosdep 后：

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
python3 src/nursing_home_sim/scripts/validate_robot.py
gz sdf -k src/nursing_home_sim/models/dual_arm_robot/model.sdf
colcon build --symlink-install --packages-select nursing_home_sim
source install/setup.bash
ros2 launch nursing_home_sim nursing_home.launch.py
```

在第二个已 source 同一环境的终端检查；前 30 秒不发送 cmd_vel、不运行手臂测试：

```bash
gz model -m dual_arm_robot --pose
ros2 topic echo /joint_states --once
ros2 topic echo /scan --once --qos-reliability best_effort
ros2 topic hz /camera/image_raw
ros2 topic echo /camera/camera_info --once --qos-reliability best_effort
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo base_link laser_link
ros2 run tf2_ros tf2_echo base_link camera_optical_frame
```

确认 roll/pitch 稳定、双臂完整可见、夹爪不碰底盘或地面、scan 无机器人自身遮挡、相机图像方向正确后，运行 `ros2 run nursing_home_sim test_arms.py`。记录每个关节反馈结果，若 PID 振荡则先调参；不能仅以脚本发送成功验收。

通过模型和传感器验收后，停止原启动并重启：

```bash
ros2 launch nursing_home_sim nursing_home.launch.py navigation:=true
ros2 run tf2_ros tf2_echo map base_link
ros2 topic echo /amcl_pose --once
```

在 RViz 对照地图、激光点与实际位置，确认地图匹配、AMCL 收敛及完整 map→odom→base_link→laser_link 链路后再发送导航目标。本轮未调整地图，定位效果还需实测。任务脚本只能作为演示，不能作为已实现送药功能的验收标准。

参考： [Gazebo Harmonic ROS 集成](https://gazebosim.org/docs/harmonic/ros2_integration/)、[Harmonic 迁移与相机 frame 配置](https://gazebosim.org/docs/harmonic/migrating_gazebo_classic_ros2_packages/)、[Gazebo 8 原生关节位置控制器](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/joint_position_controller/JointPositionController.cc)、[Nav2 Jazzy 控制器参数](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/controller_server/)。

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

### 手动控制门（当前停用，以下命令仅供恢复功能后使用）

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
4. **通过入口**: 101、102入口常开，跳过开门
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

### 问题：门无法打开（当前版本无门模型，以下为历史排查方法）
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
