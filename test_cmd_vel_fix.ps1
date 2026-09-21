# 验证 /cmd_vel 单向 bridge 修复的 PowerShell 脚本

Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证 /cmd_vel 单向 bridge 修复" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "步骤 1: 重新构建..." -ForegroundColor Yellow
Set-Location D:\Sim-Robot
colcon build --packages-select nursing_home_sim

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ 构建失败" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 构建成功" -ForegroundColor Green

Write-Host ""
Write-Host "步骤 2: 请在新终端启动仿真..." -ForegroundColor Yellow
Write-Host "cd D:\Sim-Robot" -ForegroundColor White
Write-Host ". .\install\setup.ps1" -ForegroundColor White
Write-Host "ros2 launch nursing_home_sim nursing_home.launch.py" -ForegroundColor White
Write-Host ""
Write-Host "启动后等待 15 秒，然后按任意键继续验证..." -ForegroundColor Yellow
pause

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证 1: 记录初始位置" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "查询机器人初始 pose..." -ForegroundColor White

$initialPose = gz model -m dual_arm_robot --pose 2>&1
Write-Host "初始位置：" -ForegroundColor Green
Write-Host $initialPose
Write-Host ""

# 提取坐标（简化处理）
if ($initialPose -match "x: ([-0-9.]+)") {
    $initialX = [double]$matches[1]
    Write-Host "初始 X: $initialX" -ForegroundColor White
}
if ($initialPose -match "y: ([-0-9.]+)") {
    $initialY = [double]$matches[1]
    Write-Host "初始 Y: $initialY" -ForegroundColor White
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证 2: 等待 10 秒观察位置变化" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "等待中..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "10 秒后查询机器人 pose..." -ForegroundColor White
$finalPose = gz model -m dual_arm_robot --pose 2>&1
Write-Host "最终位置：" -ForegroundColor Green
Write-Host $finalPose
Write-Host ""

# 提取最终坐标
if ($finalPose -match "x: ([-0-9.]+)") {
    $finalX = [double]$matches[1]
    Write-Host "最终 X: $finalX" -ForegroundColor White
}
if ($finalPose -match "y: ([-0-9.]+)") {
    $finalY = [double]$matches[1]
    Write-Host "最终 Y: $finalY" -ForegroundColor White
}

# 计算位置变化
$deltaX = [Math]::Abs($finalX - $initialX)
$deltaY = [Math]::Abs($finalY - $initialY)

Write-Host ""
Write-Host "位置变化：" -ForegroundColor Yellow
Write-Host "ΔX: $deltaX" -ForegroundColor White
Write-Host "ΔY: $deltaY" -ForegroundColor White

# 检查位置是否稳定（容差 0.01m）
if ($deltaX -lt 0.01 -and $deltaY -lt 0.01) {
    Write-Host "✓ 机器人位置稳定，没有意外移动" -ForegroundColor Green
} else {
    Write-Host "✗ 警告：机器人位置发生变化！" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证 3: 检查 /cmd_vel 话题内容" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "监听 /cmd_vel 5 秒..." -ForegroundColor Yellow
Write-Host "如果看到持续的非零速度值，说明有问题" -ForegroundColor White

$job = Start-Job -ScriptBlock { ros2 topic echo /cmd_vel 2>&1 | Select-Object -First 20 }
Start-Sleep -Seconds 5
$cmdVelOutput = Receive-Job $job
Stop-Job $job
Remove-Job $job

if ($cmdVelOutput) {
    Write-Host "检测到的 /cmd_vel 内容：" -ForegroundColor Yellow
    Write-Host $cmdVelOutput

    if ($cmdVelOutput -match "linear:.*x: 0\.2" -or $cmdVelOutput -match "linear:.*x: [1-9]") {
        Write-Host "✗ 警告：检测到非零速度命令！" -ForegroundColor Red
    } else {
        Write-Host "✓ 未检测到持续的非零速度命令" -ForegroundColor Green
    }
} else {
    Write-Host "✓ /cmd_vel 没有数据（正常，无人发布命令）" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证 4: 检查 /cmd_vel 话题信息" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

$topicInfo = ros2 topic info /cmd_vel -v 2>&1
Write-Host $topicInfo

# 检查 ros_gz_bridge 是否只作为 subscriber
if ($topicInfo -match "ros_gz_bridge.*Subscription count: [1-9]") {
    Write-Host "✓ ros_gz_bridge 作为 Subscriber（ROS -> GZ）" -ForegroundColor Green
} else {
    Write-Host "⚠ 请检查 ros_gz_bridge 的角色" -ForegroundColor Yellow
}

if ($topicInfo -match "ros_gz_bridge.*Publication count: [1-9]") {
    Write-Host "✗ 警告：ros_gz_bridge 仍在发布到 ROS /cmd_vel！" -ForegroundColor Red
} else {
    Write-Host "✓ ros_gz_bridge 不再发布到 ROS /cmd_vel" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "验证总结" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "请确认：" -ForegroundColor Yellow
Write-Host "□ 机器人位置没有变化（ΔX 和 ΔY < 0.01m）" -ForegroundColor White
Write-Host "□ /cmd_vel 话题没有持续的非零速度命令" -ForegroundColor White
Write-Host "□ ros2 topic info 显示 ros_gz_bridge 只作为 Subscriber，不是 Publisher" -ForegroundColor White
Write-Host "□ launch 日志显示 'Creating ROS->GZ Bridge: /cmd_vel'（单向）" -ForegroundColor White
Write-Host ""

if ($deltaX -lt 0.01 -and $deltaY -lt 0.01) {
    Write-Host "✅ 修复验证通过！机器人不再意外移动。" -ForegroundColor Green
} else {
    Write-Host "❌ 仍然检测到问题，需要进一步排查。" -ForegroundColor Red
}

Write-Host ""
Write-Host "测试完成！" -ForegroundColor Cyan
