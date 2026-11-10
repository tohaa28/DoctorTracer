"""Simplify shared chains once; preserve graph junctions and region cycles."""
import numpy as np
import time

def smooth(graph,loops,stride,width,height,tolerance=.5,passes=8,backend='cpu',metrics=None):
    started=time.perf_counter()
    vertices=list(graph);index={v:i for i,v in enumerate(vertices)}
    coords=np.array([(v%stride,v//stride) for v in vertices],float)
    # Smoothing an isolated 1-2 pixel cycle towards its centre erases holes/islands.
    pinned={v for paths in loops.values() for loop in paths if len(loop)<=8 and all(len(graph[u])==2 for u in loop) for v in loop}
    active=[v for v in vertices if v not in pinned and len(graph[v])==2 and 0<v%stride<width and 0<v//stride<height]
    positions=np.array([index[v] for v in active],int)
    neighbors=np.array([[index[u] for u in graph[v]] for v in active],int).reshape(-1,2)
    coordinates={v:tuple(coords[i]) for i,v in enumerate(vertices)}
    keep={v for v in vertices if len(graph[v])!=2};seen=set()
    chains=[]
    def simplify_cpu(chain):
        points=np.array([coordinates[v] for v in chain]);selected={0,len(chain)-1};stack=[(0,len(chain)-1)]
        while stack:
            left,right=stack.pop()
            if right-left<2:continue
            a,b=points[left],points[right];d=b-a;den=float(d@d);part=points[left+1:right]
            t=np.clip((part-a)@d/den,0,1) if den else np.zeros(len(part))
            error=((part-a-t[:,None]*d)**2).sum(1);k=int(error.argmax())
            if error[k]>tolerance**2:
                split=left+k+1;selected.add(split);stack.extend([(left,split),(split,right)])
        keep.update(chain[i] for i in selected)
    def ordered(v):
        def direction(u):
            d=u-v
            return 0 if d==1 else 1 if d==stride else 2 if d==-1 else 3
        return sorted(graph[v],key=direction)
    for start in vertices:
        if len(graph[start])==2:continue
        for nxt in ordered(start):
            if (start,nxt) in seen:continue
            chain=[start];a,b=start,nxt
            while True:
                seen.add((a,b));seen.add((b,a));chain.append(b)
                if len(graph[b])!=2:break
                a,b=b,next(v for v in graph[b] if v!=a)
            chains.append(chain)
    for start in vertices:
        for nxt in ordered(start):
            if (start,nxt) in seen:continue
            chain=[start];a,b=start,nxt
            while b!=start:
                seen.add((a,b));seen.add((b,a));chain.append(b)
                a,b=b,next(v for v in graph[b] if v!=a)
            seen.add((a,b));seen.add((b,a));half=len(chain)//2
            chains.append(chain[:half+1]);chains.append(chain[half:]+[start])
    accelerated=False;fallback=None
    if backend!='cpu' and len(coords):
        try:
            import gpu_contours
            ns=[(int(p),int(n[0]),int(n[1])) for p,n in zip(positions,neighbors)]
            coords,selected=gpu_contours.smooth(coords,ns,[[index[v] for v in chain] for chain in chains],tolerance,passes)
            coordinates={v:tuple(coords[i]) for i,v in enumerate(vertices)};keep.update(vertices[i] for i in selected);accelerated=True
        except Exception as exc:fallback=str(exc)
    if not accelerated:
        for _ in range(passes):coords[positions]=.5*coords[positions]+.25*coords[neighbors].sum(1)
        coordinates={v:tuple(coords[i]) for i,v in enumerate(vertices)}
        for chain in chains:simplify_cpu(chain)
    if metrics is not None:metrics.update(contour_compute='OpenCL GPU FP64' if accelerated else 'CPU',contour_gpu_fallback=fallback,chain_smoothing_seconds=time.perf_counter()-started,contour_chains=len(chains))
    # A small cycle must retain a filled interior after chain simplification.
    # This is global, so its neighbour uses every restored point as well.
    for color_loops in loops.values():
        for loop in color_loops:
            if sum(v in keep for v in loop)<3:
                keep.update(loop[i*len(loop)//4] for i in range(4))
    return coordinates,keep
