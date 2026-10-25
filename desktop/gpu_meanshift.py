"""Integer joint spatial/colour mode filter, identical CPU and OpenCL paths.

This is deliberately separate from OpenCV's pyramidal implementation: changing
the filter changes segmentation, so the selected algorithm is reported.
"""
import time
import numpy as np
import accelerator
import ctypes as C
import sys
from pathlib import Path
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

SOURCE=r'''
__kernel void modes(__global const uchar4 *src,__global uchar4 *dst,
 int w,int h,int radius,int range2,int iterations){
 int i=get_global_id(0);if(i>=w*h)return;uchar4 original=src[i];
 if(original.w<128){dst[i]=original;return;}
 int x=i%w,y=i/w;int3 c=convert_int3(original.xyz);
 for(int k=0;k<iterations;k++){
  int sx=0,sy=0,n=0;int3 sum=(int3)(0);
  for(int yy=max(0,y-radius);yy<=min(h-1,y+radius);yy++)
   for(int xx=max(0,x-radius);xx<=min(w-1,x+radius);xx++){
    uchar4 v=src[yy*w+xx];if(v.w<128)continue;
    int3 d=convert_int3(v.xyz)-c;
    if(d.x*d.x+d.y*d.y+d.z*d.z>range2)continue;
    n++;sx+=xx;sy+=yy;sum+=convert_int3(v.xyz);
   }
  if(!n)break;
  int nx=(sx+n/2)/n,ny=(sy+n/2)/n;int3 nc=(sum+n/2)/n;
  uint3 delta=abs(nc-c);
  int done=nx==x && ny==y && delta.x+delta.y+delta.z==0;
  x=nx;y=ny;c=nc;if(done)break;
 }
 dst[i]=(uchar4)(convert_uchar3(c),original.w);
}
'''
_kernel=None

@lru_cache(maxsize=1)
def native_runtime():
    path=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'vendor/filters/photo_modes.dll'
    lib=C.CDLL(str(path));fn=lib.doctor_modes
    fn.argtypes=[C.POINTER(C.c_uint8),C.POINTER(C.c_uint8)]+[C.c_int]*7;fn.restype=None
    return lib,fn

def native_cpu(a,radius=5,color_range=20,iterations=5):
    _,fn=native_runtime();a=np.ascontiguousarray(a,np.uint8);out=np.empty_like(a);h,w=a.shape[:2]
    workers=min(4,h);bounds=np.linspace(0,h,workers+1,dtype=int)
    def rows(i):fn(a.ctypes.data_as(C.POINTER(C.c_uint8)),out.ctypes.data_as(C.POINTER(C.c_uint8)),w,h,radius,color_range**2,iterations,int(bounds[i]),int(bounds[i+1]))
    with ThreadPoolExecutor(max_workers=workers) as pool:list(pool.map(rows,range(workers)))
    return out

def cpu(a,radius=5,color_range=20,iterations=5):
    h,w=a.shape[:2];result=a.copy();rgb=a[:,:,:3].astype(np.int32)
    for oy,ox in np.ndindex(h,w):
        if a[oy,ox,3]<128:continue
        x,y=ox,oy;c=rgb[y,x].copy()
        for _ in range(iterations):
            x0,x1=max(0,x-radius),min(w,x+radius+1);y0,y1=max(0,y-radius),min(h,y+radius+1)
            patch=rgb[y0:y1,x0:x1];d=patch-c
            take=((d*d).sum(2)<=color_range**2)&(a[y0:y1,x0:x1,3]>=128)
            yy,xx=np.nonzero(take);n=len(xx)
            if not n:break
            nx=(int(xx.sum())+n*x0+n//2)//n;ny=(int(yy.sum())+n*y0+n//2)//n
            nc=(patch[take].sum(0)+n//2)//n
            done=nx==x and ny==y and np.array_equal(nc,c)
            x,y,c=nx,ny,nc
            if done:break
        result[oy,ox,:3]=c
    return result

def gpu(a,radius=5,color_range=20,iterations=5):
    global _kernel
    cl,ctx,queue,*_=accelerator.gpu_runtime()
    if _kernel is None:_kernel=cl.Kernel(cl.Program(ctx,SOURCE).build(options=['-cl-std=CL1.2']),'modes')
    a=np.ascontiguousarray(a,np.uint8);h,w=a.shape[:2];f=cl.mem_flags
    src=cl.Buffer(ctx,f.READ_ONLY|f.COPY_HOST_PTR,hostbuf=a);dst=cl.Buffer(ctx,f.WRITE_ONLY,a.nbytes)
    _kernel(queue,(w*h,),None,src,dst,*map(np.int32,(w,h,radius,color_range**2,iterations)))
    out=np.empty_like(a);cl.enqueue_copy(queue,out,dst).wait();return out

def apply(a,backend='gpu',radius=5,color_range=20,iterations=5):
    if not 0<=radius<=12 or not 0<=color_range<=255 or not 1<=iterations<=20:raise ValueError('Invalid mode filter parameters')
    started=time.perf_counter();fallback=None
    if backend!='cpu':
        try:
            result=gpu(a,radius,color_range,iterations)
            return result,{'mode_filter_compute':'OpenCL GPU','mode_filter_seconds':time.perf_counter()-started}
        except Exception as exc:fallback=str(exc)
    try:result=native_cpu(a,radius,color_range,iterations);implementation='native CPU'
    except OSError:result=cpu(a,radius,color_range,iterations);implementation='NumPy reference CPU'
    return result,{'mode_filter_compute':implementation,'mode_filter_seconds':time.perf_counter()-started,'mode_filter_fallback':fallback}

