"""Independent geometry checks for shared colour boundaries and holes."""
import sys,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
import numpy as np
import pathops
from shared_regions import trace,NS
from vector_partition import parse

rng=np.random.default_rng(418)
for case in range(103):
    labels=rng.integers(0,4,(7,8),dtype=np.uint8)
    if case==0:labels[:]=0;labels[2:5,2:6]=1;labels[3,3:5]=2
    if case==1:labels[:]=np.indices(labels.shape).sum(0)%2
    if case==2:labels[:]=255;labels[1:6,1:7]=0;labels[2:5,2:6]=1
    svg,stats=trace(labels,[(220,0,0),(0,180,0),(0,0,200),(220,0,0)],(8,7))
    root=ET.fromstring(svg);paths=[parse(p.get('d')) for p in root.iter('{'+NS+'}path')]
    assert len(root)<=3
    for i,a in enumerate(paths):
        for b in paths[i+1:]:
            overlap=pathops.op(a,b,pathops.PathOp.INTERSECTION)
            assert abs(overlap.area)<1e-7,(case,overlap.area)
    # Every source pixel centre retains its colour; junction rounding never
    # removes a pixel centre or creates an internal gap at that centre.
    colors=[g.get('fill') for g in root]
    expected=['#dc0000','#00b400','#0000c8','#dc0000']
    for y,x in np.ndindex(labels.shape):
        owners=[colors[i] for i,p in enumerate(paths) if p.contains((x+.5,y+.5))]
        assert owners==([] if labels[y,x]==255 else [expected[labels[y,x]]]),(case,x,y,owners)
print('103 shared-boundary maps: no intersections; pixel ownership, holes, diagonals and duplicate colors passed')

for case in range(50):
    labels=rng.integers(0,3,(7,8),dtype=np.uint8)
    svg,stats=trace(labels,[(220,0,0),(0,180,0),(0,0,200)],(8,7),smooth=True)
    root=ET.fromstring(svg);paths=[parse(p.get('d')) for p in root.iter('{'+NS+'}path')]
    for i,a in enumerate(paths):
        for b in paths[i+1:]:assert abs(pathops.op(a,b,pathops.PathOp.INTERSECTION).area)<1e-7
    assert sum(abs(p.area) for p in paths)>55.7,(case,[p.area for p in paths])
print('50 smoothed maps: disjoint colours and full interior coverage passed')

labels=np.array([[0,255,299],[-1,299,255]],np.int32)
palette=[(i%256,100*(i//256),30) for i in range(300)]
svg,stats=trace(labels,palette,(3,2))
assert stats['color_groups']==3
print('Signed region IDs support more than 255 colours and transparent pixels')
