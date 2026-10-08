#!/usr/bin/env python3
"""Static source checks (PyYAML required); not a runtime scan/physics certification."""
import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET



def validate_scan_filter(root, by_topic):
    import yaml
    path = root / 'scripts/scan_self_filter.py'
    assert path.is_file(), 'Missing scan_self_filter.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    constants = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name) and target.id in (
                        'INPUT_TOPIC', 'OUTPUT_TOPIC', 'SELF_FILTER_SECTORS'):
                    constants[target.id] = ast.literal_eval(statement.value)
    assert constants['INPUT_TOPIC'] == '/scan'
    assert constants['OUTPUT_TOPIC'] == '/scan_filtered'
    assert constants['SELF_FILTER_SECTORS'] == (
        (-142.0, -129.0, 0.22), (-98.0, -82.0, 0.34),
        (-51.0, -39.0, 0.22), (39.0, 51.0, 0.22),
        (82.0, 98.0, 0.34), (129.0, 142.0, 0.22))
    for method, constant in (('create_subscription', 'INPUT_TOPIC'),
                             ('create_publisher', 'OUTPUT_TOPIC')):
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == method]
        assert len(calls) == 1
        assert isinstance(calls[0].args[1], ast.Name) and calls[0].args[1].id == constant
        assert isinstance(calls[0].args[-1], ast.Call)
        assert calls[0].args[-1].func.id == 'sensor_qos'
    qos = next(n for n in ast.walk(tree) if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Name) and n.func.id == 'QoSProfile')
    keywords = {k.arg: k.value for k in qos.keywords}
    assert keywords['history'].attr == 'KEEP_LAST'
    assert keywords['reliability'].attr == 'BEST_EFFORT'
    assert keywords['durability'].attr == 'VOLATILE'
    assert ast.literal_eval(keywords['depth']) == 5
    raw = by_topic['/scan']
    assert raw['gz_topic_name'] == '/scan'
    assert raw['qos_profile'] == 'SENSOR_DATA'
    assert '/scan_filtered' not in by_topic, 'Filtered data must not replace the raw bridge'
    nav = yaml.safe_load((root / 'config/nav2_params.yaml').read_text(encoding='utf-8'))
    assert nav['amcl']['ros__parameters']['scan_topic'] == '/scan_filtered'
    for scope in ('local_costmap', 'global_costmap'):
        params = nav[scope][scope]['ros__parameters']
        assert params['obstacle_layer']['scan']['topic'] == '/scan_filtered'
    assert nav['collision_monitor']['ros__parameters']['scan']['topic'] == '/scan_filtered'
    launch = ast.parse((root / 'launch/nursing_home.launch.py').read_text(encoding='utf-8'))
    node = next(n.value for n in ast.walk(launch) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'scan_self_filter' for t in n.targets))
    kwargs = {k.arg: k.value for k in node.keywords}
    assert ast.literal_eval(kwargs['executable']) == 'scan_self_filter.py'
    assert ast.literal_eval(kwargs['name']) == 'scan_self_filter'
    assert 'condition' not in kwargs, 'Filter must run even when navigation is disabled'
    sim = kwargs['parameters'].elts[0]
    assert ast.literal_eval(sim.keys[0]) == 'use_sim_time'
    assert sim.values[0].func.id == 'LaunchConfiguration'
    assert ast.literal_eval(sim.values[0].args[0]) == 'use_sim_time'
    args = [n for n in ast.walk(launch) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name) and n.func.id == 'DeclareLaunchArgument'
            and ast.literal_eval(n.args[0]) == 'use_sim_time']
    assert len(args) == 1
    assert ast.literal_eval(next(k.value for k in args[0].keywords if k.arg == 'default_value')) == 'true'
    description = next(n for n in ast.walk(launch) if isinstance(n, ast.Call)
                       and isinstance(n.func, ast.Name) and n.func.id == 'LaunchDescription')
    assert any(isinstance(n, ast.Name) and n.id == 'scan_self_filter' for n in description.args[0].elts)
    cmake = (root / 'CMakeLists.txt').read_text(encoding='utf-8')
    install_programs = cmake.split('install(PROGRAMS', 1)[1].split(')', 1)[0]
    assert 'scripts/scan_self_filter.py' in install_programs
    assert 'scripts/compare_scan_filter.py' in install_programs
    assert (root / 'tests/test_scan_self_filter.py').is_file()
    print('PASS (static only): six self-filter sectors, SensorData QoS, raw bridge,')
    print('      four Nav2 inputs, unconditional filter launch, executable installation.')



