// SPDX-License-Identifier: MIT
// Exact dyadic shared-grid diffusion: integer arithmetic avoids float32 drift.
import {gpuDevice} from './gpu.js?v=0.19.0';
const shader=`
struct Params{w:u32,h:u32,scale:u32,n:u32}
@group(0) @binding(0) var<storage,read> labels:array<i32>;
@group(0) @binding(1) var<storage,read_write> graph:array<u32>;
@group(0) @binding(2) var<storage,read_write> source:array<vec2<u32>>;
@group(0) @binding(3) var<storage,read_write> destination:array<vec2<u32>>;
@group(0) @binding(4) var<storage,read_write> neighbors:array<vec2<u32>>;
@group(0) @binding(5) var<uniform> p:Params;
fn ink(x:i32,y:i32)->i32{if(x<0||y<0||x>=i32(p.w)||y>=i32(p.h)){return -1;}return labels[u32(y)*p.w+u32(x)];}
fn next(v:u32,d:u32)->u32{switch d{case 0u:{return v+1u;}case 1u:{return v+p.w+1u;}case 2u:{return v-1u;}default:{return v-p.w-1u;}}}
@compute @workgroup_size(128) fn edges(@builtin(global_invocation_id) id:vec3<u32>){
 let v=id.x;if(v>=p.n){return;}let x=i32(v%(p.w+1u));let y=i32(v/(p.w+1u));var mask=0u;
 if(x<i32(p.w)&&ink(x,y-1)!=ink(x,y)){mask|=1u;}
 if(y<i32(p.h)&&ink(x-1,y)!=ink(x,y)){mask|=2u;}
 if(x>0&&ink(x-1,y-1)!=ink(x-1,y)){mask|=4u;}
 if(y>0&&ink(x-1,y-1)!=ink(x,y-1)){mask|=8u;}graph[v]=mask;
}
@compute @workgroup_size(128) fn prepare(@builtin(global_invocation_id) id:vec3<u32>){
 let v=id.x;if(v>=p.n){return;}let x=v%(p.w+1u);let y=v/(p.w+1u);source[v]=vec2<u32>(x,y)*p.scale;
 neighbors[v]=vec2<u32>(0xffffffffu);let mask=graph[v];
 if(x==0u||y==0u||x==p.w||y==p.h||countOneBits(mask)!=2u){return;}
 var ns=vec2<u32>(0u);var k=0u;for(var d=0u;d<4u;d++){if((mask&(1u<<d))!=0u){ns[k]=next(v,d);k++;}}
 // An isolated cycle of at most eight vertices is a pinned 1вЂ“2 pixel hole/island.
 var prev=v;var current=ns.x;var pinned=false;
 for(var step=1u;step<=8u;step++){
  if(current==v){pinned=true;break;}if(countOneBits(graph[current])!=2u){break;}
  var following=prev;for(var d=0u;d<4u;d++){if((graph[current]&(1u<<d))!=0u){let q=next(current,d);if(q!=prev){following=q;break;}}}
  prev=current;current=following;
 }if(!pinned){neighbors[v]=ns;}
}
@compute @workgroup_size(128) fn diffuse(@builtin(global_invocation_id) id:vec3<u32>){
 let v=id.x;if(v>=p.n){return;}let a=source[v];let ns=neighbors[v];if(ns.x==0xffffffffu){destination[v]=a;return;}
 let b=source[ns.x];let c=source[ns.y];
 // Split quotient/remainder before summing, so 2*a+b+c cannot overflow u32.
 destination[v]=(a>>vec2<u32>(1u))+(b>>vec2<u32>(2u))+(c>>vec2<u32>(2u))+(((a&vec2<u32>(1u))*2u+(b&vec2<u32>(3u))+(c&vec2<u32>(3u)))>>vec2<u32>(2u));
}`;
let cached;
export let contourGpuError=null;
export function preferGpuContours(w,h,{unlimited,detail,gpuContours}={}){return gpuContours==='always'||(unlimited&&detail<2&&w*h>=700000);}
export async function gpuContourCoordinates(labels,w,h,passes){
 const buffers=[];try{contourGpuError=null;
  if(!Number.isInteger(w)||!Number.isInteger(h)||w<1||h<1||labels.byteLength!==w*h*4){contourGpuError='Invalid contour grid';return null;}
  const device=await gpuDevice();const n=(w+1)*(h+1),scale=4**passes;
  if(!device||!Number.isInteger(passes)||passes<0||passes>10||Math.max(w,h)*scale>0xffffffff||n*8>device.limits.maxStorageBufferBindingSize)return null;
  if(!cached||cached.device!==device){
   const entries=Array.from({length:6},(_,binding)=>({binding,visibility:GPUShaderStage.COMPUTE,buffer:{type:binding===0?'read-only-storage':binding===5?'uniform':'storage'}}));
   const group=device.createBindGroupLayout({entries}),layout=device.createPipelineLayout({bindGroupLayouts:[group]});
   const module=device.createShaderModule({code:shader});const info=await module.getCompilationInfo();const errors=info.messages.filter(m=>m.type==='error');if(errors.length)throw Error(errors.map(m=>m.lineNum+': '+m.message).join('; '));const pipelines={};
   for(const entryPoint of ['edges','prepare','diffuse'])pipelines[entryPoint]=await device.createComputePipelineAsync({layout,compute:{module,entryPoint}});
   cached={device,group,pipelines};
  }
  const buffer=(size,usage)=>{const b=device.createBuffer({size,usage});buffers.push(b);return b;};const storage=GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC|GPUBufferUsage.COPY_DST;
  const input=buffer(labels.byteLength,storage),graph=buffer(n*4,storage),a=buffer(n*8,storage),b=buffer(n*8,storage),neighbors=buffer(n*8,storage),params=buffer(16,GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST),readback=buffer(n*8,GPUBufferUsage.MAP_READ|GPUBufferUsage.COPY_DST);
  device.queue.writeBuffer(input,0,labels);device.queue.writeBuffer(params,0,new Uint32Array([w,h,scale,n]));
  const encoder=device.createCommandEncoder();const dispatch=(kind,src,dst)=>{
   const group=device.createBindGroup({layout:cached.group,entries:[input,graph,src,dst,neighbors,params].map((buffer,binding)=>({binding,resource:{buffer}}))});
   const pass=encoder.beginComputePass();pass.setPipeline(cached.pipelines[kind]);pass.setBindGroup(0,group);pass.dispatchWorkgroups(Math.ceil(n/128));pass.end();
  };
  dispatch('edges',a,b);dispatch('prepare',a,b);let src=a,dst=b;
  for(let i=0;i<passes;i++){dispatch('diffuse',src,dst);[src,dst]=[dst,src];}
  encoder.copyBufferToBuffer(src,0,readback,0,n*8);device.queue.submit([encoder.finish()]);await readback.mapAsync(GPUMapMode.READ);const result=new Uint32Array(readback.getMappedRange().slice(0));readback.unmap();return result;
 }catch(error){contourGpuError=String(error.message??error);return null;}finally{for(const b of buffers)b.destroy();}
}
