cmake_minimum_required(VERSION 3.8)
project(nursing_home_sim)

# 编译选项
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 查找依赖 - ROS2 Jazzy + Gazebo Harmonic
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclpy REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(robot_state_publisher REQUIRED)
find_package(urdf REQUIRED)
find_package(xacro REQUIRED)

# 安装 Python 脚本（作为可执行文件）
install(PROGRAMS
  scripts/medicine_delivery_controller.py
  scripts/door_controller.py
  scripts/elevator_controller.py
  scripts/keyboard_control.py
  scripts/test_delivery.py
  scripts/test_arms.py
  DESTINATION lib/${PROJECT_NAME}
)

# 安装 launch 文件
install(DIRECTORY
  launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

# 安装 world 文件
install(DIRECTORY
  worlds/
  DESTINATION share/${PROJECT_NAME}/worlds
)

# 安装 URDF 文件
install(DIRECTORY
  urdf/
  DESTINATION share/${PROJECT_NAME}/urdf
)

# 安装 models 文件
install(DIRECTORY
  models/
  DESTINATION share/${PROJECT_NAME}/models
)

# 安装配置文件
install(DIRECTORY
  config/
  DESTINATION share/${PROJECT_NAME}/config
)

# 安装地图文件
install(DIRECTORY
  maps/
  DESTINATION share/${PROJECT_NAME}/maps
  OPTIONAL
)

# 安装模型文件
install(DIRECTORY
  models/
  DESTINATION share/${PROJECT_NAME}/models
  OPTIONAL
)

# 测试
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
