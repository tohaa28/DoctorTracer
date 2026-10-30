import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
import numpy as np
from gpu_meanshift import cpu,gpu,native_cpu
rng=np.random.default_rng(42)
for i in range(24):
    a=rng.integers(0,256,(1+i%7,1+i%9,4),dtype=np.uint8)
    if i%2:a[:,:,:3]//=8
    radius=i%4;threshold=[0,20,80,255][i%4];iterations=1+i%5
    x=cpu(a,radius,threshold,iterations);y=gpu(a,radius,threshold,iterations)
    assert np.array_equal(x,y),(i,np.max(abs(x.astype(int)-y)))
    assert np.array_equal(x,native_cpu(a,radius,threshold,iterations)),i
print('24 NumPy/native CPU/OpenCL mode-filter cases are byte-identical, including alpha and borders')
