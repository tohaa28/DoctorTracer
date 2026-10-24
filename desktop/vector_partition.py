"""Visible, disjoint vector regions grouped by RGB, retaining cubic curves."""
import math
import re
import time
import json
import os
import sys
import subprocess
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
import pathops

NS='http://www.w3.org/2000/svg'
TOKEN=re.compile(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?')


def parse(data):
    tokens=TOKEN.findall(data);p=pathops.Path();i=0;cmd='';x=y=mx=my=0.
    while i<len(tokens):
        if tokens[i].isalpha():cmd=tokens[i];i+=1
        upper=cmd.upper();relative=cmd.islower()
        if upper=='Z':p.close();x,y=mx,my;cmd='';continue
        n={'M':2,'L':2,'C':6,'Q':4,'H':1,'V':1}.get(upper)
        if n is None or i+n>len(tokens):raise ValueError('Unsupported vector path command: '+cmd)
        v=list(map(float,tokens[i:i+n]));i+=n
        if upper in ('H','V'):
            if upper=='H':x=v[0]+(x if relative else 0)
            else:y=v[0]+(y if relative else 0)
            p.lineTo(x,y);continue
        if relative:
            v=[value+(x if j%2==0 else y) for j,value in enumerate(v)]
        if upper=='M':p.moveTo(*v);mx,my=v;cmd='l' if relative else 'L'
        elif upper=='L':p.lineTo(*v)
        elif upper=='C':p.cubicTo(*v)
        else:p.quadTo(*v)
        x,y=v[-2:]
    return p


def serialize(p):
    result=[];current=(0.,0.)
    def point(pt):return ' '.join(format(v,'.9g') for v in pt)
    for op,pts in p.segments:
        if op=='moveTo':result.append('M'+point(pts[0]));current=pts[0]
        elif op=='lineTo':result.append('L'+point(pts[0]));current=pts[0]
        elif op=='curveTo':result.append('C'+' '.join(map(point,pts)));current=pts[-1]
        elif op=='qCurveTo':
            # SVG/EPS consumers share the same M/L/C/Z dialect.
            control,end=pts
            c1=tuple(current[j]+2/3*(control[j]-current[j]) for j in (0,1))
            c2=tuple(end[j]+2/3*(control[j]-end[j]) for j in (0,1))
            result.append('C'+' '.join(map(point,(c1,c2,end))));current=end
        elif op=='closePath':result.append('Z')
        else:raise ValueError('Unsupported boolean path verb: '+op)
    return ' '.join(result)


def components(p):
    """Keep holes attached; avoid Qt's limit on huge compound paths."""
    contours=list(p.contours)
    outers=[c for c in contours if not c.clockwise]
    holes=[c for c in contours if c.clockwise]
    if not outers and contours:raise ValueError('Invalid outer contour winding')
    grouped=[pathops.Path(c) for c in outers]
    for hole in holes:
        point=hole.firstPoints[0]
        parents=[j for j,c in enumerate(outers) if c.contains(point)]
        if not parents:raise ValueError('Unattached vector hole')
        parent=min(parents,key=lambda j:abs(outers[j].area))
        grouped[parent].addPath(hole)
    return grouped


def overlap(a,b):
    return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]


def polygon_data(data):
    from photo_curves import qpath
    from PySide6.QtGui import QTransform
    paths=[]
    # Preserve exact decimal grid coordinates for already linear output.
    if not re.search('[CcQq]',data):
        tokens=TOKEN.findall(data);current=[];i=0;cmd=''
        while i<len(tokens):
            if tokens[i].isalpha():cmd=tokens[i];i+=1
            if cmd=='Z':
                if len(current)>=3:paths.append(current)
                current=[];cmd='';continue
            if cmd=='M' and current:
                if len(current)>=3:paths.append(current)
                current=[]
            if cmd not in ('M','L'):raise ValueError('Unsupported linear audit command')
            current.append((round(float(tokens[i])*10000000),round(float(tokens[i+1])*10000000)));i+=2;cmd='L'
        if len(current)>=3:paths.append(current)
        return paths
    for polygon in qpath(data).toSubpathPolygons(QTransform().scale(64,64)):
        points=[(round(point.x()/64*10000000),round(point.y()/64*10000000)) for point in polygon]
        if len(points)>=3:paths.append(points)
    return paths


