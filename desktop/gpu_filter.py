"""Deterministic alpha-aware bilateral preprocessing on CPU/OpenCL."""
import time
import numpy as np
import accelerator

SOURCE=r'''
int reflect(int i,int size){if(size==1)return 0;int period=2*size-2;i=((i%period)+period)%period;return min(i,period-i);}
__kernel void bilateral(__global const uchar4 *src,__global uchar4 *out,
 __global const ushort *weights,int w,int h){
 int i=get_global_id(0);if(i>=w*h)return;uchar4 center=src[i];
 if(center.w<128){out[i]=center;return;}
 int x=i%w,y=i/w;uint3 sum=(uint3)(0);uint total=0;
 for(int dy=-2;dy<=2;dy++)for(int dx=-2;dx<=2;dx++){
  int r=dx*dx+dy*dy;if(r>4)continue;
  uchar4 neighbor=src[reflect(y+dy,h)*w+reflect(x+dx,w)];if(neighbor.w<128)continue;
  uint3 delta=abs(convert_int3(center.xyz)-convert_int3(neighbor.xyz));
  int d=delta.x+delta.y+delta.z;uint weight=weights[r*766+d];
  sum+=convert_uint3(neighbor.xyz)*weight;total+=weight;
 }
 out[i]=(uchar4)(convert_uchar3((sum+total/2)/total),center.w);
}
'''
DIST=np.arange(766,dtype=np.float64)
WEIGHTS=np.stack([np.rint(4096*np.exp(-DIST*DIST/(2*25**2)-r/(2*3**2))) for r in range(5)]).astype(np.uint16)
_kernel=None

def cpu(a):
    h,w=a.shape[:2];total=np.zeros((h,w),np.uint32);summed=np.zeros((h,w,3),np.uint32)
    def reflected(size):
        if size==1:return np.zeros(5,dtype=int)
        i=np.arange(-2,size+2)%(2*size-2)
        return np.minimum(i,2*size-2-i)
    padded=a[reflected(h)[:,None],reflected(w)[None,:]]
    for dy in range(-2,3):
        for dx in range(-2,3):
            r=dx*dx+dy*dy
            if r>4:continue
            neighbor=padded[dy+2:dy+2+h,dx+2:dx+2+w]
            distance=np.abs(a[:,:,:3].astype(np.int16)-neighbor[:,:,:3].astype(np.int16)).sum(2)
            weight=WEIGHTS[r,distance].astype(np.uint32)*(neighbor[:,:,3]>=128)
            total+=weight;summed+=neighbor[:,:,:3].astype(np.uint32)*weight[:,:,None]
    result=a.copy();visible=a[:,:,3]>=128
    result[:,:,:3][visible]=((summed[visible]+total[visible,None]//2)//total[visible,None]).astype(np.uint8)
    return result

def gpu(a):
    global _kernel
    cl,ctx,queue,*_=accelerator.gpu_runtime()
    if _kernel is None:_kernel=cl.Kernel(cl.Program(ctx,SOURCE).build(options=['-cl-std=CL1.2']),'bilateral')
    rgba=np.ascontiguousarray(a);h,w=a.shape[:2];f=cl.mem_flags
    src=cl.Buffer(ctx,f.READ_ONLY|f.COPY_HOST_PTR,hostbuf=rgba)
    weights=cl.Buffer(ctx,f.READ_ONLY|f.COPY_HOST_PTR,hostbuf=WEIGHTS)
    output=cl.Buffer(ctx,f.WRITE_ONLY,rgba.nbytes)
    _kernel(queue,(w*h,),None,src,output,weights,np.int32(w),np.int32(h))
    result=np.empty_like(rgba);cl.enqueue_copy(queue,result,output).wait();return result

def apply(a,backend='auto'):
    started=time.perf_counter();fallback=None
    if backend=='gpu' or (backend=='auto' and a.shape[0]*a.shape[1]>=32768):
        try:return gpu(a),{'preprocess_compute':'OpenCL GPU','preprocess_seconds':time.perf_counter()-started}
        except Exception as exc:fallback=str(exc)
    return cpu(a),{'preprocess_compute':'CPU','preprocess_fallback':fallback,'preprocess_seconds':time.perf_counter()-started}
