# 📖 文档索引 - ROS2 Jazzy + Gazebo Harmonic

> 养老院送药机器人仿真系统完整文档导航

---

## 🚀 快速开始

**新用户从这里开始 →** [`JAZZY_QUICKSTART.md`](JAZZY_QUICKSTART.md)

3 步启动系统，5 分钟内看到机器人运行。

---

## 📚 核心文档

### 1. 迁移相关

| 文档 | 说明 | 适用场景 |
|------|------|----------|
| [`ROS2_JAZZY_MIGRATION_SUMMARY.md`](ROS2_JAZZY_MIGRATION_SUMMARY.md) | ✅ **迁移总结** - 完整的迁移报告 | 了解从 ROS1 到 ROS2 Jazzy 的所有变更 |
| [`ROS2_MIGRATION_REPORT.md`](ROS2_MIGRATION_REPORT.md) | 详细迁移报告 | 技术细节和修复记录 |

### 2. 安装和配置

| 文档 | 说明 | 适用场景 |
|------|------|----------|
| [`INSTALL.md`](INSTALL.md) | 完整安装指南 | 首次安装系统 |
| [`JAZZY_QUICKSTART.md`](JAZZY_QUICKSTART.md) | ⚡ **3步快速启动** | 快速上手 |
| [`COMMAND_CHEATSHEET.md`](COMMAND_CHEATSHEET.md) | 🔖 **命令速查表** | 常用命令参考 |

### 3. 使用指南

| 文档 | 说明 | 适用场景 |
|------|------|----------|
| [`README.md`](README.md) | 项目概览 | 项目介绍和总体架构 |
| [`QUICK_START.md`](QUICK_START.md) | 快速开始 | 基础使用教程 |
| [`使用指南.md`](使用指南.md) | 中文使用指南 | 详细的中文说明 |

### 4. 开发文档

| 文档 | 说明 | 适用场景 |
|------|------|----------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 系统架构 | 理解系统设计 |
| [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md) | 项目总结 | 项目整体介绍 |
| [`TODO.md`](TODO.md) | 开发计划 | 查看待开发功能 |

### 5. 问题解决

| 文档 | 说明 | 适用场景 |
|------|------|----------|
| [`FAQ.md`](FAQ.md) | 常见问题 | 遇到问题时查阅 |

---

## 🎯 按需求选择文档

### 我想快速启动系统
1. ✅ [`JAZZY_QUICKSTART.md`](JAZZY_QUICKSTART.md) - 3步启动
2. 📋 [`COMMAND_CHEATSHEET.md`](COMMAND_CHEATSHEET.md) - 测试命令

### 我从 ROS1 迁移过来
1. 📊 [`ROS2_JAZZY_MIGRATION_SUMMARY.md`](ROS2_JAZZY_MIGRATION_SUMMARY.md) - 了解所有变更
2. 🔍 运行 `check_ros1_residue.sh` - 检查残留

### 我是第一次使用
1. 📖 [`README.md`](README.md) - 项目介绍
2. 🔧 [`INSTALL.md`](INSTALL.md) - 安装依赖
3. 🚀 [`JAZZY_QUICKSTART.md`](JAZZY_QUICKSTART.md) - 启动系统
4. 📚 [`使用指南.md`](使用指南.md) - 详细教程

### 我遇到了问题
1. ❓ [`FAQ.md`](FAQ.md) - 查看常见问题
2. 🐛 运行 `check_ros1_residue.sh` - 检查配置
3. 📋 [`COMMAND_CHEATSHEET.md`](COMMAND_CHEATSHEET.md) - 故障排查命令

### 我想开发新功能
1. 🏗️ [`ARCHITECTURE.md`](ARCHITECTURE.md) - 理解架构
2. 📝 [`TODO.md`](TODO.md) - 查看开发计划
3. 📊 [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md) - 项目整体信息

---

## 🛠️ 工具脚本

| 脚本 | 说明 | 使用方法 |
|------|------|----------|
| `start_simulation.sh` | ✅ **主启动脚本** | `./start_simulation.sh` |
| `full_test.sh` | 🧪 完整测试脚本 | `./full_test.sh` |
| `check_ros1_residue.sh` | 🔍 ROS1 残留检查 | `./check_ros1_residue.sh` |

---

## 📦 项目结构

