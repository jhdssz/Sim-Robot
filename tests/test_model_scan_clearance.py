#!/usr/bin/env python3
"""Offline home-pose geometry regressions; not a Gazebo rendering/physics claim."""
from copy import deepcopy
import math
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from experiment_geometry import sdf_collision_bounds
from scan_self_filter import SELF_FILTER_SECTORS,self_echo_sector


def model(name='model.sdf'):
    return ET.parse(ROOT/'models/dual_arm_robot'/name).getroot().find('model')


def arm_records(m):
    return [r for r in sdf_collision_bounds(m)['collisions']
            if r['link'].startswith(('left_','right_')) and 'wheel' not in r['link']]


class ModelScanClearanceTests(unittest.TestCase):
    def test_home_arm_collisions_above_lidar_in_both_models(self):
        for name in ('model.sdf','experiment.sdf'):
            m=model(name)
            laser_z=float(m.find("joint[@name='laser_joint']/pose").text.split()[2])
            records=arm_records(m)
            self.assertTrue(records)
            self.assertAlmostEqual(min(r['minimum'][2] for r in records),.34)
            for r in records:
                self.assertGreaterEqual(r['minimum'][2]-laser_z,.07-1e-9,(name,r['link']))

    def test_home_arm_visuals_above_lidar_in_both_models(self):
        # GPU lidar sees visual geometry; collision-only checks would miss visual regressions.
        for name in ('model.sdf','experiment.sdf'):
            m=model(name)
            for link in m.findall('link'):
                for c in link.findall('collision'):link.remove(c)
                for visual in link.findall('visual'):
                    clone=deepcopy(visual);clone.tag='collision';link.append(clone)
            self.assertAlmostEqual(min(r['minimum'][2] for r in arm_records(m)),.34)
            self.assertGreater(min(r['minimum'][2] for r in arm_records(m)),.27)

    def test_urdf_sdf_mounts_and_extended_torso_match(self):
        u=ET.parse(ROOT/'urdf/dual_arm_mobile_robot.urdf').getroot()
        for m in (model(),model('experiment.sdf')):
            for name,z in [('left_shoulder_joint',.8),('right_shoulder_joint',.8),('camera_link_joint',.95),('laser_joint',.27)]:
                sp=list(map(float,m.find(f"joint[@name='{name}']/pose").text.split()[:3]))
                up=list(map(float,u.find(f"joint[@name='{name}']/origin").get('xyz').split()))
                self.assertEqual(sp,up,name);self.assertAlmostEqual(sp[2],z,msg=name)
            sl=m.find("link[@name='torso']");ul=u.find("link[@name='torso']")
            for s,c in zip(sl.findall('collision'),ul.findall('collision')):
                self.assertEqual(s.findtext('geometry/box/size'),c.find('geometry/box').get('size'))
                self.assertEqual(s.findtext('pose').split()[:3],c.find('origin').get('xyz').split())
            self.assertEqual(sl.findtext("collision[@name='torso_upper_collision']/geometry/box/size"),'0.3 0.3 0.78')

    def test_four_remaining_posts_cross_plane_and_match_filter(self):
        records=sdf_collision_bounds(model())['collisions']
        posts=[r for r in records if r['collision'].startswith('torso_post_')]
        self.assertEqual(len(posts),4)
        matched=[]
        for p in posts:
            self.assertLess(p['minimum'][2],.27);self.assertGreater(p['maximum'][2],.27)
            x=(p['minimum'][0]+p['maximum'][0])/2;y=(p['minimum'][1]+p['maximum'][1])/2
            sector=self_echo_sector(math.degrees(math.atan2(y,x)),math.hypot(x,y))
            self.assertIsNotNone(sector);matched.append(sector)
        self.assertEqual(sorted(matched),list(range(4)))
        self.assertEqual(len(SELF_FILTER_SECTORS),4)

    def test_extended_torso_mass_inertia_and_scan_bay(self):
        u=ET.parse(ROOT/'urdf/dual_arm_mobile_robot.urdf').getroot().find("link[@name='torso']/inertial")
        for m in (model(),model('experiment.sdf')):
            torso=m.find("link[@name='torso']");inertial=torso.find('inertial')
            self.assertEqual(float(inertial.findtext('mass')),10)
            diag=[float(inertial.findtext('inertia/'+k)) for k in ('ixx','iyy','izz')]
            for k,v in zip(('ixx','iyy','izz'),diag):
                self.assertGreater(v,0);self.assertLessEqual(v,sum(diag)-v+1e-9)
                self.assertEqual(v,float(u.find('inertia').get(k)))
            self.assertEqual(list(map(float,inertial.findtext('pose').split()[:3])),list(map(float,u.find('origin').get('xyz').split())))
            upper=torso.find("collision[@name='torso_upper_collision']")
            center=float(upper.findtext('pose').split()[2])+.2
            height=float(upper.findtext('geometry/box/size').split()[2])
            self.assertAlmostEqual(center-height/2,.32)
            self.assertAlmostEqual(center+height/2,1.1)


    def test_conservative_arm_reach_clears_plane_with_joint_limits(self):
        # Triangle-inequality bound: all revolute rotations preserve link lengths.
        # Include maximum prismatic travel and bounding spheres for every collision.
        root=ET.parse(ROOT/'urdf/dual_arm_mobile_robot.urdf').getroot()
        joints={j.find('child').get('link'):j for j in root.findall('joint')}
        minimum=math.inf
        for link in root.findall('link'):
            name=link.get('name')
            if not name.startswith(('left_','right_')) or 'wheel' in name:continue
            side=name.split('_')[0];shoulder=side+'_shoulder'
            mount_z=.2+float(joints[shoulder].find('origin').get('xyz').split()[2])
            reach=0.0;cursor=name
            while cursor!=shoulder:
                joint=joints[cursor]
                reach+=math.sqrt(sum(float(v)**2 for v in joint.find('origin').get('xyz').split()))
                if joint.get('type')=='prismatic':
                    reach+=max(abs(float(joint.find('limit').get(k))) for k in ('lower','upper'))
                cursor=joint.find('parent').get('link')
            for collision in link.findall('collision'):
                offset=math.sqrt(sum(float(v)**2 for v in collision.find('origin').get('xyz').split()))
                geometry=collision.find('geometry')
                if geometry.find('sphere') is not None:radius=float(geometry.find('sphere').get('radius'))
                elif geometry.find('cylinder') is not None:
                    c=geometry.find('cylinder');radius=math.hypot(float(c.get('radius')),float(c.get('length'))/2)
                else:radius=math.sqrt(sum((float(v)/2)**2 for v in geometry.find('box').get('size').split()))
                bound=mount_z-reach-offset-radius
                minimum=min(minimum,bound)
                self.assertGreater(bound,.30,(name,bound))
        self.assertGreater(minimum-.27,.03)


if __name__=='__main__':unittest.main(verbosity=2)
