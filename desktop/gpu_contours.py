"""Shared contour arithmetic on OpenCL, with exact double precision and CPU fallback.

Topology, junctions, holes and independent intersection audit remain authoritative.
No fast-math: shared vertices are computed once, not independently per colour.
"""
import time
import numpy as np
import accelerator

SOURCE=r'''
#pragma OPENCL EXTENSION cl_khr_fp64 : enable
#pragma OPENCL FP_CONTRACT OFF
__kernel void diffuse(__global const double2 *src,__global double2 *dst,
 __global const int4 *neighbors,int n){
 int i=get_global_id(0);if(i>=n)return;int4 ns=neighbors[i];
 dst[i]=ns.x<0?src[i]:0.5*src[i]+0.25*(src[ns.x]+src[ns.y]);
}
__kernel void simplify(__global const double2 *coords,__global const int *points,
 __global const int2 *chains,__global int2 *stack,__global uchar *keep,int n,double tol2){
 int ci=get_global_id(0);if(ci>=n)return;int2 chain=chains[ci];int offset=chain.x,len=chain.y;
 if(len<2)return;keep[offset]=1;keep[offset+len-1]=1;int top=0;
 stack[offset+top++]=(int2)(0,len-1);
 while(top){int2 range=stack[offset+--top];int left=range.x,right=range.y;if(right-left<2)continue;
  double2 a=coords[points[offset+left]],d=coords[points[offset+right]]-a;
  double den=d.x*d.x+d.y*d.y,best=-1.;int split=left;
  for(int j=left+1;j<right;j++){double2 delta=coords[points[offset+j]]-a;
   double t=den>0.?clamp((delta.x*d.x+delta.y*d.y)/den,0.,1.):0.;
   double2 error=delta-t*d;double e=error.x*error.x+error.y*error.y;
   if(e>best){best=e;split=j;}}
  if(best>tol2){keep[offset+split]=1;stack[offset+top++]=(int2)(left,split);stack[offset+top++]=(int2)(split,right);}
 }
}
double2 near_point(double2 p,double2 corner,double radius){double2 d=p-corner;
 double length=fmax(fabs(d.x),fabs(d.y));double f=length>0.?fmin(1.,radius/length):0.;return corner+d*f;}
__kernel void curves(__global const double2 *coords,__global const int4 *points,
 __global double2 *output,int n,double radius,int w,int h){
 int i=get_global_id(0);if(i>=n)return;int4 ids=points[i];double2 c=coords[ids.y];
 double r=c.x>0.&&c.x<w&&c.y>0.&&c.y<h?radius:0.5;
 double2 enter=near_point((coords[ids.x]+c)/2.,c,r),leave=near_point((c+coords[ids.z])/2.,c,r);
 output[5*i]=enter;output[5*i+1]=(enter+2.*c)/3.;output[5*i+2]=(leave+2.*c)/3.;output[5*i+3]=leave;output[5*i+4]=c;
}
'''
_program=None

def runtime():
    global _program
    cl,ctx,queue,*_=accelerator.gpu_runtime()
    if not ctx.devices[0].double_fp_config:raise RuntimeError('GPU contour arithmetic needs FP64')
    if _program is None:_program=cl.Program(ctx,SOURCE).build(options=['-cl-std=CL1.2'])
    return cl,ctx,queue,_program

def smooth(coords,neighbors,chains,tolerance,passes):
    """Return coordinates and selected flat-chain positions; caller unions shared IDs."""
    cl,ctx,q,program=runtime();f=cl.mem_flags
    coords=np.ascontiguousarray(coords,np.float64);ns=np.full((len(coords),4),-1,np.int32)
    for position,a,b in neighbors:ns[position,:2]=a,b
    flat=np.ascontiguousarray([v for chain in chains for v in chain],np.int32)
    ranges=np.empty((len(chains),2),np.int32);offset=0
    for i,chain in enumerate(chains):ranges[i]=offset,len(chain);offset+=len(chain)
    if any(len(chain)>65536 for chain in chains):raise RuntimeError('Contour chain exceeds GPU watchdog bound')
    src=cl.Buffer(ctx,f.READ_WRITE|f.COPY_HOST_PTR,hostbuf=coords);dst=cl.Buffer(ctx,f.READ_WRITE,coords.nbytes)
    nb=cl.Buffer(ctx,f.READ_ONLY|f.COPY_HOST_PTR,hostbuf=ns)
    diffuse=cl.Kernel(program,'diffuse')
    for _ in range(passes):diffuse(q,(len(coords),),None,src,dst,nb,np.int32(len(coords)));src,dst=dst,src
    selected=np.zeros(len(flat),np.uint8)
    if len(flat):
        ids=cl.Buffer(ctx,f.READ_ONLY|f.COPY_HOST_PTR,hostbuf=flat);rs=cl.Buffer(ctx,f.READ_ONLY|f.COPY_HOST_PTR,hostbuf=ranges)
        stack=cl.Buffer(ctx,f.READ_WRITE,len(flat)*8);flags=cl.Buffer(ctx,f.READ_WRITE|f.COPY_HOST_PTR,hostbuf=selected)
        cl.Kernel(program,'simplify')(q,(len(chains),),None,src,ids,rs,stack,flags,np.int32(len(chains)),np.float64(tolerance*tolerance))
        cl.enqueue_copy(q,selected,flags)
    out=np.empty_like(coords);cl.enqueue_copy(q,out,src).wait()
    return out,set(flat[selected!=0].tolist())

def curves(coordinates,points,radius,width,height):
    cl,ctx,q,program=runtime();f=cl.mem_flags
    coords=np.ascontiguousarray(coordinates,np.float64);ids=np.ascontiguousarray(points,np.int32)
    out=np.empty((len(ids),5,2),np.float64)
    if not len(ids):return out
    src=cl.Buffer(ctx,f.READ_ONLY|f.COPY_HOST_PTR,hostbuf=coords);index=cl.Buffer(ctx,f.READ_ONLY|f.COPY_HOST_PTR,hostbuf=ids)
    dst=cl.Buffer(ctx,f.WRITE_ONLY,out.nbytes)
    cl.Kernel(program,'curves')(q,(len(ids),),None,src,index,dst,np.int32(len(ids)),np.float64(radius),np.int32(width),np.int32(height))
    cl.enqueue_copy(q,out,dst).wait();return out
