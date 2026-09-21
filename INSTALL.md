# 养老院送药机器人仿真系统 - 安装指南 (ROS2)

## 系统要求

- **操作系统**: Ubuntu 20.04 / 22.04
- **ROS2版本**: ROS2 Foxy (20.04) / Galactic / Humble (22.04)
- **Gazebo**: 11.0+ 
- **Python**: 3.8+
- **硬件要求**: 
  - CPU: Intel i5 或更高
  - RAM: 8GB 或更多
  - GPU: 建议有独立显卡（用于Gazebo渲染）

## 详细安装步骤

### 1. 安装ROS2

#### Ubuntu 22.04 安装 ROS2 Humble

```bash
# 设置UTF-8
sudo apt update && sudo apt install locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# 添加ROS2仓库
sudo apt install software-properties-common
sudo add-apt-repository universe

sudo apt update && sudo apt install curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# 更新并安装ROS2
sudo apt update
sudo apt upgrade

# 安装ROS2桌面版（包含RViz等）
sudo apt install ros-humble-desktop

# 安装开发工具
sudo apt install ros-dev-tools

# 环境设置
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

#### Ubuntu 20.04 安装 ROS2 Foxy

```bash
# 设置sources.list
sudo apt update && sudo apt install curl gnupg lsb-release
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(source /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# 安装ROS2
sudo apt update
sudo apt install ros-foxy-desktop

# 环境设置
echo "source /opt/ros/foxy/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 2. 安装Gazebo及相关包

```bash
# Gazebo（ROS2通常使用Gazebo 11）
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control

# 安装Nav2导航包
sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup

# 安装机器人状态发布器
sudo apt install ros-humble-robot-state-publisher \
                 ros-humble-joint-state-publisher \
                 ros-humble-joint-state-publisher-gui

# 安装xacro（用于处理URDF）
sudo apt install ros-humble-xacro

# 安装额外工具
sudo apt install ros-humble-tf2-tools \
                 ros-humble-rqt* \
                 ros-humble-rviz2
```

### 3. 创建Colcon工作空间

```bash
# 创建工作空间目录
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/

# 初始化工作空间（编译空工作空间）
colcon build

# 添加到环境变量
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 4. 复制项目到工作空间

#### 方法A: 从Windows D盘复制（WSL用户）

```bash
# 复制整个项目
cp -r /mnt/d/Sim-Robot ~/ros2_ws/src/nursing_home_sim

# 或者创建软链接（推荐开发时使用）
ln -s /mnt/d/Sim-Robot ~/ros2_ws/src/nursing_home_sim
```

#### 方法B: 从Git克隆

```bash
cd ~/ros2_ws/src
git clone https://github.com/yourusername/nursing_home_sim.git
```

#### 方法C: 手动复制

```bash
# 将D:\Sim-Robot文件夹复制到 ~/ros2_ws/src/ 并重命名为 nursing_home_sim
```

### 5. 设置脚本权限

```bash
cd ~/ros2_ws/src/nursing_home_sim/scripts
chmod +x *.py
cd ~/ros2_ws/src/nursing_home_sim
chmod +x *.sh
```

### 6. 编译项目

```bash
cd ~/ros2_ws

# 编译指定包
colcon build --packages-select nursing_home_sim

# 或编译所有包
colcon build

# 刷新环境
source install/setup.bash
```

### 7. 验证安装

```bash
# 检查包是否被识别
ros2 pkg list | grep nursing_home_sim

# 应该输出：nursing_home_sim

# 列出可用的launch文件
ros2 pkg prefix nursing_home_sim
ls $(ros2 pkg prefix nursing_home_sim)/share/nursing_home_sim/launch/
```

## 可选：安装RViz2和其他可视化工具

```bash
# RViz2（通常已随ROS2安装）
sudo apt install ros-humble-rviz2

# rqt工具集
sudo apt install ros-humble-rqt-robot-plugins

# 图形化工具
sudo apt install ros-humble-plotjuggler-ros
```

## 第一次运行

### 快速测试

```bash
# 1. 测试Gazebo
ros2 launch gazebo_ros gazebo.launch.py

# 如果Gazebo正常启动，说明基本环境OK
# 按 Ctrl+C 关闭
```

### 启动完整仿真

```bash
# 方法1: 使用启动脚本
cd ~/ros2_ws/src/nursing_home_sim
./start_simulation.sh

# 方法2: 使用ros2 launch
ros2 launch nursing_home_sim nursing_home.launch.py
```

### 发送测试任务

在新终端中：

```bash
# 等待系统完全启动（约10-15秒）
ros2 topic pub /medicine_delivery_task std_msgs/msg/String "data: '测试药品,101'" --once
```

## 常见安装问题

### 问题1: colcon找不到包

**错误信息**: `Package 'nursing_home_sim' not found`

**解决方法**:
```bash
cd ~/ros2_ws
colcon build --packages-select nursing_home_sim
source install/setup.bash
```

### 问题2: Gazebo启动黑屏或崩溃

**解决方法**:
```bash
# 重置Gazebo
killall -9 gzserver gzclient
rm -rf ~/.gazebo/

# 如果是显卡问题，尝试软件渲染
export LIBGL_ALWAYS_SOFTWARE=1
```

### 问题3: Python脚本无法执行

**错误信息**: `Permission denied`

**解决方法**:
```bash
# 确保脚本有执行权限
cd ~/ros2_ws/src/nursing_home_sim/scripts
chmod +x *.py

# 确保Python路径正确（脚本第一行）
head -1 medicine_delivery_controller.py
# 应该显示: #!/usr/bin/env python3
```

### 问题4: 找不到Nav2或导航包

**解决方法**:
```bash
sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup
```

### 问题5: TF错误或坐标系问题

**解决方法**:
```bash
# 查看TF树
ros2 run tf2_tools view_frames

# 检查TF发布
ros2 run tf2_ros tf2_echo map base_link
```

### 问题6: 编译错误 - 找不到ament_cmake

**解决方法**:
```bash
# 确保已source ROS2环境
source /opt/ros/humble/setup.bash
cd ~/ros2_ws
colcon build --packages-select nursing_home_sim
```

### 问题7: launch文件找不到

**错误信息**: `Package 'nursing_home_sim' not found` 或找不到launch文件

**解决方法**:
```bash
# 确保launch文件已安装
cd ~/ros2_ws
colcon build --packages-select nursing_home_sim --symlink-install
source install/setup.bash

# 检查launch文件是否存在
ls $(ros2 pkg prefix nursing_home_sim)/share/nursing_home_sim/launch/
```

### 问题8: Nav2参数文件错误

**解决方法**:
```bash
# 检查nav2_params.yaml是否存在
ls ~/ros2_ws/src/nursing_home_sim/config/nav2_params.yaml

# 如果不存在，确保已复制所有文件
```

## 卸载

如果需要完全卸载：

```bash
# 删除工作空间中的包
rm -rf ~/ros2_ws/src/nursing_home_sim

# 重新编译
cd ~/ros2_ws
colcon build

# 如果要完全卸载ROS2
sudo apt remove ros-humble-*
sudo apt autoremove
```

## 性能优化

### 提高Gazebo性能

编辑 `~/.gazebo/gui.ini`:
```ini
[geometry]
x=0
y=0

[rendering]
anti_aliasing=0
```

### 降低仿真质量以提高速度

在 `nursing_home.launch.py` 中修改：
```python
launch_arguments={
    'gui': 'false',  # 无GUI模式
    ...
}.items()
```

### 使用--symlink-install加速开发

```bash
# 开发时使用符号链接，避免每次都重新复制文件
colcon build --packages-select nursing_home_sim --symlink-install
```

## 开发环境设置（可选）

### VS Code 配置

安装扩展：
- ROS
- Python
- CMake

在项目根目录创建 `.vscode/settings.json`:
```json
{
    "python.autoComplete.extraPaths": [
        "/opt/ros/humble/lib/python3.10/site-packages",
        "/opt/ros/humble/local/lib/python3.10/dist-packages"
    ],
    "python.analysis.extraPaths": [
        "/opt/ros/humble/lib/python3.10/site-packages",
        "/opt/ros/humble/local/lib/python3.10/dist-packages"
    ],
    "cmake.configureOnOpen": false
}
```

## ROS2 vs ROS1 主要区别

本项目从ROS1迁移到ROS2，主要变化：

1. **启动文件**: XML格式 → Python格式
2. **导航**: move_base → Nav2
3. **Python库**: rospy → rclpy
4. **构建工具**: catkin_make → colcon
5. **话题命令**: `rostopic` → `ros2 topic`
6. **节点命令**: `rosnode` → `ros2 node`

## 下一步

安装完成后，请查看以下文档：
- `README.md` - 项目概览和功能说明
- `QUICK_START.md` - 快速参考指南
- `ARCHITECTURE.md` - 系统架构说明

## 获取帮助

如果遇到问题：
1. 检查ROS2日志：`~/.ros/log/latest/`
2. 查看Gazebo日志：`~/.gazebo/`
3. 使用 `ros2 topic list` 和 `ros2 node list` 诊断
4. 在GitHub Issues提问

## 更新日志

- v2.0.0 (2026-09-18): ROS2版本发布
- v1.0.0 (2026-09-18): ROS1初始版本
