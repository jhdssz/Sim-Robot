#!/usr/bin/env python3
"""Pair raw/filtered ROS scans by stamp; run before Nav2 with the robot at rest."""
import argparse
import csv
import json
from pathlib import Path
from collections import OrderedDict
import math
import time

from scan_self_filter import (
    angle_degrees, filter_scan, INPUT_TOPIC, OUTPUT_TOPIC,
    SELF_FILTER_SECTORS, self_echo_sector, sensor_qos,
)


def same_value(a, b):
    return a == b or (math.isnan(a) and math.isnan(b))


def inspect_pair(raw, filtered, front_target=.50, front_tolerance=.10):
    """Validate each sample and all metadata, preserving NaN values."""
    for field in ('header', 'angle_min', 'angle_max', 'angle_increment',
                  'time_increment', 'scan_time', 'range_min', 'range_max'):
        a, b = getattr(raw, field), getattr(filtered, field)
        equal = a == b if field == 'header' else same_value(a, b)
        if not equal:
            raise ValueError(f'Metadata changed: {field}')
    if len(raw.ranges) != len(filtered.ranges):
        raise ValueError('Range count changed')
    if len(raw.intensities) != len(filtered.intensities) or any(
            not same_value(a, b) for a, b in zip(raw.intensities, filtered.intensities)):
        raise ValueError('Intensity/index structure changed')
    expected = filter_scan(raw)
    for index, (a, b) in enumerate(zip(expected.ranges, filtered.ranges)):
        if not same_value(a, b):
            raise ValueError(f'Unexpected output at index {index}: expected {a}, got {b}')
    if not raw.ranges or not math.isfinite(raw.angle_min) or not math.isfinite(raw.angle_increment):
        raise ValueError('Empty scan or invalid angle metadata')
    angles = [angle_degrees(raw.angle_min, raw.angle_increment, i)
              for i in range(len(raw.ranges))]
    front = min(range(len(angles)), key=lambda i: abs(angles[i]))
    if abs(angles[front]) > math.degrees(abs(raw.angle_increment))*.51+1e-6:
        raise ValueError('Scan does not cover forward 0 degrees')
    front_raw, front_filtered = raw.ranges[front], filtered.ranges[front]
    if front_target is not None and (not math.isfinite(front_raw) or abs(front_raw-front_target)>front_tolerance):
        raise ValueError(f'Front raw={front_raw:.3f} does not match stationary desk fixture')
    if not same_value(front_raw, front_filtered):
        raise ValueError('Front desk return changed')
    counts = [0]*len(SELF_FILTER_SECTORS)
    for index, value in enumerate(raw.ranges):
        sector = self_echo_sector(angles[index], value)
        if sector is not None:
            counts[sector] += 1
            if filtered.ranges[index] != math.inf:
                raise ValueError(f'Self echo remains at index {index}')
    return counts, front_raw, front_filtered


def pair_evidence(raw, filtered):
    """Observed values only. Preserved returns are proxies, not object identities."""
    def valid(msg):
        return sum(math.isfinite(r) and msg.range_min <= r <= msg.range_max for r in msg.ranges)
    counts = [0]*len(SELF_FILTER_SECTORS)
    removed = []
    unchanged_valid = 0
    changed = []
    for i, (a,b) in enumerate(zip(raw.ranges, filtered.ranges)):
        angle = angle_degrees(raw.angle_min,raw.angle_increment,i)
        sector = self_echo_sector(angle,a)
        if not same_value(a,b):
            changed.append(i)
            if b == math.inf:
                removed.append(dict(index=i,angle_deg=angle,raw_distance=a,sector=sector))
                if sector is not None:
                    counts[sector] += 1
        elif math.isfinite(a) and raw.range_min <= a <= raw.range_max:
            unchanged_valid += 1
    def metadata(msg):
        return dict(stamp_sec=msg.header.stamp.sec, stamp_nanosec=msg.header.stamp.nanosec,
            frame_id=msg.header.frame_id, angle_min=msg.angle_min, angle_max=msg.angle_max,
            angle_increment=msg.angle_increment, time_increment=msg.time_increment,
            scan_time=msg.scan_time, range_min=msg.range_min, range_max=msg.range_max,
            intensities=list(msg.intensities))
    return dict(metadata_raw=metadata(raw),metadata_filtered=metadata(filtered),stamp_sec=raw.header.stamp.sec,stamp_nanosec=raw.header.stamp.nanosec,
                frame_id=raw.header.frame_id,points_raw=len(raw.ranges),points_filtered=len(filtered.ranges),
                valid_raw=valid(raw),valid_filtered=valid(filtered),sector_counts=counts,
                removed=removed,changed_indices=changed,unchanged_valid_returns=unchanged_valid,
                raw_ranges=list(raw.ranges),filtered_ranges=list(filtered.ranges),
                angle_min=raw.angle_min,angle_increment=raw.angle_increment,
                range_min=raw.range_min,range_max=raw.range_max)


