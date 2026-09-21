# 验证修复结果的 PowerShell 脚本

Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证修复结果" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "步骤 1: 重新构建包..." -ForegroundColor Yellow
Set-Location D:\Sim-Robot
colcon build --packages-select nursing_home_sim

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ 构建失败" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 构建成功" -ForegroundColor Green

Write-Host ""
Write-Host "步骤 2: Source 环境..." -ForegroundColor Yellow
& "D:\Sim-Robot\install\setup.ps1"

Write-Host ""
Write-Host "步骤 3: 启动仿真（后台运行）..." -ForegroundColor Yellow
Write-Host "请在新终端手动运行以下命令后按任意键继续：" -ForegroundColor Yellow
Write-Host "ros2 launch nursing_home_sim nursing_home.launch.py" -ForegroundColor White
pause

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证 1: 检查 collision_monitor" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "检查 collision_monitor 是否成功配置..."

$nodes = ros2 node list 2>$null
if ($nodes -match "collision_monitor") {
    Write-Host "✓ collision_monitor 节点存在" -ForegroundColor Green
} else {
    Write-Host "✗ collision_monitor 节点未找到" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证 2: 检查 /scan frame_id" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "检查 LaserScan 的 frame_id..."

$scanData = ros2 topic echo /scan --once 2>$null
$frameId = $scanData | Select-String -Pattern "frame_id:"
Write-Host $frameId
if ($frameId -match "laser_link") {
    Write-Host "✓ frame_id 正确: laser_link" -ForegroundColor Green
} else {
    Write-Host "✗ frame_id 不正确，期望: laser_link" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证 3: 检查 TF 树" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "检查 laser_link 是否在 TF 树中..."

$tfResult = ros2 run tf2_ros tf2_echo base_link laser_link 2>&1 | Select-Object -First 5
Write-Host $tfResult
if ($tfResult -match "Translation|At time") {
    Write-Host "✓ base_link -> laser_link transform 存在" -ForegroundColor Green
} else {
    Write-Host "✗ base_link -> laser_link transform 不存在" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证 4: 检查 Gazebo 话题" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "检查 Gazebo /scan 话题..."

$gzTopics = gz topic -l 2>$null
if ($gzTopics -match "/scan") {
    Write-Host "✓ Gazebo /scan 话题存在" -ForegroundColor Green

    Write-Host "检查话题详情..."
    gz topic -i -t /scan
} else {
    Write-Host "✗ Gazebo /scan 话题不存在" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证 5: 测试运动控制" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "发送速度命令..."

ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.0}}" 2>$null
Start-Sleep -Seconds 2

Write-Host "检查 odometry..."
$odomData = ros2 topic echo /odom --once 2>$null | Select-String -Pattern "position:" -Context 0,3
Write-Host $odomData

if ($odomData) {
    Write-Host "✓ 运动控制正常" -ForegroundColor Green
} else {
    Write-Host "✗ 无法读取 odometry" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证 6: 检查机器人可见性" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "请检查 Gazebo GUI："
Write-Host "1. 机器人是否可见" -ForegroundColor White
Write-Host "2. 位置是否正确: x=0.5, y=0, z=0.2" -ForegroundColor White
Write-Host "3. 所有部件是否显示正常（底盘、轮子、LiDAR、手臂）" -ForegroundColor White

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证完成摘要" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "请确认以下内容：" -ForegroundColor Yellow
Write-Host "□ collision_monitor 节点正常运行，无参数错误" -ForegroundColor White
Write-Host "□ /scan frame_id 为 'laser_link'" -ForegroundColor White
Write-Host "□ TF 树包含 base_link -> laser_link" -ForegroundColor White
Write-Host "□ AMCL 不再报 'timestamp is earlier' 错误" -ForegroundColor White
Write-Host "□ 机器人在 Gazebo 中可见" -ForegroundColor White
Write-Host "□ 运动控制正常工作" -ForegroundColor White
Write-Host ""
Write-Host "如果所有项目都正常，修复成功！" -ForegroundColor Green
