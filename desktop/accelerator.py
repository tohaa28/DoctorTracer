"""Exact integer palette assignment, optional OpenCL GPU and SIMD CPU fallback."""
import time
import numpy as np
import cv2

SOURCE=r'''
__kernel void nearest(__global const uchar4 *rgba, __global const uchar4 *pal,
 int count,int n,__global uchar *labels,__global int *distance){
 int i=get_global_id(0);if(i>=n)return;uchar4 v=rgba[i];int best=2147483647;uchar label=0;
 for(int c=0;c<count;c++){int3 d=convert_int3(v.xyz)-convert_int3(pal[c].xyz);int dd=d.x*d.x+d.y*d.y+d.z*d.z;if(dd<best){best=dd;label=c;}}
 labels[i]=label;distance[i]=best;
}
__kernel void horizontal(__global const uchar4 *rgba,__global const uchar *labels,
 __global const int *distance,int w,int h,int radius,__global ulong *rows){
 int i=get_global_id(0);if(i>=w*h)return;int x=i%w;int y=i/w;ulong mask=0;
 for(int xx=max(0,x-radius);xx<=min(w-1,x+radius);xx++){int j=y*w+xx;if(rgba[j].w>127 && distance[j]<576)mask|=((ulong)1<<labels[j]);}rows[i]=mask;
}
__kernel void refine(__global const uchar4 *rgba,__global const uchar4 *pal,int count,
 __global const uchar *labels,__global const ulong *rows,int w,int h,int radius,
 __global uchar *result){
 int i=get_global_id(0);if(i>=w*h)return;int x=i%w;int y=i/w;ulong mask=0;
 for(int yy=max(0,y-radius);yy<=min(h-1,y+radius);yy++)mask|=rows[yy*w+x];
 uchar4 v=rgba[i];int best=2147483647;uchar label=labels[i];
 for(int c=0;c<count;c++)if(mask&((ulong)1<<c)){int3 d=convert_int3(v.xyz)-convert_int3(pal[c].xyz);int dd=d.x*d.x+d.y*d.y+d.z*d.z;if(dd<best){best=dd;label=c;}}
 if(label!=labels[i]){
  int mixture=0;
  for(int l=0;l<count&&!mixture;l++)if(mask&((ulong)1<<l))
   for(int r=l+1;r<count;r++)if(mask&((ulong)1<<r)){
    long3 d=convert_long3(pal[r].xyz)-convert_long3(pal[l].xyz);
    long3 e=convert_long3(v.xyz)-convert_long3(pal[l].xyz);
    long den=d.x*d.x+d.y*d.y+d.z*d.z,dot=e.x*d.x+e.y*d.y+e.z*d.z;
    if(den>0&&dot>0&&dot<den&&
       (e.x*e.x+e.y*e.y+e.z*e.z)*den-dot*dot<=64*den){mixture=1;break;}
   }
  if(!mixture)label=labels[i];
 }
 result[i]=v.w<128?255:label;
}
'''

_runtime=None
_failure=None

def gpu_runtime():
    global _runtime,_failure
    if _runtime:return _runtime
    if _failure:raise RuntimeError(_failure)
    try:
        import pyopencl as cl
        devices=[d for p in cl.get_platforms() for d in p.get_devices(device_type=cl.device_type.GPU)]
        if not devices:raise RuntimeError('No OpenCL GPU')
        device=max(devices,key=lambda d:d.max_compute_units);ctx=cl.Context([device]);queue=cl.CommandQueue(ctx)
        program=cl.Program(ctx,SOURCE).build(options=['-cl-std=CL1.2'])
        _runtime=(cl,ctx,queue,cl.Kernel(program,'nearest'),cl.Kernel(program,'horizontal'),cl.Kernel(program,'refine'),device.name)
        return _runtime
    except Exception as exc:
        _failure=str(exc);raise