def validate_initial_pose(root):
    import yaml
    tree = ast.parse((root / 'launch/nursing_home.launch.py').read_text(encoding='utf-8'))
    spawn = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'spawn_robot' for t in n.targets))
    keywords = {k.arg: k.value for k in spawn.keywords}
    assert ast.literal_eval(keywords['package']) == 'ros_gz_sim'
    assert ast.literal_eval(keywords['executable']) == 'create'
    args = keywords['arguments'].elts
    def coordinate(flag):
        indices = [i for i, arg in enumerate(args) if isinstance(arg, ast.Constant) and arg.value == flag]
        assert len(indices) == 1, f'Missing or duplicate spawn {flag}'
        return float(ast.literal_eval(args[indices[0]+1]))
    spawn_xy = (coordinate('-x'), coordinate('-y'))
    nav = yaml.safe_load((root / 'config/nav2_params.yaml').read_text(encoding='utf-8'))
    amcl = nav['amcl']['ros__parameters']
    pose = amcl['initial_pose']
    assert amcl['set_initial_pose'] is True
    assert spawn_xy == (float(pose['x']), float(pose['y'])) == (-1.0, 0.0), 'Spawn/AMCL initial x/y mismatch'
    assert coordinate('-Y') == float(pose['yaw']) == 0.0, 'Initial yaw must be zero'
    assert coordinate('-z') == 0.2, 'Preserve original Gazebo spawn z=0.2'
    assert float(pose['z']) == 0.0, 'AMCL initial z must be zero'
    print('PASS (static): spawn and AMCL x/y=(-1.0, 0.0), yaw=0; spawn z=0.2 preserved.')