def polygon_paths(p):return polygon_data(serialize(p))


def audit_pieces(pieces,report=None):
    """Independent integer intersection audit, including same-color objects."""
    import pyclipper as pc
    seen=[];index=SpatialIndex();pairs=0;maximum=0.
    for color,data in pieces:
        polygons=polygon_data(data)
        if not polygons:continue
        bounds=(min(x for p in polygons for x,y in p)/10000000,min(y for p in polygons for x,y in p)/10000000,max(x for p in polygons for x,y in p)/10000000,max(y for p in polygons for x,y in p)/10000000)
        for j in index.candidates(bounds):
            clipper=pc.Pyclipper()
            if not clipper.AddPaths(polygons,pc.PT_SUBJECT,True):continue
            if not clipper.AddPaths(seen[j],pc.PT_CLIP,True):continue
            intersections=clipper.Execute(pc.CT_INTERSECTION,pc.PFT_NONZERO,pc.PFT_NONZERO)
            pairs+=1
            area=abs(sum(pc.Area(p) for p in intersections))/10000000**2
            maximum=max(maximum,area)
            if area>.0001:
                raise ValueError(f'Vector overlap detected by independent integer audit: {area} px2, pair {len(seen)}/{j}')
        index.add(len(seen),bounds);seen.append(polygons)
    if report is not None:report.update({'pairs_checked':pairs,'max_intersection_area_px2':maximum,'tolerance_px2':.0001})
    return pairs


def curve_tile(items,candidates,bounds):
    clip=pathops.Path();clip.moveTo(bounds[0],bounds[1]);clip.lineTo(bounds[2],bounds[1]);clip.lineTo(bounds[2],bounds[3]);clip.lineTo(bounds[0],bounds[3]);clip.close()
    seen=[];index=SpatialIndex();result=[]
    for i in reversed(candidates):
        color,p=items[i];b=p.bounds
        inside=b[0]>=bounds[0] and b[1]>=bounds[1] and b[2]<=bounds[2] and b[3]<=bounds[3]
        local=pathops.simplify(p) if inside else pathops.op(p,clip,pathops.PathOp.INTERSECTION)
        if not len(local):continue
        neighbors=index.candidates(local.bounds);covered=pathops.Path()
        for j in neighbors:covered.addPath(seen[j])
        covered.fillType=pathops.FillType.WINDING
        visible=pathops.op(local,covered,pathops.PathOp.DIFFERENCE) if len(covered) else local
        if len(covered) and len(visible):
            residual=pathops.op(visible,covered,pathops.PathOp.INTERSECTION)
            if abs(residual.area)>.00001:raise pathops.PathOpsError('Residual overlap after curve subtraction')
        if len(visible):index.add(len(seen),visible.bounds);seen.append(visible)
        for piece in components(visible):result.append((color,serialize(piece)))
    return result


def polygon_tile(items,candidates,bounds,cache):
    # Integer clipping is the robust fallback for a whole tile. Recompute all
    # its regions together, so no curved/linear approximation can overlap a
    # previously emitted region. Other tiles retain their original Beziers.
    import pyclipper as pc
    rect=[(round(bounds[x]*10000000),round(bounds[y]*10000000)) for x,y in [(0,1),(2,1),(2,3),(0,3)]]
    seen=[];index=SpatialIndex();result=[]
    def emit(node,color):
        for outer in node.Childs:
            if outer.IsHole:continue
            paths=[outer.Contour]+[h.Contour for h in outer.Childs if h.IsHole]
            chunks=[]
            for path in paths:
                chunks.append('M'+' L'.join(f'{x/10000000:.7f} {y/10000000:.7f}' for x,y in path)+' Z')
            result.append((color,' '.join(chunks)))
            for hole in outer.Childs:emit(hole,color)
    for i in reversed(candidates):
        color,p=items[i]
        if i not in cache:cache[i]=polygon_paths(p)
        if not cache[i]:continue
        clipper=pc.Pyclipper()
        if not clipper.AddPaths(cache[i],pc.PT_SUBJECT,True):continue
        clipper.AddPath(rect,pc.PT_CLIP,True)
        local=clipper.Execute(pc.CT_INTERSECTION,pc.PFT_NONZERO,pc.PFT_NONZERO)
        if not local:continue
        clipper=pc.Pyclipper();clipper.AddPaths(local,pc.PT_SUBJECT,True)
        b=clipper.GetBounds();neighbors=index.candidates((b.left/10000000,b.top/10000000,b.right/10000000,b.bottom/10000000))
        for j in neighbors:clipper.AddPaths(seen[j],pc.PT_CLIP,True)
        tree=clipper.Execute2(pc.CT_DIFFERENCE,pc.PFT_NONZERO,pc.PFT_NONZERO)
        visible=pc.ClosedPathsFromPolyTree(tree)
        if visible:
            bb=(min(x for path in visible for x,y in path)/10000000,min(y for path in visible for x,y in path)/10000000,max(x for path in visible for x,y in path)/10000000,max(y for path in visible for x,y in path)/10000000)
            index.add(len(seen),bb);seen.append(visible)
        emit(tree,color)
    return result