def json_safe(value):
    if isinstance(value,float) and not math.isfinite(value):
        return str(value)
    if isinstance(value,dict):
        return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [json_safe(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pairs',type=int,default=20)
    parser.add_argument('--timeout',type=float,default=60)
    parser.add_argument('--front-target',type=float,default=.50)
    parser.add_argument('--front-tolerance',type=float,default=.10)
    parser.add_argument('--no-front-fixture',action='store_true',help='Validate arbitrary environment; no 0.50 m desk claim')
    parser.add_argument('--output',default='experiment_results/live_scan')
    options,ros_args=parser.parse_known_args()
    if options.pairs<=0 or options.timeout<=0 or options.front_tolerance<0:
        parser.error('invalid pairs/timeout/tolerance')
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import LaserScan
    out=Path(options.output); out.mkdir(parents=True,exist_ok=False)
    records=[]
    class ScanComparison(Node):
        def __init__(self):
            super().__init__('scan_filter_comparison')
            self.raw=OrderedDict(); self.filtered=OrderedDict()
            self.failure=None; self.evicted=[0,0]; self.received=[0,0]
            self.subs=[self.create_subscription(LaserScan,topic,lambda m,k=k:self.receive(m,k),sensor_qos())
                       for k,topic in enumerate((INPUT_TOPIC,OUTPUT_TOPIC))]
        def receive(self,msg,side):
            self.received[side]+=1
            key=(msg.header.stamp.sec,msg.header.stamp.nanosec,msg.header.frame_id)
            own,other=(self.raw,self.filtered) if side==0 else (self.filtered,self.raw)
            if key not in other:
                own[key]=msg
                while len(own)>100:
                    own.popitem(last=False); self.evicted[side]+=1
                return
            partner=other.pop(key)
            own.pop(key,None)
            raw,filtered=(msg,partner) if side==0 else (partner,msg)
            record=pair_evidence(raw,filtered)
            try:
                counts,front_raw,front_filtered=inspect_pair(raw,filtered,
                    None if options.no_front_fixture else options.front_target,options.front_tolerance)
                record.update(status='PASS',metadata_equal=True,front_raw=front_raw,front_filtered=front_filtered)
            except ValueError as e:
                record.update(status='FAIL',error=str(e),metadata_equal=raw.header==filtered.header and all(
                    same_value(getattr(raw,k),getattr(filtered,k)) for k in ('angle_min','angle_max','angle_increment','scan_time','time_increment','range_min','range_max')))
                self.failure=str(e)
            records.append(record)
            with (out/'pairs.jsonl').open('a',encoding='utf-8') as f:
                f.write(json.dumps(json_safe(record),ensure_ascii=False)+'\n')
            self.get_logger().info(f"Pair {len(records)}: {record['status']} sectors={record['sector_counts']} valid={record['valid_raw']}->{record['valid_filtered']}")
    rclpy.init(args=ros_args); node=ScanComparison(); started=time.monotonic()
    interrupted=False
    try:
        while rclpy.ok() and time.monotonic()-started<options.timeout and not node.failure and len(records)<options.pairs:
            rclpy.spin_once(node,timeout_sec=.1)
    except KeyboardInterrupt:
        interrupted=True
    finally:
        totals=[sum(r['sector_counts'][i] for r in records) for i in range(len(SELF_FILTER_SECTORS))]
        status='FAIL' if node.failure else ('INCOMPLETE' if len(records)<options.pairs or not all(totals) or interrupted else 'PASS')
        endpoints={topic:[dict(node=i.node_name,qos=str(i.qos_profile)) for i in node.get_publishers_info_by_topic(topic)]
                   for topic in (INPUT_TOPIC,OUTPUT_TOPIC)}
        summary=dict(source='live ROS subscriptions; confirm Gazebo origin using bag and process logs',status=status,
            matched_pairs=len(records),validated_pairs=sum(r['status']=='PASS' for r in records),requested_pairs=options.pairs,
            sector_totals=totals,received=node.received,evicted=node.evicted,unmatched=[len(node.raw),len(node.filtered)],
            elapsed_wall_s=time.monotonic()-started,error=node.failure,
            subscription_qos='KEEP_LAST depth=5 BEST_EFFORT VOLATILE',publishers=endpoints,
            front_fixture_enabled=not options.no_front_fixture,
            limitation='Exact value preservation does not identify real objects, recover occluded ranges, or prove Nav2 avoidance')
        (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        fields=['stamp_sec','stamp_nanosec','frame_id','points_raw','points_filtered','valid_raw','valid_filtered','sector_counts','removed','unchanged_valid_returns','metadata_equal','status','error']
        with (out/'pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); writer.writeheader()
            for row in records:
                row=dict(row); row['removed']=json.dumps(json_safe(row['removed'])); row['sector_counts']=json.dumps(row['sector_counts']); writer.writerow(row)
        (out/'report.md').write_text('# Live LaserScan capture\n\n```json\n'+json.dumps(summary,indent=2)+'\n```\nSee pairs.csv and pairs.jsonl for observed rays.\n',encoding='utf-8')
        print(json.dumps(summary,indent=2))
        node.destroy_node(); rclpy.try_shutdown()
    return 0 if status=='PASS' else (2 if status=='INCOMPLETE' else 1)


if __name__=='__main__':
    raise SystemExit(main())
