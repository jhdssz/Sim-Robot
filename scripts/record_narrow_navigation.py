#!/usr/bin/env python3
"""Collect actual Nav2 actions, trajectories, costmaps and Gazebo evidence."""
import argparse
import csv
import json
import math
from pathlib import Path
import time
from experiment_geometry import analyze, polygon, polygons_distance, footprint_at


def yaw(q):
    return math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))


def pose_row(p):
    return dict(x=p.position.x, y=p.position.y, yaw=yaw(p.orientation))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True)
    ap.add_argument('--world', required=True)
    ap.add_argument('--params', required=True)
    ap.add_argument('--goal', type=float, nargs=3, default=[4, 0, 0])
    ap.add_argument('--timeout', type=float, default=180)
    opts, ros_args = ap.parse_known_args()
    import rclpy
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.action import ActionClient
    from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
    from rclpy.time import Time
    from tf2_ros import Buffer, TransformListener, TransformException
    from tf2_msgs.msg import TFMessage
    from nav2_msgs.action import NavigateToPose, ComputePathToPose
    from nav_msgs.msg import Path as NavPath, OccupancyGrid
    from geometry_msgs.msg import PoseStamped
    from sensor_msgs.msg import LaserScan
    from ros_gz_interfaces.msg import Contacts
    from scan_self_filter import sensor_qos
    out = Path(opts.output)
    out.mkdir(parents=True, exist_ok=False)
    geometry = analyze(opts.world, opts.params)
    (out/'geometry.json').write_text(json.dumps(geometry, indent=2), encoding='utf-8')
    boxes, vertices = geometry['all_world_boxes'], geometry['footprint']
    obstacle_poly = polygon(geometry['obstacle'])
    rows, truth, events, checks = [], [], [], []
    contact_messages, laser_hits = 0, 0
    summary = dict(source='live ROS/Gazebo subscriptions', goal=opts.goal, status='INCOMPLETE')

    def append(name, obj):
        with (out/name).open('a', encoding='utf-8') as f:
            f.write(json.dumps(obj)+'\n')

    def metrics(row):
        fp = footprint_at(row['x'], row['y'], row['yaw'], vertices)
        row['footprint_clearance_m'] = min(polygons_distance(fp, polygon(b)) for b in boxes)
        row['slit_footprint_overlap'] = polygons_distance(fp, geometry['slit_roi']) == 0
        row['center_in_slit'] = min(v[0] for v in geometry['slit_roi']) <= row['x'] <= max(v[0] for v in geometry['slit_roi']) and min(v[1] for v in geometry['slit_roi']) <= row['y'] <= max(v[1] for v in geometry['slit_roi'])
        return row

    rclpy.init(args=ros_args)
    node = Node('narrow_navigation_recorder', parameter_overrides=[Parameter('use_sim_time', value=True)])
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    started, active_goal = time.monotonic(), None

    def sample():
        try:
            t = buffer.lookup_transform('map', 'base_link', Time())
            row = metrics(dict(wall_s=time.monotonic()-started, stamp_sec=t.header.stamp.sec,
                stamp_nanosec=t.header.stamp.nanosec, x=t.transform.translation.x,
                y=t.transform.translation.y, yaw=yaw(t.transform.rotation)))
            row['sim_age_s'] = node.get_clock().now().nanoseconds/1e9-(row['stamp_sec']+row['stamp_nanosec']/1e9)
            rows.append(row)
            append('trajectory_map.jsonl', row)
        except TransformException:
            pass

    def ground_truth(msg):
        append('ground_truth_tf.jsonl', dict(transforms=[dict(parent=t.header.frame_id, child=t.child_frame_id,
            x=t.transform.translation.x, y=t.transform.translation.y, z=t.transform.translation.z,
            yaw=yaw(t.transform.rotation), stamp_sec=t.header.stamp.sec,
            stamp_nanosec=t.header.stamp.nanosec) for t in msg.transforms]))
        for t in msg.transforms:
            if t.child_frame_id.split('::')[-1] != 'dual_arm_robot' or t.header.frame_id not in ('world','nursing_home','/world/nursing_home'):
                continue
            row = metrics(dict(wall_s=time.monotonic()-started, stamp_sec=t.header.stamp.sec,
                stamp_nanosec=t.header.stamp.nanosec, x=t.transform.translation.x,
                y=t.transform.translation.y, yaw=yaw(t.transform.rotation)))
            truth.append(row)
            append('trajectory_gazebo.jsonl', row)

    def contacts(msg):
        nonlocal contact_messages
        contact_messages += 1
        for c in msg.contacts:
            names = [c.collision1.name, c.collision2.name]
            if any('ground_plane' in n or 'corridor_floor' in n for n in names):
                continue
            event = dict(wall_s=time.monotonic()-started, collision_names=names,
                kind='SELF_CONTACT' if all('dual_arm_robot' in n for n in names) else 'ENVIRONMENT_OR_UNKNOWN')
            events.append(event)
            append('contacts.jsonl', event)

    def plan_callback(msg):
        append('plans.jsonl', dict(wall_s=time.monotonic()-started, frame=msg.header.frame_id,
            poses=[pose_row(p.pose) for p in msg.poses]))

    def costmap(msg, topic):
        record = dict(wall_s=time.monotonic()-started, topic=topic, frame=msg.header.frame_id,
            stamp_sec=msg.header.stamp.sec, stamp_nanosec=msg.header.stamp.nanosec,
            resolution=msg.info.resolution, width=msg.info.width, height=msg.info.height,
            origin=pose_row(msg.info.origin), data=list(msg.data))
        append('costmaps.jsonl', record)
        try:
            t = None if msg.header.frame_id == 'map' else buffer.lookup_transform(msg.header.frame_id, 'map', Time())
            values = []
            for u in (-.75, -.25, .25, .75):
                for v in (-.6, 0, .6):
                    x = geometry['obstacle']['pose'][0]+u*geometry['obstacle']['size'][0]/2
                    y = geometry['obstacle']['pose'][1]+v*geometry['obstacle']['size'][1]/2
                    xx, yy = x, y
                    if t:
                        a = yaw(t.transform.rotation)
                        xx = t.transform.translation.x+math.cos(a)*x-math.sin(a)*y
                        yy = t.transform.translation.y+math.sin(a)*x+math.cos(a)*y
                    a = -yaw(msg.info.origin.orientation)
                    dx, dy = xx-msg.info.origin.position.x, yy-msg.info.origin.position.y
                    ix = math.floor((math.cos(a)*dx-math.sin(a)*dy)/msg.info.resolution)
                    iy = math.floor((math.sin(a)*dx+math.cos(a)*dy)/msg.info.resolution)
                    if 0 <= ix < msg.info.width and 0 <= iy < msg.info.height:
                        values.append(int(msg.data[iy*msg.info.width+ix]))
            check = dict(wall_s=record['wall_s'], topic=topic, obstacle_interior_values=values,
                lethal_samples=sum(v == 100 for v in values), known_free_samples=sum(v == 0 for v in values))
            checks.append(check)
            append('costmap_checks.jsonl', check)
        except TransformException:
            pass

    def scan_callback(msg):
        nonlocal laser_hits
        try:
            t = buffer.lookup_transform('map', msg.header.frame_id, Time.from_msg(msg.header.stamp))
        except TransformException:
            return
        a, hits = yaw(t.transform.rotation), []
        for i, r in enumerate(msg.ranges):
            if not math.isfinite(r) or not msg.range_min <= r <= msg.range_max:
                continue
            theta = msg.angle_min+i*msg.angle_increment+a
            point = (t.transform.translation.x+r*math.cos(theta), t.transform.translation.y+r*math.sin(theta))
            if polygons_distance([point], obstacle_poly) <= .075:
                hits.append(dict(index=i, range_m=r, endpoint_map=point))
        if hits:
            laser_hits += len(hits)
            append('obstacle_scan_hits.jsonl', dict(stamp_sec=msg.header.stamp.sec, stamp_nanosec=msg.header.stamp.nanosec, hits=hits))

    transient = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE)
    subscriptions = [node.create_subscription(TFMessage, '/experiment/ground_truth', ground_truth, sensor_qos()),
        node.create_subscription(Contacts, '/experiment/contacts', contacts, sensor_qos()),
        node.create_subscription(NavPath, '/plan', plan_callback, 10),
        node.create_subscription(LaserScan, '/scan_filtered', scan_callback, sensor_qos())]
    for topic in ['/map', '/local_costmap/costmap', '/global_costmap/costmap']:
        subscriptions.append(node.create_subscription(OccupancyGrid, topic, lambda m,k=topic: costmap(m,k), transient))
    timer = node.create_timer(.1, sample)
    nav = ActionClient(node, NavigateToPose, 'navigate_to_pose')
    planner = ActionClient(node, ComputePathToPose, 'compute_path_to_pose')

    def wait(future, seconds):
        deadline = time.monotonic()+seconds
        while rclpy.ok() and not future.done() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.1)
        if not future.done():
            raise TimeoutError('ROS future timed out')
        return future.result()

    def stamped_goal():
        p = PoseStamped()
        p.header.frame_id = 'map'
        p.header.stamp = node.get_clock().now().to_msg()
        p.pose.position.x, p.pose.position.y = opts.goal[:2]
        p.pose.orientation.z, p.pose.orientation.w = math.sin(opts.goal[2]/2), math.cos(opts.goal[2]/2)
        return p

    try:
        deadline = time.monotonic()+30
        while not rows and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.1)
        if not rows or rows[-1]['sim_age_s'] > 1:
            raise RuntimeError('Missing or stale map->base_link TF')
        if math.hypot(rows[-1]['x']-geometry['start'][0], rows[-1]['y']-geometry['start'][1]) > .25:
            raise RuntimeError('Restart simulation at (-2,0) for each repetition')
        settle_until = time.monotonic()+8
        while time.monotonic() < settle_until:
            rclpy.spin_once(node, timeout_sec=.1)
        summary['start_map'] = rows[-1]
        if not planner.wait_for_server(timeout_sec=20) or not nav.wait_for_server(timeout_sec=20):
            raise RuntimeError('Nav2 action server unavailable')
        goal = ComputePathToPose.Goal()
        goal.goal, goal.planner_id, goal.use_start = stamped_goal(), 'GridBased', False
        t0 = time.monotonic()
        handle = wait(planner.send_goal_async(goal), 20)
        summary['planning_accepted'] = handle.accepted
        if not handle.accepted:
            raise RuntimeError('Planner rejected goal')
        result = wait(handle.get_result_async(), 30)
        summary.update(planning_wall_s=time.monotonic()-t0, planning_action_status=result.status,
            planning_time_s=result.result.planning_time.sec+result.result.planning_time.nanosec/1e9,
            planning_error_code=getattr(result.result, 'error_code', None))
        plan_callback(result.result.path)
        if result.status != 4:
            raise RuntimeError('Initial global plan failed')
        if result.result.path.header.frame_id == 'map':
            summary['initial_path_footprint_clearance_m'] = min((metrics(pose_row(p.pose))['footprint_clearance_m'] for p in result.result.path.poses), default=None)
        goal = NavigateToPose.Goal()
        goal.pose = stamped_goal()
        t0 = time.monotonic()
        active_goal = wait(nav.send_goal_async(goal), 20)
        summary['navigation_accepted'] = active_goal.accepted
        if not active_goal.accepted:
            raise RuntimeError('Navigation rejected goal')
        result = wait(active_goal.get_result_async(), opts.timeout)
        summary.update(navigation_action_status=result.status, navigation_wall_s=time.monotonic()-t0,
            navigation_error_code=getattr(result.result, 'error_code', None),
            navigation_error_msg=getattr(result.result, 'error_msg', None))
        for _ in range(5):
            rclpy.spin_once(node, timeout_sec=.1)
        summary['status'] = 'ACTION_SUCCEEDED' if result.status == 4 else 'ACTION_FAILED'
    except (Exception, KeyboardInterrupt) as error:
        summary['error'] = str(error) or type(error).__name__
        if active_goal and active_goal.accepted:
            try:
                wait(active_goal.cancel_goal_async(), 5)
                summary['cancel_result_status'] = wait(active_goal.get_result_async(), 10).status
            except Exception as e:
                summary['cancel_error'] = str(e)
    finally:
        summary['elapsed_wall_s'] = time.monotonic()-started
        for label, data in [('map_estimate', rows), ('gazebo_model', truth)]:
            summary[label] = None if not data else dict(samples=len(data), final=data[-1],
                minimum_sampled_footprint_clearance_m=min(r['footprint_clearance_m'] for r in data),
                slit_approach_observed=any(r['slit_footprint_overlap'] for r in data), center_in_slit=any(r['center_in_slit'] for r in data),
                position_error_m=math.hypot(data[-1]['x']-opts.goal[0], data[-1]['y']-opts.goal[1]),
                yaw_error_rad=abs(math.atan2(math.sin(data[-1]['yaw']-opts.goal[2]), math.cos(data[-1]['yaw']-opts.goal[2]))))
        summary.update(contact_messages=contact_messages, nonfloor_contact_events=len(events), self_contact_events=sum(e['kind']=='SELF_CONTACT' for e in events),
            collision='CONTACT_OBSERVED' if any(e['kind']!='SELF_CONTACT' for e in events) else ('NO_NONFLOOR_CONTACT_OBSERVED' if contact_messages else 'UNKNOWN'),
            filtered_scan_endpoints_near_added_obstacle=laser_hits,
            static_map_obstacle_checks=[c for c in checks if c['topic'] == '/map'],
            local_obstacle_lethal_observed=any(c['topic'] == '/local_costmap/costmap' and c['lethal_samples'] > 0 for c in checks),
            global_obstacle_lethal_observed=any(c['topic'] == '/global_costmap/costmap' and c['lethal_samples'] > 0 for c in checks),
            safe_detour_verdict='REQUIRES_REVIEW: action, trajectory, contacts, costmap and scan evidence must agree',
            limitations=['Sampled 2D configured footprint clearance is not a continuous or full 3D collision proof.',
                'Missing Gazebo ground truth/contact streams remain UNKNOWN; zero observed contacts is not proof.',
                'Model pose assumes base_link identity as in current SDF. Fixed home arms required.',
                'New static-map region must be free to attribute lethal marking to online sensing.'])
        for label, data in [('trajectory_map', rows), ('trajectory_gazebo', truth)]:
            if data:
                with (out/(label+'.csv')).open('w', newline='', encoding='utf-8') as f:
                    w = csv.DictWriter(f, fieldnames=list(data[0]))
                    w.writeheader()
                    w.writerows(data)
        if rows or truth:
            def point(x,y): return (80+(x+2)*100, 500-(y+3)*100)
            svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><rect width="800" height="600" fill="white"/>']
            for b in boxes:
                pts = ' '.join(f'{x},{y}' for x,y in (point(*v) for v in polygon(b)))
                svg.append(f'<polygon points="{pts}" fill="lightgray" stroke="black"/>')
            for data, color in [(rows,'blue'), (truth,'green')]:
                pts = ' '.join(f'{x},{y}' for x,y in (point(r['x'],r['y']) for r in data))
                svg.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
            svg.append('<text x="20" y="25">Observed: blue=map TF; green=Gazebo model</text></svg>')
            (out/'trajectory.svg').write_text(''.join(svg), encoding='utf-8')
        (out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        (out/'report.md').write_text('# Actual Nav2 run\n\n```json\n'+json.dumps(summary, indent=2)+'\n```\n', encoding='utf-8')
        print(json.dumps(summary, indent=2))
        node.destroy_node()
        rclpy.try_shutdown()
    return 0 if summary.get('navigation_action_status') == 4 else 1


if __name__ == '__main__':
    raise SystemExit(main())
