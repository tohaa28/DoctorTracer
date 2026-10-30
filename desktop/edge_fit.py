"""Bounded inverse-raster edge fit on a shared graph, followed by curve refit.

The local observation is a bilinear premultiplied RGBA reconstruction. A boundary
predicts equal coverage of its two inks. Junctions and tiny cycles stay pinned.
This is a local coverage objective, not a claim of globally optimal inversion.
"""
import numpy as np


def fit(coordinates,graph,loops,keep,labels,palette,source,radius=1.5,compute='cpu',metrics=None):
    h,w=labels.shape;stride=w+1
    if not coordinates or not len(palette):return coordinates,{},0
    pixels=source.astype(float)/255
    pixels[:,:,:3]*=pixels[:,:,3:4]
    inks=np.concatenate([np.asarray(palette,float)/255,np.ones((len(palette),1))],1)
    pinned={v for paths in loops.values() for loop in paths if len(loop)<=8 for v in loop}
    ids=[];pairs=[];normals=[];neighbors=[]
    for v in sorted(coordinates):
        x,y=v%stride,v//stride
        if v in pinned or len(graph[v])!=2 or not (1<x<w-1 and 1<y<h-1):continue
        colors=sorted(set(labels[y-1:y+1,x-1:x+1].ravel().tolist()))
        if len(colors)!=2 or colors[0]<0:continue
        a,b=inks[colors];delta=b-a
        if float(delta@delta)<.01:continue
        ns=sorted(graph[v]);t=np.asarray(coordinates[ns[1]])-coordinates[ns[0]]
        length=float(np.sqrt(t@t))
        if length<.1:continue
        ids.append(v);pairs.append((a,b));normals.append((-t[1]/length,t[0]/length));neighbors.append(ns)
    if not ids:return coordinates,{},0
    pairs=np.asarray(pairs);base=np.array([coordinates[v] for v in ids]);normal=np.asarray(normals)
    a=pairs[:,0];d=pairs[:,1]-a;den=(d*d).sum(1)
    gpu_loss=None
    if compute!='cpu':
        try:
            from gpu_edge_fit import evaluator
            gpu_loss=evaluator(source,a,d)
            if metrics is not None:metrics['edge_fit_compute']='OpenCL GPU FP64'
        except Exception as exc:
            if metrics is not None:metrics.update(edge_fit_compute='CPU',edge_fit_gpu_fallback=str(exc))
    def loss(points):
        nonlocal gpu_loss
        if gpu_loss is not None:
            try:return gpu_loss(points)
            except Exception as exc:
                gpu_loss=None
                if metrics is not None:metrics.update(edge_fit_compute='CPU',edge_fit_gpu_fallback=str(exc))

        xy=np.clip(points-.5,[0,0],[w-1.000001,h-1.000001]);ij=np.floor(xy).astype(int);f=xy-ij;x=ij[:,0];y=ij[:,1]
        observed=(pixels[y,x]*(1-f[:,0,None])*(1-f[:,1,None])+pixels[y,x+1]*f[:,0,None]*(1-f[:,1,None])+pixels[y+1,x]*(1-f[:,0,None])*f[:,1,None]+pixels[y+1,x+1]*f[:,0,None]*f[:,1,None])
        coverage=((observed-a)*d).sum(1)/den
        return (coverage-.5)**2
    best=loss(base);chosen=base.copy()
    for step in [-.25,-.125,.125,.25]:
        p=base+step*normal;cost=loss(p)+.02*step*step
        take=cost+1e-9<best;chosen[take]=p[take];best[take]=cost[take]
    out=dict(coordinates)
    for v,p in zip(ids,chosen):out[v]=tuple(p)
    # Select one radius per shared vertex, so reverse traversal is identical.
    previous={};following={}
    for paths in loops.values():
        for loop in paths:
            selected=[v for v in loop if v in keep]
            if len(selected)<3:continue
            for i,v in enumerate(selected):
                if v not in previous:previous[v]=selected[i-1];following[v]=selected[(i+1)%len(selected)]
    active=[i for i,v in enumerate(ids) if v in previous]
    radii={}
    if active:
        # Keep vector batches aligned with the observation pair arrays.
        before=np.array([out[previous.get(v,v)] for v in ids]);after=np.array([out[following.get(v,v)] for v in ids])
        corner=chosen;left=(before+corner)/2;right=(after+corner)/2
        def curve_cost(r):
            def near(p):
                delta=p-corner;length=np.max(np.abs(delta),axis=1)
                return corner+delta*np.minimum(1,r/np.maximum(length,1e-12))[:,None]
            enter,leave=near(left),near(right);value=np.zeros(len(ids))
            for t in [.25,.5,.75]:value+=loss((1-t)**2*enter+2*t*(1-t)*corner+t*t*leave)
            return value+.002*(r-radius)**2
        best=curve_cost(radius);selected=np.full(len(ids),radius)
        for r in [.5,1.,2.]:
            cost=curve_cost(r);take=cost+1e-9<best;best[take]=cost[take];selected[take]=r
        radii={ids[i]:float(selected[i]) for i in active}
    return out,radii,int(np.count_nonzero(np.any(chosen!=base,axis=1)))
