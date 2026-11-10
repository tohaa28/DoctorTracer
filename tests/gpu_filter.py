import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
import gpu_filter as f,accelerator,numpy as np
rng=np.random.default_rng(5)
try:device=accelerator.gpu_runtime()[-1]
except Exception:device=None
checks=0
for h,w in [(1,1),(1,9),(11,1),(17,19),(129,137)]:
    for _ in range(3):
        a=rng.integers(0,256,(h,w,4),dtype=np.uint8);cpu=f.cpu(a)
        assert np.array_equal(cpu[:,:,3],a[:,:,3]) and np.array_equal(cpu[a[:,:,3]<128],a[a[:,:,3]<128])
        if device:
            gpu,stats=f.apply(a,'gpu');assert stats['preprocess_compute']=='OpenCL GPU'
            assert np.array_equal(cpu,gpu);checks+=1
print({'ok':True,'actual_gpu_cases':checks,'device':device})
