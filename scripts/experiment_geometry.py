#!/usr/bin/env python3
"""Read SDF geometry and quantify the independent narrow-gap fixture (offline)."""
import argparse
import ast
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
if not (ROOT/'models').is_dir():
    from ament_index_python.packages import get_package_share_directory
    ROOT=Path(get_package_share_directory('nursing_home_sim'))


def pose(node):
    p=node.find('pose')
    return [float(v) for v in p.text.split()] if p is not None else [0.0]*6


def compose(a,b):
    # The world fixtures are yaw-only. Reject tilted world collision frames.
    if any(abs(v)>1e-8 for v in (a[3],a[4],b[3],b[4])):
        raise ValueError('Tilted world boxes require 3D projection')
    c,s=math.cos(a[5]),math.sin(a[5])
    return [a[0]+c*b[0]-s*b[1],a[1]+s*b[0]+c*b[1],a[2]+b[2],0,0,a[5]+b[5]]


def world_boxes(world):
    boxes=[]
    for model in ET.parse(world).getroot().find('world').findall('model'):
        for link in model.findall('link'):
            for collision in link.findall('collision'):
                size=collision.find('geometry/box/size')
                if size is None: continue
                size=list(map(float,size.text.split()))
                p=compose(compose(pose(model),pose(link)),pose(collision))
                if p[2]+size[2]/2<=.05: continue # floor, not an upright obstacle
                boxes.append(dict(name=model.get('name')+'/'+link.get('name'),pose=p,size=size))
    return boxes


def polygon(box):
    x,y,_,_,_,yaw=box['pose']; sx,sy,_=box['size']; c,s=math.cos(yaw),math.sin(yaw)
    return [(x+c*a-s*b,y+s*a+c*b) for a,b in [(-sx/2,-sy/2),(sx/2,-sy/2),(sx/2,sy/2),(-sx/2,sy/2)]]


def segment_distance(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]; den=dx*dx+dy*dy
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)) if den else 0
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)


def polygons_distance(a,b):
    # SAT intersection, then shortest vertex-to-edge distance for disjoint convex polygons.
    separated=False
    for poly in (a,b):
        for i,p in enumerate(poly):
            q=poly[(i+1)%len(poly)]; axis=(-(q[1]-p[1]),q[0]-p[0])
            aa=[v[0]*axis[0]+v[1]*axis[1] for v in a]; bb=[v[0]*axis[0]+v[1]*axis[1] for v in b]
            if max(aa)<min(bb) or max(bb)<min(aa): separated=True
    if not separated:return 0.0
    return min(segment_distance(p,poly[i],poly[(i+1)%len(poly)]) for points,poly in ((a,b),(b,a)) for p in points for i in range(len(poly)))


def footprint_at(x,y,yaw,vertices):
    c,s=math.cos(yaw),math.sin(yaw)
    return [(x+c*a-s*b,y+s*a+c*b) for a,b in vertices]


def sdf_collision_bounds(model):
    """Exact primitive AABBs at SDF home pose, resolving link/joint pose frames."""
    def mat(p):
        x,y,z,r,pitch,yaw = p
        cr,sr,cp,sp,cy,sy = math.cos(r),math.sin(r),math.cos(pitch),math.sin(pitch),math.cos(yaw),math.sin(yaw)
        return [[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr,x],
                [sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr,y],[-sp,cp*sr,cp*cr,z],[0,0,0,1]]
    def mul(a,b):
        return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
    identity=mat([0]*6)
    frames={n.get('name'):n for n in list(model) if n.tag in ('link','joint','frame')}
    cache={'__model__':identity}
    def resolve(name,trail=()):
        if name in cache:return cache[name]
        if name in trail:raise ValueError('Cyclic SDF frame: '+name)
        n=frames[name]; pe=n.find('pose')
        default=n.findtext('child') if n.tag=='joint' else '__model__'
        parent=pe.get('relative_to',default) if pe is not None else default
        cache[name]=mul(resolve(parent,trail+(name,)),mat(pose(n)))
        return cache[name]
    records=[]
    for link in model.findall('link'):
        for c in link.findall('collision'):
            pe=c.find('pose'); parent=pe.get('relative_to',link.get('name')) if pe is not None else link.get('name')
            t=mul(resolve(parent),mat(pose(c))); g=c.find('geometry')
            if g.find('box') is not None:
                half=[float(v)/2 for v in g.findtext('box/size').split()]
                ext=[sum(abs(t[i][j])*half[j] for j in range(3)) for i in range(3)]
            elif g.find('sphere') is not None:
                ext=[float(g.findtext('sphere/radius'))]*3
            elif g.find('cylinder') is not None:
                r=float(g.findtext('cylinder/radius')); h=float(g.findtext('cylinder/length'))/2
                ext=[r*math.sqrt(max(0,1-t[i][2]**2))+h*abs(t[i][2]) for i in range(3)]
            else:raise ValueError('Unsupported robot collision geometry')
            records.append(dict(link=link.get('name'),collision=c.get('name'),
                minimum=[t[i][3]-ext[i] for i in range(3)],maximum=[t[i][3]+ext[i] for i in range(3)]))
    def envelope(items):
        lo=[min(r['minimum'][i] for r in items) for i in range(3)]
        hi=[max(r['maximum'][i] for r in items) for i in range(3)]
        return dict(minimum=lo,maximum=hi,size=[b-a for a,b in zip(lo,hi)])
    return dict(home_pose=envelope(records),wheels=envelope([r for r in records if 'wheel' in r['link']]),collisions=records)


