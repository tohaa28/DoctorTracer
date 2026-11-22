import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
import numpy as np
from region_merge import merge

labels=np.array([[0,0,1,1,2,2],[0,0,1,1,2,2],[-1,-1,-1,-1,-1,-1]],np.int32)
a,p=merge(labels,[(100,100,100),(102,100,100),(250,0,0)],2)
assert np.all(a[:2,:4]==a[0,0]);assert a[0,4]!=a[0,0]
assert (a[2]==-1).all();assert p[a[0,0]]==[101,100,100]
assert np.array_equal(a,merge(labels,[(100,100,100),(102,100,100),(250,0,0)],2)[0])
# Disconnected islands separated by transparency must never be joined.
a,p=merge(np.array([[0,-1,1]],np.int32),[(10,0,0),(11,0,0)],1)
assert a[0,0]!=a[0,2] and len(p)==2
print('Adjacent Ward merges preserve transparency, topology, means and deterministic ordering')
