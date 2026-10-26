"""Palette proposals: preserve interior inks; temper area bias for photographs.

Only proposals change. Explicit user RGB entries are never silently rewritten.
Histogram order, half-up rounding and sample budget match desktop_palette.rs.
"""
import numpy as np


def discover(a, limit, legacy):
    inks=legacy(a,0,False)
    pixels=a[:,:,:3][a[:,:,3]>=128]
    if not len(pixels):return [[255,255,255]]
    sample=pixels[::max(1,len(pixels)//60000)]
    if len(inks)<=limit:
        good=np.zeros(len(sample),bool)
        for ink in inks:
            delta=sample.astype(np.int32)-ink
            good|=(delta*delta).sum(1)<=576
        if np.mean(good)>=.96:return inks
        # A small illustration can have many antialias pixels but few real inks.
        # Accept mixtures only when interior pixels still explain most area.
        if np.mean(good)>=.75:
            explained=good.copy();rgb=sample.astype(float)
            for i,left in enumerate(inks):
                for right in inks[i+1:]:
                    left=np.asarray(left,float);d=np.asarray(right,float)-left;den=float(d@d)
                    if not den:continue
                    t=np.clip((rgb-left)@d/den,0,1)
                    explained|=((rgb-left-t[:,None]*d)**2).sum(1)<=64
            if np.mean(explained)>=.995:return inks
    keys=(sample.astype(np.int32)//8)@np.array([1024,32,1])
    counts=np.bincount(keys,minlength=32768)
    sums=np.stack([np.bincount(keys,weights=sample[:,j],minlength=32768) for j in range(3)],1)
    active=counts>0
    colors=np.floor(sums[active]/counts[active,None]+.5).astype(np.uint8)
    weights=counts[active].astype(float)**.75
    repeats=np.maximum(1,np.floor(weights*60000/weights.sum()+.5)).astype(int)
    rgb=np.repeat(colors,repeats,axis=0)
    rgba=np.concatenate([rgb,np.full((len(rgb),1),255,np.uint8)],1)[None]
    return legacy(rgba,limit,True,attempts=5)