def analyze(world,params):
    boxes=world_boxes(world)
    desk=next(b for b in boxes if b['name']=='reception_desk/link')
    obstacle=next(b for b in boxes if b['name']=='narrow_gap_obstacle/link')
    cabinet=next(b for b in boxes if b['name']=='medicine_shelf/link')
    sdf=ET.parse(ROOT/'models/dual_arm_robot/model.sdf').getroot().find('model')
    chassis=list(map(float,sdf.find("link[@name='base_link']/collision/geometry/box/size").text.split()))
    footprint=ast.literal_eval(re.search(r'footprint:\s*"([^"\n]+)"',Path(params).read_text(encoding='utf-8')).group(1))
    radius=max(math.hypot(*v) for v in footprint)
    collision_envelope=sdf_collision_bounds(sdf)
    full_home_width=collision_envelope['home_pose']['size'][1]
    reference_south=cabinet['pose'][1]-cabinet['size'][1]/2
    block_north=obstacle['pose'][1]+obstacle['size'][1]/2
    gap=reference_south-block_north
    overlap=[max(cabinet['pose'][0]-cabinet['size'][0]/2,obstacle['pose'][0]-obstacle['size'][0]/2),
             min(cabinet['pose'][0]+cabinet['size'][0]/2,obstacle['pose'][0]+obstacle['size'][0]/2)]
    assert overlap[1]>overlap[0] and gap>0
    slit_roi=[[overlap[0],block_north],[overlap[1],block_north],
              [overlap[1],reference_south],[overlap[0],reference_south]]
    # A conservative full-yaw circular sweep checks a fallback geometric route against every upright box.
    route=[[-2,0],[-2,-3.6],[4,-3.6],[4,0]]; clearance=math.inf
    for a,b in zip(route,route[1:]):
        n=math.ceil(math.dist(a,b)/.01)
        for i in range(n+1):
            p=[a[j]+(b[j]-a[j])*i/n for j in range(2)]
            for box in boxes:
                clearance=min(clearance,polygons_distance([p],polygon(box))-radius)
    return dict(source='offline SDF/config geometry; NOT Gazebo/Nav2 measurements',desk=desk,cabinet=cabinet,gap_reference=cabinet['name'],obstacle=obstacle,
        gap_m=gap,gap_axis='y',slit_roi=slit_roi,chassis_size_m=chassis,sdf_collision_envelope=collision_envelope,
        full_home_width_including_both_arms_m=full_home_width,
        gap_minus_home_width_m=gap-full_home_width,
        gap_minus_forward_nav_width_m=gap-(max(v[1] for v in footprint)-min(v[1] for v in footprint)),
        all_yaw_projection_blocked=gap<min(max(v[0] for v in footprint)-min(v[0] for v in footprint),max(v[1] for v in footprint)-min(v[1] for v in footprint)),
        wheels_outer_width_approx_m=.55,
        footprint=footprint,footprint_length_m=.64,footprint_width_m=.8,
        rotation_swept_diameter_m=radius*2,costmap_resolution_m=.05,inflation_radius_m=.55,
        gap_cells=gap/.05,rotated_y_width_formula='0.64*abs(sin(yaw)) + 0.80*abs(cos(yaw))',
        minimum_rotated_footprint_width_m=.64,geometric_fallback_route=route,
        fallback_swept_circle_clearance_lower_bound_m=clearance-.005,
        start=[-2,0,0],goal=[4,0,0],all_world_boxes=boxes,
        note='Inflation is a graded cost, not a hard wall; check footprint and measured costmap. Navfn global paths are center paths and may still propose unsafe slits.')


def main():
    p=argparse.ArgumentParser(); p.add_argument('--world',default=str(ROOT/'worlds/nursing_home_narrow.world'));p.add_argument('--params',default=str(ROOT/'config/nav2_narrow.yaml'));p.add_argument('--output',default='experiment_results/geometry.json');o=p.parse_args()
    data=analyze(o.world,o.params); out=Path(o.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in data.items() if k!='all_world_boxes'},indent=2))

if __name__=='__main__':main()

