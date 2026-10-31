#!/usr/bin/env bash
# Offline -> build -> real simulation; no fabricated ROS inputs, no Git writes.
set -Eeuo pipefail
PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-offline}"
RESULTS="${2:-$HOME/ros2_experiment_results/$(date +%Y%m%d_%H%M%S)}"
WORKSPACE="${ROS_WORKSPACE:-$HOME/ros2_ws}"
mkdir -p "$RESULTS"
RESULTS="$(cd "$RESULTS" && pwd)"
exec > >(tee -a "$RESULTS/terminal.log") 2>&1
printf 'Project=%s\nWorkspace=%s\nMode=%s\nUTC=%s\n' "$PROJECT" "$WORKSPACE" "$MODE" "$(date -u --iso-8601=seconds)"
git -C "$PROJECT" status --short
git -C "$PROJECT" rev-parse HEAD

offline() {
  python3 "$PROJECT/scripts/run_scan_tests_detailed.py" --output "$RESULTS/offline"
  python3 "$PROJECT/tests/test_model_scan_clearance.py"
  python3 "$PROJECT/scripts/experiment_geometry.py" --output "$RESULTS/geometry.json"
}
preflight() {
  test -r /opt/ros/jazzy/setup.bash
  set +u
  source /opt/ros/jazzy/setup.bash
  set -u
  command -v ros2
  command -v gz
  command -v colcon
  gz sim --versions
  for pkg in rclpy sensor_msgs nav2_msgs nav2_bringup ros_gz_sim ros_gz_bridge ros_gz_interfaces tf2_ros; do
    ros2 pkg prefix "$pkg"
  done
  python3 -c 'import rclpy, yaml; from nav2_msgs.action import NavigateToPose, ComputePathToPose; from ros_gz_interfaces.msg import Contacts'
  ros2 interface show nav2_msgs/action/NavigateToPose
  ros2 interface show nav2_msgs/action/ComputePathToPose
}
build() {
  offline
  preflight
  mkdir -p "$WORKSPACE"
  (cd "$WORKSPACE" && colcon build --base-paths "$PROJECT" --packages-select nursing_home_sim --symlink-install)
  (cd "$WORKSPACE" && colcon test --packages-select nursing_home_sim --event-handlers console_direct+)
  (cd "$WORKSPACE" && colcon test-result --verbose)
}

PIDS=()
cleanup() {
  # Only signal process groups created by this script; never pkill unrelated work.
  trap - EXIT INT TERM
  for ((i=${#PIDS[@]}-1;i>=0;i--)); do kill -INT -- "-${PIDS[i]}" 2>/dev/null || true; done
  sleep 3
  for ((i=${#PIDS[@]}-1;i>=0;i--)); do kill -TERM -- "-${PIDS[i]}" 2>/dev/null || true; done
  for pid in "${PIDS[@]}"; do wait "$pid" 2>/dev/null || true; done
}
start_group() {
  local logfile="$1"; shift
  setsid "$@" >"$logfile" 2>&1 &
  PIDS+=("$!")
}

live() {
  local variant="$1" run="$RESULTS"
  preflight
  set +u
  source "$WORKSPACE/install/setup.bash"
  set -u
  local share params
  share="$(ros2 pkg prefix --share nursing_home_sim)"
  params="$share/config/nav2_narrow.yaml"
  if [[ "$variant" == raw ]]; then params="$share/config/nav2_narrow_raw.yaml"; fi
  # Refuse accidentally testing stale installed scene/config.
  for f in worlds/nursing_home_narrow.world models/dual_arm_robot/experiment.sdf config/nav2_narrow.yaml config/nav2_narrow_raw.yaml; do
    cmp "$PROJECT/$f" "$share/$f"
  done
  # Fail on another simulation: comparisons and action results must have one provenance.
  if ros2 node list | grep -Eq '^/(scan_self_filter|controller_server|robot_state_publisher)$'; then
    echo 'Another simulation/Nav2 instance is active. Stop it before starting a reproducible run.'
    return 1
  fi
  trap cleanup EXIT INT TERM
  start_group "$run/gazebo.log" ros2 launch nursing_home_sim nursing_home.launch.py \
    world:="$share/worlds/nursing_home_narrow.world" robot_sdf:="$share/models/dual_arm_robot/experiment.sdf" \
    navigation:=false task_controllers:=false
  start_group "$run/experiment_bridge.log" ros2 run ros_gz_bridge parameter_bridge \
    --ros-args -p config_file:="$share/config/experiment_bridge.yaml" -p use_sim_time:=true
  timeout 90 ros2 topic echo /scan sensor_msgs/msg/LaserScan --once --field header
  timeout 30 ros2 topic echo /scan_filtered sensor_msgs/msg/LaserScan --once --field header
  ros2 topic info -v /scan > "$run/qos_scan.txt"
  ros2 topic info -v /scan_filtered > "$run/qos_filtered.txt"
  gz topic -l > "$run/gazebo_topics.txt"
  ros2 topic list -t > "$run/ros_topics.txt"
  start_group "$run/rosbag.log" ros2 bag record --include-hidden-topics -o "$run/bag" \
    /clock /scan /scan_filtered /tf /tf_static /odom /joint_states /map /plan \
    /local_costmap/costmap /global_costmap/costmap /local_costmap/published_footprint \
    /global_costmap/published_footprint /cmd_vel /cmd_vel_smoothed \
    /experiment/ground_truth /experiment/contacts \
    /navigate_to_pose/_action/status /navigate_to_pose/_action/feedback
  # This scene has a different front distance; require exact preservation, not the old 0.50 m fixture.
  local scan_rc=0
  python3 "$PROJECT/scripts/compare_scan_filter.py" --pairs 20 --timeout 90 --no-front-fixture \
    --output "$run/live_scan" --ros-args -p use_sim_time:=true || scan_rc=$?
  printf '%s\n' "$scan_rc" > "$run/scan_exit_code.txt"
  if [[ "$scan_rc" -eq 1 ]]; then echo 'Scan mismatch/runtime error: stop navigation.'; return 1; fi
  if [[ "$scan_rc" -eq 2 ]]; then echo 'Scan evidence incomplete; Nav2 result will remain a separate experiment.'; fi
  if [[ "$variant" == scan ]]; then return "$scan_rc"; fi
  start_group "$run/nav2.log" ros2 launch nursing_home_sim navigation.launch.py params_file:="$params"
  local nav_rc=0
  python3 "$PROJECT/scripts/record_narrow_navigation.py" --world "$share/worlds/nursing_home_narrow.world" \
    --params "$params" --goal 4 0 0 --timeout 180 --output "$run/navigation" --ros-args -p use_sim_time:=true || nav_rc=$?
  ros2 param dump /controller_server > "$run/controller_runtime.yaml"
  ros2 param dump /local_costmap/local_costmap > "$run/local_costmap_runtime.yaml"
  ros2 param dump /global_costmap/global_costmap > "$run/global_costmap_runtime.yaml"
  ros2 param dump /amcl > "$run/amcl_runtime.yaml"
  return "$nav_rc"
}

case "$MODE" in
  offline) offline ;;
  build) build ;;
  scan) live scan ;;
  filtered) live filtered ;;
  raw) live raw ;;
  *) echo 'Usage: bash scripts/run_repro_experiment.sh {offline|build|scan|filtered|raw} [unique-results-dir]'; exit 2 ;;
esac
