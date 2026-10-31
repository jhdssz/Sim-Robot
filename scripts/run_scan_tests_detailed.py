#!/usr/bin/env python3
"""Run the existing unittest suite, recording actual calls without replacing assertions."""
import argparse
import ast
import csv
import inspect
import json
import math
from pathlib import Path
import sys
import time
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'tests')]
import test_scan_self_filter as tests
import scan_self_filter as production
import compare_scan_filter as comparison


def safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    return value


def snapshot(msg):
    return dict(angle_min=msg.angle_min, angle_max=msg.angle_max,
                angle_increment=msg.angle_increment,
                angles_deg=[production.angle_degrees(msg.angle_min,msg.angle_increment,i)
                            for i in range(len(msg.ranges))],
                ranges=list(msg.ranges), range_min=msg.range_min, range_max=msg.range_max,
                stamp=[msg.header.stamp.sec,msg.header.stamp.nanosec],
                frame_id=msg.header.frame_id)


class DetailedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.records=[]

    def startTest(self,test):
        super().startTest(test)
        source=inspect.getsource(getattr(tests.FilterTests,test._testMethodName))
        tree=ast.parse(textwrap.dedent(source))
        assertions=[ast.get_source_segment(textwrap.dedent(source),n)
                    for n in ast.walk(tree) if isinstance(n,ast.Call)
                    and isinstance(n.func,ast.Attribute) and n.func.attr.startswith('assert')]
        self.current=dict(name=test._testMethodName,purpose=test.shortDescription(),
                          expected_assertions=assertions,sectors=production.SELF_FILTER_SECTORS,
                          calls=[],status='PASS')
        self.started=time.perf_counter()

    def addFailure(self,test,err):
        self.current['status']='FAIL'; super().addFailure(test,err)

    def addError(self,test,err):
        self.current['status']='ERROR'; super().addError(test,err)

    def stopTest(self,test):
        self.current['duration_ms']=(time.perf_counter()-self.started)*1000
        self.records.append(self.current)
        self.stream.writeln(json.dumps(safe(self.current),ensure_ascii=False))
        super().stopTest(test)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='experiment_results/offline')
    opts=parser.parse_args(); out=Path(opts.output); out.mkdir(parents=True,exist_ok=True)
    result_holder=[]
    original_filter=production.filter_scan; original_pair=comparison.inspect_pair
    def wrapped_filter(msg):
        before=snapshot(msg); actual=original_filter(msg)
        changed=[i for i,(a,b) in enumerate(zip(msg.ranges,actual.ranges))
                 if not comparison.same_value(a,b)]
        # Noncandidate samples are only synthetic environment proxies, not proven real obstacles.
        candidates=[i for i,r in enumerate(msg.ranges)
                    if math.isfinite(msg.angle_min) and math.isfinite(msg.angle_increment)
                    and production.self_echo_sector(production.angle_degrees(msg.angle_min,msg.angle_increment,i),r) is not None]
        preserved=all(comparison.same_value(a,b) for i,(a,b) in enumerate(zip(msg.ranges,actual.ranges)) if i not in candidates)
        result_holder[0].current['calls'].append(dict(kind='filter',input=before,
             actual=snapshot(actual),filtered_count=len(changed),changed_indices=changed,
             synthetic_environment_preserved=preserved))
        return actual
    def wrapped_pair(raw,filtered,*args,**kwargs):
        record=dict(kind='comparison',input=snapshot(raw),provided_output=snapshot(filtered))
        try:
            value=original_pair(raw,filtered,*args,**kwargs); record['actual']=value; return value
        except Exception as error:
            record['actual_exception']=f'{type(error).__name__}: {error}'; raise
        finally:
            result_holder[0].current['calls'].append(record)
    tests.filter_scan=wrapped_filter; tests.inspect_pair=wrapped_pair
    # Do not wrap comparison.filter_scan: its oracle calls are not test-subject calls.
    def factory(*args,**kwargs):
        result=DetailedResult(*args,**kwargs); result_holder.append(result); return result
    with (out/'terminal.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=factory).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(tests.FilterTests))
    data=safe(result.records)
    (out/'details.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'tests.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['name','purpose','status','duration_ms','filtered_count','synthetic_environment_preserved','expected_assertions','sectors','calls']
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for r in data:
            row={k:r.get(k) for k in fields}
            row['filtered_count']=sum(c.get('filtered_count',0) for c in r['calls'])
            row['synthetic_environment_preserved']=all(c.get('synthetic_environment_preserved',True) for c in r['calls'])
            for k in ['expected_assertions','sectors','calls']: row[k]=json.dumps(row[k],ensure_ascii=False)
            writer.writerow(row)
    lines=['# Offline LaserScan unittest evidence','',
           'Actual unittest execution; all inputs are synthetic. Counts are summed across direct filter calls in each test. Comparison-only tests have no direct filter call (0 is not a live measurement).', '',
           '| Test | Purpose | Result | ms | Filtered | Synthetic environment proxies retained |',
           '|---|---|---|---:|---:|---|']
    for r in data:
        calls=r['calls']; count=sum(c.get('filtered_count',0) for c in calls)
        keep=all(c.get('synthetic_environment_preserved',True) for c in calls)
        lines.append(f"| {r['name']} | {r['purpose']} | {r['status']} | {r['duration_ms']:.4f} | {count} | {keep if any(c['kind']=='filter' for c in calls) else 'N/A; comparison validation'} |")
    for r in data:
        lines += ['',f"## {r['name']}",'','Expected: original assertions (unchanged):','```python',*r['expected_assertions'],'```',
                  'Actual input angles/distances, thresholds, outputs and caught exceptions:', '```json',json.dumps(r,ensure_ascii=False,indent=2),'```']
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'{result.testsRun} actual tests; failures={len(result.failures)}, errors={len(result.errors)}; report={out}')
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__':
    raise SystemExit(main())
