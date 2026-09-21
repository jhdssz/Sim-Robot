# 常见问题解答 (FAQ)

## 安装相关

### Q1: 我应该使用哪个Ubuntu版本？
**A:** 推荐使用Ubuntu 20.04 LTS + ROS Noetic。这是最稳定的组合。Ubuntu 18.04 + ROS Melodic也可以工作。

### Q2: 安装时提示找不到ROS包怎么办？
**A:** 
```bash
# 更新软件源
sudo apt update

# 如果还是找不到，检查是否添加了ROS源
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
```

### Q3: catkin_make编译失败？
**A:**
```bash
# 清理并重新编译
cd ~/catkin_ws
rm -rf build devel
catkin_make

# 如果是Python版本问题
catkin_make -DPYTHON_EXECUTABLE=/usr/bin/python3
```

## 运行相关

### Q4: Gazebo启动后黑屏或卡住？
**A:**
```bash
# 方法1: 重置Gazebo配置
killall -9 gzserver gzclient
rm -rf ~/.gazebo/

# 方法2: 使用软件渲染（虚拟机中）
export LIBGL_ALWAYS_SOFTWARE=1
roslaunch nursing_home_sim nursing_home.launch

# 方法3: 关闭GUI（无头模式）
roslaunch nursing_home_sim nursing_home.launch gui:=false
```

### Q5: 机器人不移动？
**A:**
```bash
# 检查1: 确认move_base在运行
rosnode list | grep move_base

# 检查2: 查看速度命令是否发布
rostopic echo /cmd_vel

# 检查3: 查看导航状态
rostopic echo /move_base/status

# 检查4: 确认没有错误日志
rostopic echo /move_base/local_costmap/footprint
```

### Q6: 找不到包 "nursing_home_sim"？
**A:**
```bash
# 确保source了工作空间
source ~/catkin_ws/devel/setup.bash

# 添加到bashrc使其永久生效
echo "source ~/catkin_ws/devel/setup.bash" >> ~/.bashrc

# 验证包是否存在
rospack find nursing_home_sim
```

### Q7: Python脚本无法执行？
**A:**
```bash
# 添加执行权限
cd ~/catkin_ws/src/nursing_home_sim/scripts
chmod +x *.py

# 检查Python解释器路径
head -1 medicine_delivery_controller.py
# 应该显示: #!/usr/bin/env python 或 #!/usr/bin/env python3
```

## 导航相关

### Q8: 机器人导航时撞到障碍物？
**A:** 调整代价地图参数
```yaml
# 编辑 config/costmap_common_params.yaml
inflation_radius: 0.55  # 增大这个值
obstacle_range: 2.5     # 增大检测范围
```

### Q9: 机器人导航很慢或抖动？
**A:** 调整速度参数
```yaml
# 编辑 config/base_local_planner_params.yaml
max_vel_x: 0.5          # 提高最大速度
acc_lim_x: 3.0          # 提高加速度
```

### Q10: 机器人在原地转圈，无法到达目标？
**A:**
```bash
# 可能是定位问题，检查AMCL
rostopic echo /amcl_pose

# 或者代价地图有问题，可视化查看
rosrun rviz rviz
# 添加 Map, Local Costmap, Global Costmap
```

## 机械臂相关

### Q11: 机械臂不动？
**A:**
```bash
# 检查关节控制话题
rostopic list | grep joint

# 手动测试单个关节
rostopic pub /dual_arm_robot/left_shoulder_joint/command std_msgs/Float64 "data: 0.5"

# 查看是否有joint_states发布
rostopic echo /joint_states
```

### Q12: 机械臂运动范围受限？
**A:** 检查URDF中的关节限制
```xml
<!-- 在 dual_arm_mobile_robot.urdf 中 -->
<limit lower="-1.57" upper="1.57" effort="50" velocity="1.0"/>
<!-- 可以调整 lower 和 upper 值 -->
```

## 任务执行相关

### Q13: 发送任务后没有反应？
**A:**
```bash
# 检查控制器是否运行
rosnode list | grep medicine_delivery

# 查看控制器日志
rosnode info /medicine_delivery_controller

# 手动启动控制器
rosrun nursing_home_sim medicine_delivery_controller.py
```

### Q14: 机器人到达目标后没有执行抓取动作？
**A:** 检查代码中的动作序列是否正确执行，可能需要增加等待时间：
```python
# 在 medicine_delivery_controller.py 中
time.sleep(2)  # 增加这个延迟
```

### Q15: 门无法打开？
**A:**
```bash
# 检查门控制器
rosnode list | grep door

# 手动测试开门
rostopic pub /door_control std_msgs/String "data: 'open,door_101'"

# 查看Gazebo中门的关节名称是否正确
gz joint -m door_101 -l
```

## 性能相关

### Q16: 仿真运行很卡？
**A:**
```bash
# 方法1: 降低Gazebo更新频率
# 编辑 nursing_home.launch，添加：
<arg name="use_sim_time" value="true"/>

# 方法2: 关闭Gazebo GUI
roslaunch nursing_home_sim nursing_home.launch gui:=false

# 方法3: 减少传感器更新频率
# 在URDF中修改 <updateRate>
```

### Q17: CPU占用过高？
**A:**
```bash
# 降低物理引擎精度
# 编辑 worlds/nursing_home.world
<max_step_size>0.01</max_step_size>  # 增大这个值
<real_time_update_rate>100</real_time_update_rate>  # 降低这个值
```

## 传感器相关

