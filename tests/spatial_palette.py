"""Runtime parity and integration checks for the opt-in photo segmentation."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
import numpy as np
from PIL import Image
import engine, accelerator
import spatial_palette as spatial

rng=np.random.default_rng(142)
gpu_cases=0
try:
    device=accelerator.gpu_runtime()[-1]
except Exception as exc:
    device=None
    print('GPU NOT TESTED:',exc)
for h,w in [(1,1),(1,37),(39,1),(17,19),(64,65)]:
    for count in [2,8,32,64]:
        a=rng.integers(0,256,(h,w,4),dtype=np.uint8)
        palette=rng.integers(0,256,(count,3),dtype=np.uint8)
        for strength,iterations in [(0,0),(0,2),(300,1),(700,2),(1500,3)]:
            cpu=spatial.assign_cpu(a,palette,strength,iterations)
            assert np.all(cpu[a[:,:,3]<128]==255)
            if strength==0:
                assert np.array_equal(cpu,accelerator.assign_cpu(a,palette,False,0))
            if device:
                gpu,meta=spatial.assign(a,palette,'gpu',strength,iterations)
                assert meta['compute']=='OpenCL GPU',meta
                assert np.array_equal(cpu,gpu),(h,w,count,strength,iterations)
                gpu_cases+=1

# A genuine blue-channel distance and equal-distance tie regression.
a=np.array([[[0,0,160,255],[0,0,150,255],[0,0,200,127]]],np.uint8)
palette=[[0,0,100],[0,0,200]]
assert spatial.assign_cpu(a,palette,0,2).tolist()==[[1,0,255]]

# High-contrast thin strokes and holes survive this parameter range.
a=np.zeros((41,43,4),np.uint8);a[:]=[255,255,255,255]
a[5:35,5:35,:3]=0;a[12:28,12:28,:3]=255;a[2:39,39,:3]=0
labels=spatial.assign_cpu(a,[[0,0,0],[255,255,255]],700,2)
assert np.array_equal(labels,accelerator.assign_cpu(a,[[0,0,0],[255,255,255]],False,0))

original=spatial.assign_gpu
def fail(*args,**kwargs):raise RuntimeError('simulated device failure')
spatial.assign_gpu=fail
fallback,meta=spatial.assign(a,[[0,0,0],[255,255,255]],'gpu')
assert meta['compute']=='OpenCV CPU' and 'simulated' in meta['gpu_fallback']
assert np.array_equal(fallback,labels)
spatial.assign_gpu=original

with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'photo.png';Image.fromarray(a).save(path)
    cfg={'category':'photo','palette':['#000000','#ffffff'],'detail':1,'compute':'cpu','photo_spatial':True}
    cpu,stats=engine.trace(path,cfg)
    assert stats['segmentation']=='spatial-experimental'
    if device:
        gpu,stats=engine.trace(path,{**cfg,'compute':'gpu'})
        assert stats['compute']=='OpenCL GPU' and gpu==cpu
    for category in ['aa','hard','photo']:
        cfg={'category':category,'compute':'cpu','detail':1}
        base,_=engine.trace(path,cfg)
        enabled,stats=engine.trace(path,{**cfg,'photo_spatial':True})
        assert enabled==base and stats.get('segmentation')!='spatial-experimental'
print({'ok':True,'actual_gpu_cases':gpu_cases,'device':device})
