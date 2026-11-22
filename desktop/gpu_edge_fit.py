"""FP64 OpenCL evaluation of local inverse-raster coverage candidates."""
import numpy as np
import accelerator
_program=None
_context=None
SOURCE=r'''
#pragma OPENCL EXTENSION cl_khr_fp64 : enable
#pragma OPENCL FP_CONTRACT OFF
double4 pixel(__global const uchar4 *a,int i){uchar4 p=a[i];double alpha=p.w/255.;return (double4)(p.x/255.*alpha,p.y/255.*alpha,p.z/255.*alpha,alpha);}
__kernel void score(__global const uchar4 *source,__global const double2 *points,
 __global const double4 *inks,__global const double4 *delta,__global double *out,int w,int h,int n,int count){
 int i=get_global_id(0);if(i>=count)return;int k=i%n;double2 p=clamp(points[i]-.5,(double2)(0,0),(double2)(w-1.000001,h-1.000001));int x=(int)floor(p.x),y=(int)floor(p.y);double fx=p.x-x,fy=p.y-y;
 double4 observed=pixel(source,y*w+x)*(1-fx)*(1-fy)+pixel(source,y*w+x+1)*fx*(1-fy)+pixel(source,(y+1)*w+x)*(1-fx)*fy+pixel(source,(y+1)*w+x+1)*fx*fy;
 double4 d=delta[k],v=observed-inks[k];double coverage=(v.x*d.x+v.y*d.y+v.z*d.z+v.w*d.w)/(d.x*d.x+d.y*d.y+d.z*d.z+d.w*d.w);out[i]=(coverage-.5)*(coverage-.5);
}
'''


def evaluator(source,inks,delta):
    global _program,_context
    cl,ctx,queue,*_=accelerator.gpu_runtime()
    if not any('cl_khr_fp64' in d.extensions for d in ctx.devices):raise RuntimeError('GPU lacks FP64')
    if _context is not ctx:
        _program=cl.Program(ctx,SOURCE).build(options=['-cl-std=CL1.2']);_context=ctx
    f=cl.mem_flags
    src=cl.Buffer(ctx,f.READ_ONLY|f.COPY_HOST_PTR,hostbuf=np.ascontiguousarray(source,np.uint8))
    a=cl.Buffer(ctx,f.READ_ONLY|f.COPY_HOST_PTR,hostbuf=np.ascontiguousarray(inks,np.float64))
    d=cl.Buffer(ctx,f.READ_ONLY|f.COPY_HOST_PTR,hostbuf=np.ascontiguousarray(delta,np.float64))
    kernel=cl.Kernel(_program,'score');h,w=source.shape[:2];n=len(inks)
    def score(points):
        points=np.ascontiguousarray(points,np.float64);out=np.empty(points.shape[:-1],np.float64)
        p=cl.Buffer(ctx,f.READ_ONLY|f.COPY_HOST_PTR,hostbuf=points);o=cl.Buffer(ctx,f.WRITE_ONLY,out.nbytes)
        kernel(queue,(out.size,),None,src,p,a,d,o,np.int32(w),np.int32(h),np.int32(n),np.int32(out.size))
        cl.enqueue_copy(queue,out,o).wait();return out
    return score