### Q18: 没有激光雷达数据？
**A:** 当前版本没有添加激光雷达传感器。如需添加：
```xml
<!-- 在URDF中添加 -->
<gazebo reference="base_link">
  <sensor type="ray" name="laser">
    <pose>0 0 0.2 0 0 0</pose>
    <ray>
      <scan>
        <horizontal>
          <samples>360</samples>
          <resolution>1</resolution>
          <min_angle>-3.14159</min_angle>
          <max_angle>3.14159</max_angle>
        </horizontal>
      </scan>
      <range>
        <min>0.1</min>
        <max>10.0</max>
      </range>
    </ray>
    <plugin name="gazebo_ros_laser" filename="libgazebo_ros_laser.so">
      <topicName>/scan</topicName>
    </plugin>
  </sensor>
</gazebo>
```

### Q19: 如何添加摄像头？
**A:**
```xml
<!-- 在URDF中添加相机传感器 -->
<gazebo reference="camera_link">
  <sensor type="camera" name="camera1">
    <camera>
      <horizontal_fov>1.3962634</horizontal_fov>
      <image>
        <width>640</width>
        <height>480</height>
      </image>
    </camera>
    <plugin name="camera_controller" filename="libgazebo_ros_camera.so">
      <cameraName>camera</cameraName>
      <imageTopicName>image_raw</imageTopicName>
    </plugin>
  </sensor>
</gazebo>
```

## 地图相关

### Q20: 没有地图文件 nursing_home_map.pgm？
**A:** 需要使用SLAM生成地图：
```bash
# 方法1: 使用gmapping
rosrun gmapping slam_gmapping

# 手动控制机器人走一圈
rosrun nursing_home_sim keyboard_control.py

# 保存地图
rosrun map_server map_saver -f ~/catkin_ws/src/nursing_home_sim/maps/nursing_home_map

# 方法2: 使用cartographer（更精确）
# 或者方法3: 使用Gazebo的build_map工具
```

## 调试技巧

### Q21: 如何调试ROS节点？
**A:**
```bash
# 查看所有节点
rosnode list

# 查看节点信息
rosnode info /medicine_delivery_controller

# 查看所有话题
rostopic list

# 监听话题内容
rostopic echo /odom

# 查看话题频率
rostopic hz /cmd_vel

# 查看计算图
rqt_graph

# 查看TF树
rosrun tf view_frames
evince frames.pdf
```

### Q22: 如何录制和回放？
**A:**
```bash
# 录制所有话题
rosbag record -a -O my_test.bag

# 录制特定话题
rosbag record /cmd_vel /odom /joint_states -O specific_test.bag

# 查看bag文件信息
rosbag info my_test.bag

# 回放
rosbag play my_test.bag

# 慢速回放
rosbag play -r 0.5 my_test.bag  # 0.5倍速
```

### Q23: 如何使用RViz可视化？
**A:**
```bash
# 启动RViz
rosrun rviz rviz

# 添加以下显示项：
# 1. Fixed Frame: 设置为 "map"
# 2. 添加 RobotModel
# 3. 添加 Map (话题: /map)
# 4. 添加 Path (话题: /move_base/NavfnROS/plan)
# 5. 添加 LaserScan (如果有激光)
# 6. 添加 TF

# 保存配置
File -> Save Config As -> nursing_home.rviz
```

## WSL相关

### Q24: 在WSL中Gazebo无法显示GUI？
**A:**
```bash
# 安装VcXsrv或X410作为X服务器

# 在WSL中设置DISPLAY
export DISPLAY=:0

# 添加到bashrc
echo "export DISPLAY=:0" >> ~/.bashrc

# 或使用无头模式
roslaunch nursing_home_sim nursing_home.launch gui:=false
```

### Q25: 如何从Windows访问WSL中的文件？
**A:**
```bash
# 在Windows文件资源管理器中输入：
\\wsl$\Ubuntu\home\your_username\catkin_ws\src\nursing_home_sim

# 或者在WSL中：
explorer.exe .
```

## 进阶问题

### Q26: 如何集成MoveIt!？
**A:**
```bash
# 安装MoveIt!
sudo apt install ros-noetic-moveit

# 启动MoveIt!配置助手
roslaunch moveit_setup_assistant setup_assistant.launch

# 加载URDF并按步骤配置
```

### Q27: 如何添加多个机器人？
**A:** 使用命名空间：
```xml
<!-- 修改 nursing_home.launch -->
<group ns="robot1">
  <param name="tf_prefix" value="robot1"/>
  <node name="spawn_robot" pkg="gazebo_ros" type="spawn_model"
        args="-urdf -param robot_description -model robot1 -x 0 -y 0 -z 0.2"/>
</group>

<group ns="robot2">
  <param name="tf_prefix" value="robot2"/>
  <node name="spawn_robot" pkg="gazebo_ros" type="spawn_model"
        args="-urdf -param robot_description -model robot2 -x 2 -y 0 -z 0.2"/>
</group>
```

### Q28: 如何连接真实机器人？
**A:**
1. 将Gazebo插件替换为真实硬件驱动
2. 修改URDF中的 `<plugin>` 部分
3. 使用相应的硬件接口包（如 `ros_control`）
4. 配置正确的串口/网络连接

## 获取帮助

如果以上FAQ没有解决你的问题：

1. **查看日志**
   ```bash
   cat ~/.ros/log/latest/rosout.log
   ```

2. **GitHub Issues**: 在项目GitHub页面提交issue

3. **ROS Answers**: https://answers.ros.org/

4. **Gazebo Forum**: https://answers.gazebosim.org/

5. **Stack Overflow**: 使用标签 `ros`, `gazebo`

---

**提示**: 90%的问题都是因为忘记 `source ~/catkin_ws/devel/setup.bash` 😊
