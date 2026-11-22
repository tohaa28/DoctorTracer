"""Independent integer overlap audit, spatially clipped with winding preserved."""
import math
from collections import defaultdict
import pyclipper as pc
SCALE=10_000_000
SPAN=128*SCALE


def audit(polygons_by_group,report=None):
    tiles=defaultdict(lambda:defaultdict(list))
    for group,paths in enumerate(polygons_by_group):
        for path in paths:
            x0=min(p[0] for p in path);x1=max(p[0] for p in path);y0=min(p[1] for p in path);y1=max(p[1] for p in path)
            for y in range(y0//SPAN,y1//SPAN+1):
                for x in range(x0//SPAN,x1//SPAN+1):tiles[x,y][group].append(path)
    areas=defaultdict(float);pairs=set();checks=0
    for (x,y),groups in tiles.items():
        rect=[(x*SPAN,y*SPAN),((x+1)*SPAN,y*SPAN),((x+1)*SPAN,(y+1)*SPAN),(x*SPAN,(y+1)*SPAN)];local=[]
        for group,paths in sorted(groups.items()):
            clip=pc.Pyclipper();clip.AddPaths(paths,pc.PT_SUBJECT,True);clip.AddPath(rect,pc.PT_CLIP,True)
            clipped=clip.Execute(pc.CT_INTERSECTION,pc.PFT_NONZERO,pc.PFT_NONZERO)
            if not clipped:continue
            bounds=(min(p[0] for path in clipped for p in path),min(p[1] for path in clipped for p in path),max(p[0] for path in clipped for p in path),max(p[1] for path in clipped for p in path))
            for other,previous,b in local:
                if bounds[0]>=b[2] or bounds[2]<=b[0] or bounds[1]>=b[3] or bounds[3]<=b[1]:continue
                c=pc.Pyclipper();c.AddPaths(clipped,pc.PT_SUBJECT,True);c.AddPaths(previous,pc.PT_CLIP,True)
                intersection=c.Execute(pc.CT_INTERSECTION,pc.PFT_NONZERO,pc.PFT_NONZERO);checks+=1;key=(other,group);pairs.add(key)
                areas[key]+=abs(sum(pc.Area(p) for p in intersection))/SCALE**2
                if areas[key]>.000099:
                    # Confirm near-threshold / positive results on original full groups.
                    exact=pc.Pyclipper();exact.AddPaths(polygons_by_group[group],pc.PT_SUBJECT,True);exact.AddPaths(polygons_by_group[other],pc.PT_CLIP,True)
                    full=exact.Execute(pc.CT_INTERSECTION,pc.PFT_NONZERO,pc.PFT_NONZERO);area=abs(sum(pc.Area(p) for p in full))/SCALE**2
                    if area>.0001:raise ValueError(f'Vector overlap detected by independent integer audit: {area} px2, pair {group}/{other}')
            local.append((group,clipped,bounds))
    if report is not None:report.update(pairs_checked=len(pairs),tile_pair_checks=checks,audit_tiles=len(tiles),max_intersection_area_px2=max(areas.values(),default=0.),tolerance_px2=.0001,audit_compute='tiled integer CPU')
    return len(pairs)