def clean_polygon_pieces(pieces):
    # Resolve very small rounding slivers from compound multi-region clipping
    # using simpler per-object subtraction, then run the same audit again.
    import pyclipper as pc
    seen=[];index=SpatialIndex();result=[]
    def emit(node,color):
        for outer in node.Childs:
            if outer.IsHole:continue
            contours=[outer.Contour]+[h.Contour for h in outer.Childs if h.IsHole]
            data=' '.join('M'+' L'.join(f'{x/10000000:.7f} {y/10000000:.7f}' for x,y in path)+' Z' for path in contours)
            result.append((color,data))
            for hole in outer.Childs:emit(hole,color)
    for color,data in pieces:
        polygons=polygon_data(data)
        if not polygons:continue
        bb=(min(x for p in polygons for x,y in p)/10000000,min(y for p in polygons for x,y in p)/10000000,max(x for p in polygons for x,y in p)/10000000,max(y for p in polygons for x,y in p)/10000000)
        for j in index.candidates(bb):
            clipper=pc.Pyclipper();clipper.StrictlySimple=True
            if not clipper.AddPaths(polygons,pc.PT_SUBJECT,True):polygons=[];break
            clipper.AddPaths(seen[j],pc.PT_CLIP,True)
            polygons=clipper.Execute(pc.CT_DIFFERENCE,pc.PFT_NONZERO,pc.PFT_NONZERO)
            if not polygons:break
        if not polygons:continue
        clipper=pc.Pyclipper();clipper.AddPaths(polygons,pc.PT_SUBJECT,True)
        tree=clipper.Execute2(pc.CT_UNION,pc.PFT_NONZERO,pc.PFT_NONZERO)
        normalized=pc.ClosedPathsFromPolyTree(tree)
        if not normalized:continue
        index.add(len(seen),bb);seen.append(normalized);emit(tree,color)
    return result


class SpatialIndex:
    def __init__(self):self.cells={};self.bounds={}
    def keys(self,b):
        for y in range(math.floor(b[1]/64),math.floor(b[3]/64)+1):
            for x in range(math.floor(b[0]/64),math.floor(b[2]/64)+1):yield x,y
    def add(self,index,b):
        self.bounds[index]=b
        for key in self.keys(b):self.cells.setdefault(key,[]).append(index)
    def candidates(self,b):
        found=set()
        for key in self.keys(b):found.update(self.cells.get(key,()))
        return sorted(i for i in found if overlap(b,self.bounds[i]))


def tile_result(items,candidates,bounds,cache):
    try:
        pieces=curve_tile(items,candidates,bounds)
        audit_pieces(pieces)
        return pieces,False
    except (pathops.PathOpsError,ValueError):
        pieces=polygon_tile(items,candidates,bounds,cache)
        try:audit_pieces(pieces)
        except ValueError:
            pieces=clean_polygon_pieces(pieces)
            audit_pieces(pieces)
        return pieces,True


def geometry_worker(job_file,worker_index):
    job=json.loads(Path(job_file).read_text(encoding='utf8'))
    items=[(color,parse(data)) for color,data in job['items']]
    rows=[];cache={}
    for i in range(worker_index,len(job['tiles']),job['workers']):
        candidates,bounds=job['tiles'][i]
        rows.append((i,tile_result(items,candidates,bounds,cache)))
    Path(job['outputs'][worker_index]).write_text(json.dumps(rows),encoding='utf8')
    return 0