```
D:\Sim-Robot/
├── 📁 launch/              # 启动文件（Python）
│   ├── nursing_home.launch.py    ✅ ROS2 + Gazebo Harmonic
│   └── navigation.launch.py      ✅ Nav2 导航
│
├── 📁 urdf/                # 机器人模型
│   └── dual_arm_mobile_robot.urdf  ✅ Gazebo Harmonic 插件
│
├── 📁 scripts/             # Python 脚本（rclpy）
│   ├── medicine_delivery_controller.py
│   ├── door_controller.py
│   ├── elevator_controller.py
│   ├── keyboard_control.py
│   ├── test_delivery.py
│   └── test_arms.py
│
├── 📁 config/              # 配置文件
│   └── nav2_params.yaml          ✅ Nav2 参数
│
├── 📁 worlds/              # Gazebo 世界文件
│   └── nursing_home.world
│
├── 📁 maps/                # 地图文件
│
├── 📄 package.xml          ✅ ros_gz 依赖
├── 📄 CMakeLists.txt       ✅ ament_cmake
│
└── 📚 文档/
    ├── README.md                           # 项目概览
    ├── JAZZY_QUICKSTART.md                 # ⚡ 快速开始
    ├── COMMAND_CHEATSHEET.md               # 🔖 命令速查
    ├── ROS2_JAZZY_MIGRATION_SUMMARY.md     # ✅ 迁移总结
    ├── ROS2_MIGRATION_REPORT.md            # 迁移报告
    ├── INSTALL.md                          # 安装指南
    ├── QUICK_START.md                      # 使用教程
    ├── 使用指南.md                          # 中文指南
    ├── ARCHITECTURE.md                     # 系统架构
    ├── PROJECT_SUMMARY.md                  # 项目总结
    ├── FAQ.md                              # 常见问题
    └── TODO.md                             # 开发计划
```

---

## ⚡ 最常用的命令

```bash
# 1. 快速启动
./start_simulation.sh

# 2. 发送任务
ros2 topic pub /medicine_delivery_task std_msgs/msg/String "data: '阿司匹林,101'" --once

# 3. 控制机器人
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.0}}"

# 4. 查看状态
ros2 topic list
ros2 node list

# 5. 检查配置
./check_ros1_residue.sh
```

完整命令列表：[`COMMAND_CHEATSHEET.md`](COMMAND_CHEATSHEET.md)

---

## 🎓 学习路径

### 初级（第 1 天）
1. 阅读 [`README.md`](README.md) 了解项目
2. 按照 [`JAZZY_QUICKSTART.md`](JAZZY_QUICKSTART.md) 启动系统
3. 尝试发送送药任务
4. 查看 [`COMMAND_CHEATSHEET.md`](COMMAND_CHEATSHEET.md) 学习基础命令

### 中级（第 2-3 天）
1. 阅读 [`ARCHITECTURE.md`](ARCHITECTURE.md) 理解架构
2. 阅读 [`使用指南.md`](使用指南.md) 学习详细用法
3. 运行测试脚本：`test_delivery.py`, `test_arms.py`
4. 尝试修改参数文件

### 高级（第 4+ 天）
1. 阅读 [`ROS2_JAZZY_MIGRATION_SUMMARY.md`](ROS2_JAZZY_MIGRATION_SUMMARY.md) 了解技术细节
2. 学习 Gazebo Harmonic 插件系统
3. 开发新功能（参考 [`TODO.md`](TODO.md)）
4. 参与项目贡献

---

## 🔧 技术栈

| 组件 | 版本 | 说明 |
|------|------|------|
| Ubuntu | 24.04 | 操作系统 |
| ROS2 | Jazzy | 机器人框架 |
| Gazebo | Harmonic | 物理仿真 |
| ros_gz | latest | ROS-Gazebo 桥接 |
| Nav2 | latest | 导航系统 |
| Python | 3.12+ | 脚本语言 |

---

## 📞 获取帮助

1. 📖 查看 [`FAQ.md`](FAQ.md)
2. 🔍 运行 `./check_ros1_residue.sh`
3. 📋 查看 [`COMMAND_CHEATSHEET.md`](COMMAND_CHEATSHEET.md) 故障排查部分
4. 💬 提交 Issue 到项目仓库

---

## ✅ 快速检查清单

使用前确保：

- [ ] Ubuntu 24.04 已安装
- [ ] ROS2 Jazzy 已安装
- [ ] Gazebo Harmonic 已安装
- [ ] ros_gz 包已安装
- [ ] 项目已编译成功
- [ ] 环境已 source

运行检查：
```bash
./check_ros1_residue.sh
```

---

## 🎯 推荐阅读顺序

**新用户**：README → JAZZY_QUICKSTART → COMMAND_CHEATSHEET → 使用指南

**迁移用户**：ROS2_JAZZY_MIGRATION_SUMMARY → JAZZY_QUICKSTART → COMMAND_CHEATSHEET

**开发者**：README → ARCHITECTURE → PROJECT_SUMMARY → TODO

**问题排查**：FAQ → check_ros1_residue.sh → COMMAND_CHEATSHEET (故障排查)

---

**最后更新**: 2026-09-18  
**项目状态**: ✅ 完全兼容 ROS2 Jazzy + Gazebo Harmonic  
**文档版本**: 2.0  

🎉 享受使用 ROS2 Jazzy + Gazebo Harmonic！
