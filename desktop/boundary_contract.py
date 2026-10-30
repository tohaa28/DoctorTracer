"""Analytic shared-edge contract; no raster tolerance or gap-area allowance."""
import re
from collections import defaultdict

TOKEN=re.compile(r'[MLCZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?')

def _edge(a,b,oriented):
    return (min(a,b),1 if a<=b else -1) if oriented else min(a,b)

def segments(data,oriented=False):
    t=TOKEN.findall(data);i=0;cmd='';point=start=(0,0)
    while i<len(t):
        if t[i] in ('M','L','C','Z'):cmd=t[i];i+=1
        if cmd=='Z':
            if point!=start:yield _edge((0,*point,*start),(0,*start,*point),oriented)
            point=start;cmd='';continue
        n=6 if cmd=='C' else 2;v=tuple(round(float(x)*10000) for x in t[i:i+n]);i+=n
        if cmd=='M':point=start=v;cmd='L';continue
        if cmd=='L':
            if point!=v:yield _edge((0,*point,*v),(0,*v,*point),oriented)
        elif cmd=='C':
            if not (point==v[:2]==v[2:4]==v[4:]):yield _edge((1,*point,*v),(1,*v[4:],*v[2:4],*v[:2],*point),oriented)
        else:raise ValueError('Unsupported shared boundary command')
        point=v[-2:]

def verify(faces):
    owners=defaultdict(list)
    for color,data in faces:
        for key,direction in segments(data,True):owners[key].append((color,direction))
    bad=[key for key,values in owners.items() if len(values)!=2 or values[0][0]==values[1][0] or values[0][1]+values[1][1]!=0]
    if bad:raise ValueError(f'Shared boundary contract failed: {len(bad)} unmatched interfaces')
    return {'paired_edges':len(owners),'unmatched_edges':0,'boundary_contract':'analytic reversed primitives'}