def parallel_tiles(items,jobs,workers):
    with tempfile.TemporaryDirectory(prefix='doctor-geometry-') as directory:
        root=Path(directory);job=root/'geometry.json'
        outputs=[str(root/f'worker-{i}.json') for i in range(workers)]
        job.write_text(json.dumps({'items':[(c,serialize(p)) for c,p in items],
                                   'tiles':jobs,'workers':workers,'outputs':outputs}),encoding='utf8')
        command=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).with_name('app.py'))]
        processes=[]
        try:
            for i in range(workers):
                processes.append(subprocess.Popen(command+['--geometry-worker',str(job),str(i)],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)))
            for process in processes:
                _,error=process.communicate(timeout=180)
                if process.returncode:raise RuntimeError('Geometry worker failed: '+error.decode('utf8',errors='replace')[-1200:])
            rows={i:result for output in outputs for i,result in json.loads(Path(output).read_text(encoding='utf8'))}
            return [rows[i] for i in range(len(jobs))]
        finally:
            for process in processes:
                if process.poll() is None:process.terminate();process.wait(timeout=10)


def partition(svg):
    started=time.perf_counter();root=ET.fromstring(svg);items=[]
    for el in root.iter('{'+NS+'}path'):
        p=parse(el.get('d',''));transform=el.get('transform','')
        if transform:
            m=re.fullmatch(r'translate\(([-+\d.eE]+)[, ]+([-+\d.eE]+)\)',transform)
            if not m:raise ValueError('Unsupported partition transform')
            p=p.transform(translateX=float(m[1]),translateY=float(m[2]))
        if el.get('fill-rule')=='evenodd':p.fillType=pathops.FillType.EVEN_ODD
        if el.get('fill-opacity','1') not in ('1','1.0'):raise ValueError('Partial opacity requires a separate partition policy')
        if len(p):items.append((el.get('fill','#000000'),p))
    index=SpatialIndex()
    for i,(_,p) in enumerate(items):index.add(i,p.bounds)
    view=list(map(float,root.get('viewBox',f"0 0 {root.get('width')} {root.get('height')}").split()))
    left,top,width,height=view
    out=ET.Element(root.tag,root.attrib);groups={};count=operations=tiles=fallbacks=0
    jobs=[]
    for y in range(math.floor(top/128),math.ceil((top+height)/128)):
        for x in range(math.floor(left/128),math.ceil((left+width)/128)):
            bounds=(max(left,x*128),max(top,y*128),min(left+width,(x+1)*128),min(top+height,(y+1)*128))
            candidates=index.candidates(bounds)
            if not candidates:continue
            tiles+=1;operations+=len(candidates);jobs.append((candidates,bounds))
    workers=min(4,os.cpu_count() or 1) if len(items)>1000 and len(jobs)>12 else 1
    cache={}
    results=parallel_tiles(items,jobs,workers) if workers>1 else [tile_result(items,c,b,cache) for c,b in jobs]
    for pieces,fallback in results:
        fallbacks+=int(fallback)
        for color,data in pieces:
            if color not in groups:
                groups[color]=ET.SubElement(out,'{'+NS+'}g',{'id':'color-'+color.lstrip('#'),'fill':color,'data-color':color})
            ET.SubElement(groups[color],'{'+NS+'}path',{'d':data,'fill':color,'fill-rule':'nonzero'});count+=1
    ET.register_namespace('',NS)
    from color_objects import merge_colors
    merged,count=merge_colors(ET.tostring(out,encoding='unicode',xml_declaration=True),preserve_curves=tiles<=1)
    return merged,{
        'paths':count,'color_groups':len(groups),'vector_layout':'disjoint color groups',
        'partition_seconds':time.perf_counter()-started,'partition_operations':operations,
        'partition_tiles':tiles,'partition_polygon_tiles':fallbacks,'geometry_compute':'Skia/Clipper CPU','geometry_workers':workers,
        'geometry_verified':True,'overlap_tolerance_px2':.0001}