def assign_cpu(a,palette,aa,radius):
    rgb=np.ascontiguousarray(a[:,:,:3]);pal=np.asarray(palette,dtype=np.uint8)
    # OpenCV's SIMD implementation avoids a H*W*K*3 temporary array.
    distances,indices=cv2.batchDistance(rgb.reshape(-1,3),pal,cv2.CV_32F,normType=cv2.NORM_L2SQR,K=1)
    labels=indices.reshape(rgb.shape[:2]).astype(np.uint8);distance=distances.reshape(rgb.shape[:2])
    if aa:
        best=np.full(labels.shape,np.inf,np.float32);refined=labels.copy();kernel=np.ones((radius*2+1,radius*2+1),np.uint8)
        channels=[rgb[:,:,i].astype(np.int32) for i in range(3)];supports=[]
        for i,color in enumerate(pal):
            allowed=cv2.dilate(((labels==i)&(distance<576)&(a[:,:,3]>127)).astype(np.uint8),kernel)>0
            supports.append(allowed)
            d=sum((channels[c]-int(color[c]))**2 for c in range(3))
            use=allowed&(d<best);refined[use]=i;best[use]=d[use]
        changed=(refined!=labels)&(a[:,:,3]>127)
        # Neighborhood support is only evidence for antialias mixtures. A lone
        # nearby ink must not replace a closer shaded foreground color.
        values=rgb[changed].astype(np.int64);mixture=np.zeros(len(values),bool)
        local=[s[changed] for s in supports];inks=pal.astype(np.int64)
        for l in range(len(inks)):
            e=values-inks[l];e2=(e*e).sum(1)
            for r in range(l+1,len(inks)):
                d=inks[r]-inks[l];den=int(d@d)
                if not den:continue
                dot=e@d
                mixture|=local[l]&local[r]&(dot>0)&(dot<den)&(e2*den-dot*dot<=64*den)
        keep=np.zeros(labels.shape,bool);keep[changed]=mixture
        labels=np.where(keep,refined,labels).astype(np.uint8)
    labels[a[:,:,3]<128]=255
    return labels

def assign_gpu(a,palette,aa,radius):
    cl,ctx,queue,nearest,horizontal,refine,name=gpu_runtime();flags=cl.mem_flags
    a=np.ascontiguousarray(a,dtype=np.uint8);h,w=a.shape[:2];n=w*h
    pal=np.zeros((len(palette),4),np.uint8);pal[:,:3]=palette
    src=cl.Buffer(ctx,flags.READ_ONLY|flags.COPY_HOST_PTR,hostbuf=a);inks=cl.Buffer(ctx,flags.READ_ONLY|flags.COPY_HOST_PTR,hostbuf=pal)
    labels=cl.Buffer(ctx,flags.READ_WRITE,n);distance=cl.Buffer(ctx,flags.READ_WRITE,n*4)
    nearest(queue,(n,),None,src,inks,np.int32(len(pal)),np.int32(n),labels,distance)
    if aa:
        rows=cl.Buffer(ctx,flags.READ_WRITE,n*8);result=cl.Buffer(ctx,flags.WRITE_ONLY,n)
        horizontal(queue,(n,),None,src,labels,distance,np.int32(w),np.int32(h),np.int32(radius),rows)
        refine(queue,(n,),None,src,inks,np.int32(len(pal)),labels,rows,np.int32(w),np.int32(h),np.int32(radius),result)
    else:result=labels
    out=np.empty((h,w),np.uint8);cl.enqueue_copy(queue,out,result).wait();out[a[:,:,3]<128]=255
    return out,name

def assign(a,palette,aa=True,radius=3,backend='auto'):
    started=time.perf_counter();fallback=None
    if backend in ('auto','gpu') and len(palette)<=64 and (backend=='gpu' or a.shape[0]*a.shape[1]>=500_000):
        try:
            labels,name=assign_gpu(a,palette,aa,radius)
            return labels,{'device':name,'compute':'OpenCL GPU','assignment_seconds':time.perf_counter()-started}
        except Exception as exc:fallback=str(exc)
    labels=assign_cpu(a,palette,aa,radius)
    return labels,{'compute':'OpenCV CPU','gpu_fallback':fallback,'assignment_seconds':time.perf_counter()-started}
