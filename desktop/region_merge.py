"""Merge adjacent photo regions by their increase in RGB squared error."""
import heapq
import numpy as np

def merge(labels,palette,target):
    n=len(palette)
    if n<=target:return labels,palette
    visible=labels>=0;areas=np.bincount(labels[visible],minlength=n).astype(float)
    sums=np.asarray(palette,dtype=float)*areas[:,None]
    parent=np.arange(n);versions=np.zeros(n,int);neighbors=[set() for _ in range(n)]
    pairs=np.concatenate([np.stack([labels[:-1].ravel(),labels[1:].ravel()],1),np.stack([labels[:,:-1].ravel(),labels[:,1:].ravel()],1)])
    pairs=pairs[(pairs[:,0]>=0)&(pairs[:,1]>=0)&(pairs[:,0]!=pairs[:,1])]
    pairs=np.unique(np.sort(pairs,axis=1),axis=0);heap=[]
    def cost(a,b):
        d=sums[a]/areas[a]-sums[b]/areas[b]
        return float((d@d)*areas[a]*areas[b]/(areas[a]+areas[b]))
    def push(a,b):
        if a>b:a,b=b,a
        heapq.heappush(heap,(cost(a,b),a,b,int(versions[a]),int(versions[b])))
    for a,b in pairs:
        a,b=int(a),int(b);neighbors[a].add(b);neighbors[b].add(a);push(a,b)
    remaining=n
    while remaining>target and heap:
        _,a,b,va,vb=heapq.heappop(heap)
        if parent[a]!=a or parent[b]!=b or versions[a]!=va or versions[b]!=vb:continue
        parent[b]=a;areas[a]+=areas[b];sums[a]+=sums[b];versions[a]+=1;remaining-=1
        adjacent=(neighbors[a]|neighbors[b])-{a,b};neighbors[a]=adjacent;neighbors[b]=set()
        for c in adjacent:
            neighbors[c].discard(b);neighbors[c].add(a);push(a,c)
    for i in range(n):
        while parent[i]!=parent[parent[i]]:parent[i]=parent[parent[i]]
    roots=sorted(set(parent.tolist()));index={r:i for i,r in enumerate(roots)}
    remap=np.array([index[int(r)] for r in parent],np.int32);out=np.full(labels.shape,-1,np.int32);out[visible]=remap[labels[visible]]
    colors=[np.rint(sums[r]/areas[r]).astype(int).tolist() for r in roots]
    return out,colors
