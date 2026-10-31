#!/usr/bin/env python3
"""Launch RViz with process-local rendering options and preserve graphics diagnostics."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', choices=['auto', 'xcb', 'software'], default='auto')
    parser.add_argument('--output', required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('rviz_args', nargs=argparse.REMAINDER)
    opts = parser.parse_args()
    extra = opts.rviz_args[1:] if opts.rviz_args[:1] == ['--'] else opts.rviz_args
    env = os.environ.copy()
    if opts.render in ('xcb', 'software'):
        env['QT_QPA_PLATFORM'] = 'xcb'
    if opts.render == 'software':
        env['LIBGL_ALWAYS_SOFTWARE'] = 'true'
    command = ['ros2', 'run', 'rviz2', 'rviz2', *extra]
    info = dict(mode=opts.render, dry_run=opts.dry_run, command=command,
        graphics_env={k:env.get(k) for k in ['DISPLAY','WAYLAND_DISPLAY','XDG_SESSION_TYPE',
            'QT_QPA_PLATFORM','LIBGL_ALWAYS_SOFTWARE','MESA_GL_VERSION_OVERRIDE','MESA_GLSL_VERSION_OVERRIDE']},
        note='xcb/software are diagnostic alternatives, not a guaranteed fix for the indexed-map sampler bug.')
    out = Path(opts.output)
    out.mkdir(parents=True, exist_ok=False)
    (out/'environment.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    if opts.dry_run:
        print(json.dumps(info, indent=2))
        return 0
    if not shutil.which('ros2'):
        info['error'] = 'ros2 missing; source /opt/ros/jazzy/setup.bash first'
        (out/'result.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
        print(info['error'], file=sys.stderr)
        return 1
    for name, args in [('glxinfo',['glxinfo','-B']), ('packages',['dpkg-query','-W',
        'ros-jazzy-rviz2','ros-jazzy-rviz-rendering','libgl1-mesa-dri'])]:
        try:
            r = subprocess.run(args, env=env, capture_output=True, text=True, timeout=10)
            (out/(name+'.txt')).write_text(r.stdout+r.stderr, encoding='utf-8')
        except Exception as error:
            (out/(name+'.txt')).write_text(str(error), encoding='utf-8')
    process = None
    try:
        with (out/'rviz.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end='', flush=True)
            code = process.wait()
    except KeyboardInterrupt:
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        code = 130
    info['exit_code'] = code
    info['rendering_verified'] = False
    info['note'] += ' RViz exiting normally does not verify map rendering; inspect map/costmap displays.'
    (out/'result.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
