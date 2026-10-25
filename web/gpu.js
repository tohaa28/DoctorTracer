// SPDX-License-Identifier: MIT
// Same integer filter as Rust CPU. No private image uploads.
const shader=`
struct Params {width:u32,height:u32,limit:u32,padding:u32}
@group(0) @binding(0) var<storage,read> source:array<u32>;
@group(0) @binding(1) var<storage,read_write> output:array<u32>;
@group(0) @binding(2) var<uniform> params:Params;
fn rgb(p:u32)->vec3<i32>{return vec3<i32>(i32(p&255u),i32((p>>8u)&255u),i32((p>>16u)&255u));}
@compute @workgroup_size(16,16)
fn main(@builtin(global_invocation_id) id:vec3<u32>){
 if(id.x>=params.width||id.y>=params.height){return;}
 let i=id.y*params.width+id.x;let p=source[i];
 if((p>>24u)<128u){output[i]=p;return;}
 let color=rgb(p);var sum=vec3<u32>(0u);var weights=0u;
 for(var dy=-2;dy<=2;dy++){for(var dx=-2;dx<=2;dx++){
  let x=i32(id.x)+dx;let y=i32(id.y)+dy;
  if(x<0||y<0||x>=i32(params.width)||y>=i32(params.height)){continue;}
  let q=source[u32(y)*params.width+u32(x)];if((q>>24u)<128u){continue;}
  let delta=abs(color-rgb(q));let diff=delta.x+delta.y+delta.z;
  let weight=u32(max(0,i32(params.limit)-diff)*(3-abs(dx))*(3-abs(dy)));
  weights+=weight;sum+=weight*vec3<u32>(rgb(q));
 }}
 let c=(sum+vec3<u32>(weights/2u))/weights;
 output[i]=(p&0xff000000u)|c.x|(c.y<<8u)|(c.z<<16u);
}`;
let device,pipeline;
export async function gpuFilter(pixels,width,height,detail){
 const buffers=[];
 try{
  if(!navigator.gpu)return null;
  if(!device){const adapter=await navigator.gpu.requestAdapter();if(!adapter)return null;device=await adapter.requestDevice();pipeline=await device.createComputePipelineAsync({layout:'auto',compute:{module:device.createShaderModule({code:shader}),entryPoint:'main'}});}
  if(pixels.byteLength>device.limits.maxStorageBufferBindingSize)return null;
  const buffer=(size,usage)=>{const b=device.createBuffer({size,usage});buffers.push(b);return b;};
  const input=buffer(pixels.byteLength,GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST);
  const output=buffer(pixels.byteLength,GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC);
  const uniform=buffer(16,GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST);
  const readback=buffer(pixels.byteLength,GPUBufferUsage.MAP_READ|GPUBufferUsage.COPY_DST);
  device.queue.writeBuffer(input,0,pixels);device.queue.writeBuffer(uniform,0,new Uint32Array([width,height,[60,48,36][detail],0]));
  const group=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[input,output,uniform].map((b,binding)=>({binding,resource:{buffer:b}}))});
  const encoder=device.createCommandEncoder();const pass=encoder.beginComputePass();pass.setPipeline(pipeline);pass.setBindGroup(0,group);pass.dispatchWorkgroups(Math.ceil(width/16),Math.ceil(height/16));pass.end();encoder.copyBufferToBuffer(output,0,readback,0,pixels.byteLength);device.queue.submit([encoder.finish()]);
  await readback.mapAsync(GPUMapMode.READ);const result=new Uint8Array(readback.getMappedRange().slice(0));readback.unmap();return result;
 }catch{device=null;pipeline=null;return null;}
 finally{for(const b of buffers)b.destroy();}
}
