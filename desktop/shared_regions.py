"""Trace a labelled partition with exactly matching boundaries on both sides.

Every corner belongs to a shared grid graph. Two-colour corners are rounded
with the same quadratic in reverse; junctions stay fixed. No boolean flattening
or independently fitted, overlapping colour masks are needed.
"""
import collections
import time
import xml.etree.ElementTree as ET
import numpy as np

NS='http://www.w3.org/2000/svg'

def trace(labels,palette,original,smooth=False,curve_tolerance=.5,rounding=1.5,passes=8):
    started=time.perf_counter();h,w=labels.shape;stride=w+1
    # Duplicate RGB entries are one editable object, including their boundaries.
    unique=[];lookup={};remap=np.full(len(palette),-1,np.int32)
    for i,rgb in enumerate(palette):
        rgb=tuple(rgb)
        if rgb not in lookup:lookup[rgb]=len(unique);unique.append(rgb)
        remap[i]=lookup[rgb]
    visible=labels!=255 if labels.dtype==np.uint8 else labels>=0
    mapped=np.full(labels.shape,-1,np.int32);mapped[visible]=remap[labels[visible]]
    labels=mapped;palette=unique
    edges=collections.defaultdict(dict);graph=collections.defaultdict(set)
    padded=np.pad(labels.astype(np.int32),1,constant_values=-1)
    def add(color,a,b):
        if color<0:return
        edges[int(color)].setdefault(a,[]).append(b)
    # All grid edges once. Clockwise directed loops keep the material at right.
    ys,xs=np.nonzero(padded[:-1,1:-1]!=padded[1:,1:-1])
    for y,x in zip(ys.tolist(),xs.tolist()):
        a=y*stride+x;b=a+1
        add(padded[y+1,x+1],a,b);add(padded[y,x+1],b,a)
        graph[a].add(b);graph[b].add(a)
    ys,xs=np.nonzero(padded[1:-1,:-1]!=padded[1:-1,1:])
    for y,x in zip(ys.tolist(),xs.tolist()):
        a=y*stride+x;b=a+stride
        add(padded[y+1,x],a,b);add(padded[y+1,x+1],b,a)
        graph[a].add(b);graph[b].add(a)
    def xy(v):return (v%stride,v//stride)
    loops_by_color={}
    for color,outgoing in sorted(edges.items()):
        loops_by_color[color]=[]
        while outgoing:
            start=next(iter(outgoing));a=start;loop=[];previous=None
            while True:
                loop.append(a);choices=outgoing[a]
                if len(choices)==1 or previous is None:b=choices[0]
                else:
                    # At a diagonal contact choose the rightmost continuation.
                    ax,ay=xy(a);px,py=xy(previous)
                    dx,dy=ax-px,ay-py
                    def turn(v):
                        bx,by=xy(v);cross=dx*(by-ay)-dy*(bx-ax);dot=dx*(bx-ax)+dy*(by-ay)
                        return (2 if cross>0 else 1 if dot>0 else 0)
                    b=max(choices,key=turn)
                choices.remove(b)
                if not choices:del outgoing[a]
                previous,a=a,b
                if a==start:break
            loops_by_color[color].append(loop)
    coordinates={v:(v%stride,v//stride) for v in graph}
    keep=None
    if smooth:
        from boundary_smoothing import smooth as smooth_graph
        coordinates,keep=smooth_graph(graph,loops_by_color,stride,w,h,curve_tolerance,passes)
    def xy(v):return coordinates[v]
    def fmt(p):return f'{p[0]:.4f} {p[1]:.4f}'
    def middle(a,b):
        a,b=xy(a),xy(b);return ((a[0]+b[0])/2,(a[1]+b[1])/2)
    root=ET.Element('{'+NS+'}svg',{'width':str(original[0]),'height':str(original[1]),'viewBox':f'0 0 {w} {h}','version':'1.1','data-color-objects':'merged'})
    loops=segments=0;pieces=[]
    for color,color_loops in sorted(loops_by_color.items()):
        paths=[]
        for loop in color_loops:
            # Keep straight grid runs as a single segment. Never remove a junction.
            points=[]
            for i,v in enumerate(loop):
                u,t=loop[i-1],loop[(i+1)%len(loop)]
                if (v in keep) if keep is not None else (len(graph[v])!=2 or v-u!=t-v):points.append(v)
            if len(points)<3:continue
            data=['M'+fmt(middle(points[-1],points[0]))]
            for i,v in enumerate(points):
                before=middle(points[i-1],v);after=middle(v,points[(i+1)%len(points)]);corner=xy(v)
                # Limit corner rounding by adjacent half-edges; long runs stay straight.
                def near(p):
                    delta=(p[0]-corner[0],p[1]-corner[1]);length=max(abs(delta[0]),abs(delta[1]));f=min(1,(rounding if smooth and 0<corner[0]<w and 0<corner[1]<h else .5)/length) if length else 0
                    return (corner[0]+delta[0]*f,corner[1]+delta[1]*f)
                enter,leave=near(before),near(after)
                if i==0:data[0]='M'+fmt(enter if len(graph[v])==2 else corner)
                if len(graph[v])==2:
                    data.append('L'+fmt(enter))
                    c1=tuple((enter[j]+2*corner[j])/3 for j in (0,1));c2=tuple((leave[j]+2*corner[j])/3 for j in (0,1))
                    data.append('C'+fmt(c1)+' '+fmt(c2)+' '+fmt(leave))
                else:data.append('L'+fmt(corner))
                segments+=1
            # Close between the same rounded endpoints used by the neighbour.
            # A separately rounded midpoint could create a subpixel sliver.
            data.append('Z');path=' '.join(data);paths.append(path);loops+=1
        if paths:
            fill='#%02x%02x%02x'%tuple(palette[color]);g=ET.SubElement(root,'{'+NS+'}g',{'fill':fill,'id':'color-'+fill[1:]})
            data=' '.join(paths)
            ET.SubElement(g,'{'+NS+'}path',{'d':data,'fill':fill,'fill-rule':'nonzero'})
            pieces.append((fill,data))
    report={}
    if smooth:
        from vector_partition import audit_pieces
        try:audit_pieces(pieces,report)
        except ValueError as exc:
            fallback,stats=trace(labels,palette,original,smooth=False)
            document=ET.fromstring(fallback)
            audit_pieces([(p.get('fill'),p.get('d')) for p in document.iter('{'+NS+'}path')],report)
            stats['geometry_verified']=True;stats['geometry_audit']=report
            stats['shared_boundary_seconds']=time.perf_counter()-started
            stats['smoothing_fallback']=True;stats['smoothing_fallback_reason']=str(exc)
            return fallback,stats
    ET.register_namespace('',NS)
    return ET.tostring(root,encoding='unicode'),{'paths':loops,'color_groups':len(root),'shared_corners':segments,'shared_boundary_seconds':time.perf_counter()-started,'vector_layout':'shared boundary color groups','geometry_compute':'shared grid CPU',
        'geometry_verified':bool(smooth),'geometry_audit':report}