def validate(root):
    model_path = root / 'models/dual_arm_robot/model.sdf'
    model = ET.parse(model_path).getroot().find('model')
    urdf = ET.parse(root / 'urdf/dual_arm_mobile_robot.urdf').getroot()
    slinks = {x.get('name'): x for x in model.findall('link')}
    ulinks = {x.get('name'): x for x in urdf.findall('link')}
    sjoints = {x.get('name'): x for x in model.findall('joint')}
    ujoints = {x.get('name'): x for x in urdf.findall('joint')}
    assert set(slinks) == set(ulinks), 'SDF/URDF link mismatch'
    assert set(sjoints) == set(ujoints), 'SDF/URDF joint mismatch'
    parents = {}
    for name, sj in sjoints.items():
        uj = ujoints[name]
        parent, child = sj.findtext('parent'), sj.findtext('child')
        assert parent in slinks and child in slinks
        assert child not in parents, f'Multiple parents: {child}'
        parents[child] = parent
        assert parent == uj.find('parent').get('link')
        assert child == uj.find('child').get('link')
        assert sj.get('type') == uj.get('type') or (sj.get('type') == 'revolute' and uj.get('type') == 'continuous')
        pose = sj.find('pose')
        if pose is not None:
            assert pose.get('relative_to') == parent, name
            xyzrpy = [float(x) for x in pose.text.split()]
            up = uj.find('origin')
            expected = [float(x) for x in (up.get('xyz') + ' ' + up.get('rpy')).split()]
            assert all(abs(a-b) < 1e-9 for a,b in zip(xyzrpy, expected)), name
            lp = slinks[child].find('pose')
            assert lp.get('relative_to') == name and all(float(x) == 0 for x in lp.text.split()), child
        if uj.get('type') == 'revolute' or uj.get('type') == 'prismatic':
            assert sj.findtext('axis/xyz') == uj.find('axis').get('xyz'), name
            for key in ('lower','upper','effort','velocity'):
                assert float(sj.findtext('axis/limit/' + key)) == float(uj.find('limit').get(key)), (name, key)
    for child in slinks:
        visited = set()
        while child in parents:
            assert child not in visited, 'Kinematic cycle'
            visited.add(child)
            child = parents[child]
        assert child == 'base_link', 'Disconnected link tree'
    for side in ('left','right'):
        arm = [j for n,j in sjoints.items() if n.startswith(side + '_') and 'wheel' not in n]
        assert sum(j.get('type') == 'revolute' for j in arm) == 6
        assert sum(j.get('type') == 'prismatic' for j in arm) == 2
    for name, link in slinks.items():
        inertial = link.find('inertial')
        assert float(inertial.findtext('mass')) > 0, name
        inertia = inertial.find('inertia')
        diag = [float(inertia.findtext(k)) for k in ('ixx','iyy','izz')]
        assert all(x>0 for x in diag) and all(x <= sum(diag)-x+1e-9 for x in diag), name
        if (name.startswith(('left_','right_')) and 'wheel' not in name) or name in ('torso', 'laser_support'):
            ui = ulinks[name].find('inertial')
            assert float(ui.find('mass').get('value')) == float(inertial.findtext('mass'))
            for k in ('ixx','iyy','izz','ixy','ixz','iyz'):
                assert float(ui.find('inertia').get(k)) == float(inertia.findtext(k)), name
    bridges = json.loads((root / 'config/ros_gz_bridge.yaml').read_text(encoding='utf-8'))
    by_topic = {b['ros_topic_name']:b for b in bridges}
    controllers = [p for p in model.findall('plugin') if p.get('name').endswith('::JointPositionController')]
    assert len(controllers) == 16
    for plugin in controllers:
        j = plugin.findtext('joint_name')
        assert j in sjoints
        b = by_topic[plugin.findtext('topic')]
        assert b['direction'] == 'ROS_TO_GZ' and b['gz_type_name'] == 'gz.msgs.Double'
        assert float(plugin.findtext('cmd_max')) == float(sjoints[j].findtext('axis/limit/effort'))
    assert by_topic['/tf']['gz_topic_name'] == '/odom_tf'
    diff_drive = model.find("plugin[@name='gz::sim::systems::DiffDrive']")
    assert diff_drive is not None, 'Missing DiffDrive plugin'
    assert [j.text for j in diff_drive.findall('left_joint')] == [
        'left_front_wheel_joint', 'left_rear_wheel_joint'], 'DiffDrive must drive both left wheels'
    assert [j.text for j in diff_drive.findall('right_joint')] == [
        'right_front_wheel_joint', 'right_rear_wheel_joint'], 'DiffDrive must drive both right wheels'
    assert diff_drive.findtext('tf_topic') == '/odom_tf'
    print('PASS (static): DiffDrive contains both front/rear left and right wheel joints.')
    for topic in ('/scan','/joint_states','/camera/image_raw','/camera/camera_info','/odom'):
        assert by_topic[topic]['direction'] == 'GZ_TO_ROS'
    assert slinks['laser_link'].findtext('sensor/gz_frame_id') == 'laser_link'
    assert slinks['camera_link'].findtext('sensor/gz_frame_id') == 'camera_optical_frame'
    # At rest, shoulders clear the torso; LiDAR occupies the open lower scan bay.
    for side, sign in (('left',1),('right',-1)):
        pose = [float(x) for x in sjoints[side+'_shoulder_joint'].findtext('pose').split()]
        assert pose[1] == sign*.32 and abs(pose[1])-.06 > .15
    laser_xyz = [float(x) for x in sjoints['laser_joint'].findtext('pose').split()[:3]]
    assert laser_xyz == [0.0, 0.0, 0.27], 'LiDAR scan-bay placement changed'
    # Housing z=0.25..0.29 lies within the bay z=0.22..0.32.
    assert .22 < laser_xyz[2]-.02 and laser_xyz[2]+.02 < .32
    assert sjoints['laser_support_joint'].findtext('parent') == 'base_link'
    assert sjoints['laser_support_joint'].findtext('pose') == '0 0 0.235 0 0 0'
    assert slinks['laser_support'].findtext('collision/geometry/cylinder/length') == '0.03'
    torso = slinks['torso']
    assert len(torso.findall('collision')) == 6, 'Scan bay needs two plates and four posts'
    for collision, visual in zip(torso.findall('collision'), torso.findall('visual')):
        assert collision.findtext('pose') == visual.findtext('pose')
        assert collision.findtext('geometry/box/size') == visual.findtext('geometry/box/size')
        center = [float(x) for x in collision.findtext('pose').split()[:3]]
        size = [float(x) for x in collision.findtext('geometry/box/size').split()]
        center[2] += .2  # torso origin in base_link
        lower_z, upper_z = center[2]-size[2]/2, center[2]+size[2]/2
        if lower_z <= laser_xyz[2] <= upper_z:
            # Posts cross the plane but must clear the radius-0.05 housing.
            nearest = [max(abs(center[i]-laser_xyz[i])-size[i]/2, 0) for i in (0, 1)]
            assert sum(v*v for v in nearest) > .05**2, 'Housing intersects a scan-bay post'
        else:
            assert upper_z <= laser_xyz[2]-.02 or lower_z >= laser_xyz[2]+.02
    for sc, uc in zip(torso.findall('collision'), ulinks['torso'].findall('collision')):
        assert sc.findtext('geometry/box/size') == uc.find('geometry/box').get('size')
        assert sc.findtext('pose').split()[:3] == uc.find('origin').get('xyz').split()
    assert len(ulinks['torso'].findall('collision')) == 6
    validate_scan_filter(root, by_topic)
    validate_initial_pose(root)
    for p in list((root/'scripts').glob('*.py')) + list((root/'launch').glob('*.py')) + list((root/'tests').glob('*.py')):
        ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
    print('PASS: connected model tree; SDF/URDF poses, axes, limits and arm inertia;')
    print('      6 DOF + 2 fingers per arm; 16 controller/bridge routes; sensor frames; Python syntax.')
    gz = shutil.which('gz')
    if gz:
        subprocess.run([gz, 'sdf', '-k', str(model_path)], check=True)
    else:
        print('SKIP: gz sdf -k (Gazebo not installed). Physics, rendering, TF timing and AMCL require Ubuntu runtime.')


if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
    validate(root)
