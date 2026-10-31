#!/usr/bin/env python3
"""Observe the user's navigation goal without sending, replacing or cancelling goals."""
import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time


def angle(q):
    return math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--duration', type=float, default=180)
    parser.add_argument('--bag', action='store_true')
    opts, ros_args = parser.parse_known_args()
    if opts.duration <= 0:
        parser.error('duration must be positive')
    import rclpy
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
    from rclpy.time import Time
    from tf2_ros import Buffer, TransformListener, TransformException
    from nav2_msgs.action import NavigateToPose, Spin
    from action_msgs.msg import GoalStatusArray
    from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Twist, TwistStamped
    from nav_msgs.msg import Path as NavPath, Odometry
    from rcl_interfaces.msg import Log
    from rosidl_runtime_py.convert import message_to_ordereddict
    out = Path(opts.output)
    out.mkdir(parents=True, exist_ok=False)
    rclpy.init(args=ros_args)
    node = Node('passive_nav_diagnostics', parameter_overrides=[Parameter('use_sim_time', value=True)])
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    counts, samples, jumps, recoveries = Counter(), [], [], []
    started = time.monotonic()
    bag = None
    bag_log = None

    def write(name, record):
        with (out/name).open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False)+'\n')

    def receive(msg, topic):
        counts[topic] += 1
        write('messages.jsonl', dict(wall_s=time.monotonic()-started,
            topic=topic, message=message_to_ordereddict(msg)))
        if topic == '/navigate_to_pose/_action/feedback':
            recoveries.append(msg.feedback.number_of_recoveries)

    best_effort = QoSProfile(depth=30, reliability=ReliabilityPolicy.BEST_EFFORT)
    transient = QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL,
        reliability=ReliabilityPolicy.RELIABLE)
    specs = [('/plan', NavPath), ('/local_plan', NavPath), ('/amcl_pose', PoseWithCovarianceStamped),
        ('/odom', Odometry), ('/goal_pose', PoseStamped), ('/rosout', Log),
        ('/navigate_to_pose/_action/feedback', NavigateToPose.Impl.FeedbackMessage),
        ('/spin/_action/feedback', Spin.Impl.FeedbackMessage)]
    subscriptions = [node.create_subscription(kind, topic, lambda m,k=topic: receive(m,k), best_effort)
        for topic, kind in specs]
    for topic in ['/navigate_to_pose/_action/status', '/spin/_action/status']:
        subscriptions.append(node.create_subscription(GoalStatusArray, topic,
            lambda m,k=topic: receive(m,k), transient))
    # Discover Twist vs TwistStamped rather than assuming a distro's cmd_vel setting.
    velocity_subs = {}

    def discover_velocities():
        types = dict(node.get_topic_names_and_types())
        for topic in ['/cmd_vel', '/cmd_vel_nav', '/cmd_vel_smoothed']:
            if topic in velocity_subs or topic not in types:
                continue
            kind = TwistStamped if 'geometry_msgs/msg/TwistStamped' in types[topic] else Twist
            velocity_subs[topic] = node.create_subscription(kind, topic,
                lambda m,k=topic: receive(m,k), best_effort)
        write('publishers.jsonl', dict(wall_s=time.monotonic()-started,
            topics={topic:[dict(node=e.node_name, namespace=e.node_namespace, qos=str(e.qos_profile))
                for e in node.get_publishers_info_by_topic(topic)]
                for topic in ['/cmd_vel','/cmd_vel_smoothed','/odom','/scan','/scan_filtered']}))

    def sample():
        row = dict(wall_s=time.monotonic()-started, transforms={})
        for parent, child in [('map','base_link'), ('odom','base_link'), ('map','odom')]:
            try:
                t = buffer.lookup_transform(parent, child, Time())
                row['transforms'][parent+'->'+child] = dict(x=t.transform.translation.x,
                    y=t.transform.translation.y, yaw=angle(t.transform.rotation),
                    stamp_s=t.header.stamp.sec+t.header.stamp.nanosec/1e9)
            except TransformException:
                pass
        if samples:
            for name, current in row['transforms'].items():
                previous = samples[-1]['transforms'].get(name)
                if previous:
                    displacement = math.hypot(current['x']-previous['x'],current['y']-previous['y'])
                    rotation = abs(math.atan2(math.sin(current['yaw']-previous['yaw']), math.cos(current['yaw']-previous['yaw'])))
                    if displacement > .5 or rotation > .5:
                        jumps.append(dict(wall_s=row['wall_s'], transform=name,
                            displacement_m=displacement, rotation_rad=rotation))
        samples.append(row)
        write('transforms.jsonl', row)

    timers = [node.create_timer(.1, sample), node.create_timer(2, discover_velocities)]
    try:
        for index, command in enumerate([
            ['ros2','action','info','/navigate_to_pose'], ['ros2','action','info','/spin'],
            ['ros2','param','dump','/controller_server'], ['ros2','param','dump','/bt_navigator'],
            ['ros2','param','dump','/amcl']]):
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=5)
                (out/f'graph-{index}.txt').write_text(' '.join(command)+'\n'+result.stdout+result.stderr, encoding='utf-8')
            except Exception as e:
                (out/f'graph-{index}.txt').write_text(str(e), encoding='utf-8')
        if opts.bag:
            topics = ['/scan','/scan_filtered','/tf','/tf_static','/odom','/amcl_pose','/map',
                '/plan','/local_plan','/cmd_vel','/cmd_vel_nav','/cmd_vel_smoothed','/goal_pose',
                '/local_costmap/costmap','/global_costmap/costmap','/rosout','/behavior_tree_log',
                '/navigate_to_pose/_action/status','/navigate_to_pose/_action/feedback',
                '/spin/_action/status','/spin/_action/feedback','/clock',
                '/experiment/ground_truth','/experiment/contacts']
            bag_log = (out/'rosbag.log').open('w', encoding='utf-8')
            bag = subprocess.Popen(['ros2','bag','record','--include-hidden-topics','-o',str(out/'bag'),*topics],
                stdout=bag_log, stderr=subprocess.STDOUT, start_new_session=True)
        print('PASSIVE recorder ready. Send your door goal once in RViz; this recorder sends no goal.', flush=True)
        # Duration starts after setup, giving the operator the full requested interval.
        deadline = time.monotonic()+opts.duration
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.1)
    except KeyboardInterrupt:
        pass
    finally:
        if bag and bag.poll() is None:
            os.killpg(bag.pid, signal.SIGINT)
            try:
                bag.wait(timeout=10)
            except subprocess.TimeoutExpired:
                bag.terminate()
                try:
                    bag.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    bag.kill()
                    bag.wait()
        if bag_log:
            bag_log.close()
        summary = dict(passive=True, goals_sent=0, goals_cancelled=0, counts=dict(counts),
            elapsed_wall_s=time.monotonic()-started, transform_samples=len(samples),
            transform_jump_candidates=jumps,
            maximum_reported_navigation_recoveries=max(recoveries) if recoveries else None,
            bag_exit_code=bag.returncode if bag else None,
            spin_feedback_messages=counts['/spin/_action/feedback'],
            conclusion='Cause of any loop requires comparison of plan, odom, map->odom, commands and recovery events.',
            limitations=['/goal_pose may not contain goals sent directly by the RViz Nav2 action panel.',
                'Save the actual clicked goal position/orientation or sender log; feedback does not reveal the requested target.',
                'Late-joining transient status includes older goals; correlate goal IDs and active time.',
                'Zero spin feedback or no log message does not prove no recovery occurred.',
                'TF jump candidates are observations, not proof of faulty localization.'])
        (out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        node.destroy_node()
        rclpy.try_shutdown()
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
