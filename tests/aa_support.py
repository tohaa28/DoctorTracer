"""Neighborhood evidence must not turn shaded foreground into thick dark ink."""
import sys,json,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from accelerator import assign_cpu,assign_gpu
out=ROOT/'build/aa-support';out.mkdir(exist_ok=True);jobs=[]
for alpha in [False,True]:
    a=np.full((16,24,4),[160,0,0,255],np.uint8);a[:,:4]=[12,1,1,255]
    if alpha:a[:2,:,3]=0
    palette=[[12,1,1],[228,0,0],[253,212,1],[253,251,229]]
    labels=assign_cpu(a,palette,True,3);raw=assign_cpu(a,palette,False,3)
    assert np.array_equal(labels,raw),'Shaded foreground expanded into black'
    gpu,_=assign_gpu(a,palette,True,3);assert np.array_equal(labels,gpu)
    key='shading-'+str(alpha);(out/(key+'.rgba')).write_bytes(a.tobytes());(out/(key+'.labels')).write_bytes(labels.tobytes());jobs.append({'key':key,'w':24,'h':16,'palette':palette})
# A genuine black/white mixture must still reject an unsupported gray ink.
a=np.full((16,24,4),[255,255,255,255],np.uint8);a[:,:10]=[0,0,0,255];a[:,10]=[125,125,125,255]
palette=[[0,0,0],[255,255,255],[160,160,160]];labels=assign_cpu(a,palette,True,3)
assert np.all(assign_cpu(a,palette,False,3)[:,10]==2) and np.all(labels[:,10]==0)
gpu,_=assign_gpu(a,palette,True,3);assert np.array_equal(labels,gpu)
(out/'mixture.rgba').write_bytes(a.tobytes());(out/'mixture.labels').write_bytes(labels.tobytes());jobs.append({'key':'mixture','w':24,'h':16,'palette':palette})
(out/'jobs.json').write_text(json.dumps(jobs),encoding='utf8')
subprocess.run(['node','tests/aa_support.mjs'],cwd=ROOT,check=True)
print('PASS: shading retained, true antialias restriction retained, CPU/OpenCL/Rust exact')
