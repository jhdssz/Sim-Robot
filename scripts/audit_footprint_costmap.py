#!/usr/bin/env python3
"""Read-only current-footprint vs raw Costmap audit; never send motion or clear maps."""
import argparse
from collections import deque
import json
import math
from pathlib import Path
import time


def raster_line(a, b):
    x, y = a
    bx, by = b
    dx, dy = abs(bx-x), abs(by-y)
    sx, sy = 1 if x < bx else -1, 1 if y < by else -1
    error = dx-dy
    while True:
        yield x, y
        if (x, y) == (bx, by):
            break
        twice = 2*error
        if twice > -dy:
            error -= dy
            x += sx
        if twice < dx:
            error += dx
            y += sy


def boundary_audit(points, origin, resolution, width, height, data):
    """Approximate DWB edge rasterization; raw costs distinguish lethal from inflation."""
    if len(points) < 3 or resolution <= 0 or len(data) != width*height:
        raise ValueError('Invalid grid/polygon')
    ox, oy, angle = origin
    c, s = math.cos(-angle), math.sin(-angle)
    indices = []
    for x, y in points:
        dx, dy = x-ox, y-oy
        indices.append((math.floor((c*dx-s*dy)/resolution), math.floor((s*dx+c*dy)/resolution)))
    cells = set()
    for a, b in zip(indices, indices[1:]+indices[:1]):
        cells.update(raster_line(a, b))
    counts = dict(lethal_254=0, unknown_255=0, inscribed_253=0, graded_1_252=0, free_0=0, outside=0)
    blocked = []
    ca, sa = math.cos(angle), math.sin(angle)
    for x, y in sorted(cells):
        if not (0 <= x < width and 0 <= y < height):
            counts['outside'] += 1
            continue
        value = int(data[y*width+x])
        key = 'lethal_254' if value == 254 else 'unknown_255' if value == 255 else 'inscribed_253' if value == 253 else 'free_0' if value == 0 else 'graded_1_252'
        counts[key] += 1
        if value in (254,255):
            xx, yy = (x+.5)*resolution, (y+.5)*resolution
            blocked.append(dict(ix=x, iy=y, cost=value, center=[ox+ca*xx-sa*yy, oy+sa*xx+ca*yy]))
    return dict(counts=counts, blocked_cells=blocked,
        note='Approximate boundary raster; corner tie cells may differ from DWB LineIterator. Not a full future-trajectory test.')


def yaw(q):
    return math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))


def stamp(t):
    return t.sec+t.nanosec/1e9


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--snapshots', type=int, default=3)
    parser.add_argument('--timeout', type=float, default=20)
    parser.add_argument('--max-stamp-delta', type=float, default=.1)
    opts, args = parser.parse_known_args()
    if opts.snapshots < 1 or opts.timeout <= 0 or opts.max_stamp_delta < 0:
        parser.error('Invalid snapshot/time limits')
    import rclpy
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from nav2_msgs.msg import Costmap
    from geometry_msgs.msg import PolygonStamped
    from nav_msgs.msg import OccupancyGrid
    from rosidl_runtime_py.convert import message_to_ordereddict
    from tf2_ros import Buffer, TransformListener, TransformException
    from rclpy.time import Time
    from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
    out = Path(opts.output)
    out.mkdir(parents=True, exist_ok=False)
    rclpy.init(args=args)
    node = Node('footprint_costmap_audit', parameter_overrides=[Parameter('use_sim_time', value=True)])
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    footprints, grids, records = deque(maxlen=50), deque(maxlen=20), []
    static = [None]
    processed = set()
    sensor = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
    latch = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    subscriptions = [node.create_subscription(Costmap, '/local_costmap/costmap_raw', grids.append, sensor),
        node.create_subscription(PolygonStamped, '/local_costmap/published_footprint', footprints.append, sensor),
        node.create_subscription(OccupancyGrid, '/map', lambda m: static.__setitem__(0,m), latch)]

    def inspect():
        if not footprints:
            return
        for grid in list(grids):
            key = (grid.header.stamp.sec,grid.header.stamp.nanosec)
            if key in processed:
                continue
            candidates = [f for f in footprints if f.header.frame_id == grid.header.frame_id]
            if not candidates:
                continue
            footprint = min(candidates, key=lambda f: abs(stamp(f.header.stamp)-stamp(grid.header.stamp)))
            delta = abs(stamp(footprint.header.stamp)-stamp(grid.header.stamp))
            if delta > opts.max_stamp_delta:
                continue
            meta = grid.metadata
            result = boundary_audit([(v.x,v.y) for v in footprint.polygon.points],
                (meta.origin.position.x,meta.origin.position.y,yaw(meta.origin.orientation)),
                meta.resolution,meta.size_x,meta.size_y,grid.data)
            result.update(stamp=key, frame=grid.header.frame_id, footprint_stamp_delta_s=delta,
                costmap_update_time_s=stamp(meta.update_time), static_map_evidence=[])
            baseline = static[0]
            if baseline:
                try:
                    transform = None if baseline.header.frame_id == grid.header.frame_id else buffer.lookup_transform(
                        baseline.header.frame_id,grid.header.frame_id,Time.from_msg(grid.header.stamp))
                    for cell in result['blocked_cells']:
                        x,y = cell['center']
                        if transform:
                            a = yaw(transform.transform.rotation)
                            x,y = (transform.transform.translation.x+math.cos(a)*x-math.sin(a)*y,
                                transform.transform.translation.y+math.sin(a)*x+math.cos(a)*y)
                        a = -yaw(baseline.info.origin.orientation)
                        dx,dy = x-baseline.info.origin.position.x,y-baseline.info.origin.position.y
                        ix = math.floor((math.cos(a)*dx-math.sin(a)*dy)/baseline.info.resolution)
                        iy = math.floor((math.sin(a)*dx+math.cos(a)*dy)/baseline.info.resolution)
                        value = int(baseline.data[iy*baseline.info.width+ix]) if 0 <= ix < baseline.info.width and 0 <= iy < baseline.info.height else None
                        result['static_map_evidence'].append(dict(local_cell=[cell['ix'],cell['iy']],map_position=[x,y],static_occupancy=value))
                except TransformException as error:
                    result['static_map_error'] = str(error)
            number = len(records)+1
            (out/f'snapshot-{number}.json').write_text(json.dumps(dict(result=result,
                raw_costmap=message_to_ordereddict(grid),published_footprint=message_to_ordereddict(footprint),
                static_map=message_to_ordereddict(baseline) if baseline else None),indent=2),encoding='utf-8')
            records.append(result)
            processed.add(key)
            print(f"Snapshot {number}: {result['counts']}",flush=True)
            if len(records) >= opts.snapshots:
                break
    started = time.monotonic()
    try:
        while rclpy.ok() and time.monotonic()-started < opts.timeout and len(records) < opts.snapshots:
            rclpy.spin_once(node,timeout_sec=.1)
            inspect()
    except KeyboardInterrupt:
        pass
    finally:
        summary = dict(source='live raw Costmap + time-near published footprint', snapshots=records,
            complete=len(records)>=opts.snapshots, commands_sent=0, maps_cleared=0,
            interpretation='Current lethal-boundary cells support a start-pose collision explanation. No current lethal cell does not rule out future-pose rejection or earlier collisions.',
            source_limit='Static-free + local-lethal suggests observation data or stale cells; cannot by itself identify self echoes or prove the filter caused them.')
        (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        node.destroy_node()
        rclpy.try_shutdown()
    return 0 if summary['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
