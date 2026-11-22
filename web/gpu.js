// SPDX-License-Identifier: MIT
// Exact integer ports of desktop OpenCL bilateral, mode and spatial kernels.
const common=`
struct Params{w:u32,h:u32,radius:u32,range2:u32}
@group(0) @binding(0) var<storage,read> source:array<u32>;
@group(0) @binding(1) var<storage,read_write> output:array<u32>;
@group(0) @binding(2) var<uniform> params:Params;
fn rgb(p:u32)->vec3<i32>{return vec3<i32>(i32(p&255u),i32((p>>8u)&255u),i32((p>>16u)&255u));}
fn pack(c:vec3<u32>,p:u32)->u32{return (p&0xff000000u)|c.x|(c.y<<8u)|(c.z<<16u);}
fn reflect(i:i32,n:u32)->u32{if(n==1u){return 0u;}let period=2*i32(n)-2;let j=((i%period)+period)%period;return u32(min(j,period-j));}
`;
const bilateral=common+`
@group(0) @binding(3) var<storage,read> weights:array<u32>;
@compute @workgroup_size(16,16) fn main(@builtin(global_invocation_id) id:vec3<u32>){
 if(id.x>=params.w||id.y>=params.h){return;}let i=id.y*params.w+id.x;let p=source[i];if((p>>24u)<128u){output[i]=p;return;}
 let center=rgb(p);var sums=vec3<u32>(0u);var total=0u;
 for(var dy=-2;dy<=2;dy++){for(var dx=-2;dx<=2;dx++){let r=dx*dx+dy*dy;if(r>4){continue;}let j=reflect(i32(id.y)+dy,params.h)*params.w+reflect(i32(id.x)+dx,params.w);let q=source[j];if((q>>24u)<128u){continue;}let delta=abs(center-rgb(q));let d=delta.x+delta.y+delta.z;let weight=weights[u32(r*766+d)];sums+=vec3<u32>(rgb(q))*weight;total+=weight;}}
 output[i]=pack((sums+vec3<u32>(total/2u))/total,p);
}`;
const modes=common+`
@compute @workgroup_size(16,16) fn main(@builtin(global_invocation_id) id:vec3<u32>){
 if(id.x>=params.w||id.y>=params.h){return;}let i=id.y*params.w+id.x;let p=source[i];if((p>>24u)<128u){output[i]=p;return;}
 var x=i32(id.x);var y=i32(id.y);var color=rgb(p);let radius=i32(params.radius);
 for(var k=0;k<5;k++){var sx=0;var sy=0;var n=0;var sum=vec3<i32>(0);
  for(var yy=max(0,y-radius);yy<=min(i32(params.h)-1,y+radius);yy++){for(var xx=max(0,x-radius);xx<=min(i32(params.w)-1,x+radius);xx++){
   let q=source[u32(yy)*params.w+u32(xx)];if((q>>24u)<128u){continue;}let d=rgb(q)-color;if(u32(d.x*d.x+d.y*d.y+d.z*d.z)>params.range2){continue;}n++;sx+=xx;sy+=yy;sum+=rgb(q);
  }}if(n==0){break;}let nx=(sx+n/2)/n;let ny=(sy+n/2)/n;let nc=(sum+vec3<i32>(n/2))/n;let done=nx==x&&ny==y&&all(nc==color);x=nx;y=ny;color=nc;if(done){break;}
 }output[i]=pack(vec3<u32>(color),p);
}`;

const nearest=common+`
@group(0) @binding(3) var<storage,read> palette:array<u32>;
@compute @workgroup_size(16,16) fn main(@builtin(global_invocation_id) id:vec3<u32>){if(id.x>=params.w||id.y>=params.h){return;}let i=id.y*params.w+id.x;let p=source[i];if((p>>24u)<128u){output[i]=255u;return;}var best=2147483647;var label=0u;for(var c=0u;c<params.radius;c++){let d=rgb(p)-rgb(palette[c]);let distance=d.x*d.x+d.y*d.y+d.z*d.z;if(distance<best){best=distance;label=c;}}output[i]=label;}`;
const spatial=common+`
@group(0) @binding(3) var<storage,read> palette:array<u32>;
@group(0) @binding(4) var<storage,read> labels:array<u32>;
struct Phase{value:u32,a:u32,b:u32,c:u32}
@group(0) @binding(5) var<uniform> phase:Phase;
@compute @workgroup_size(16,16) fn main(@builtin(global_invocation_id) id:vec3<u32>){if(id.x>=params.w||id.y>=params.h){return;}let i=id.y*params.w+id.x;let p=source[i];if((p>>24u)<128u){output[i]=255u;return;}if(((id.x+id.y)&1u)!=phase.value){output[i]=labels[i];return;}var neighbours=vec4<u32>(255u);if(id.x>0u){neighbours.x=labels[i-1u];}if(id.x+1u<params.w){neighbours.y=labels[i+1u];}if(id.y>0u){neighbours.z=labels[i-params.w];}if(id.y+1u<params.h){neighbours.w=labels[i+params.w];}var best=2147483647;var label=labels[i];for(var c=0u;c<params.radius;c++){let d=rgb(p)-rgb(palette[c]);var energy=d.x*d.x+d.y*d.y+d.z*d.z;for(var k=0u;k<4u;k++){if(neighbours[k]!=255u&&neighbours[k]!=c){energy+=i32(params.range2);}}if(energy<best){best=energy;label=c;}}output[i]=label;}`;
let device,pipelines,weightBuffer;
const constants=()=>Uint32Array.from({length:5*766},(_,i)=>Math.round(4096*Math.exp(-((i%766)**2)/(2*25**2)-Math.floor(i/766)/18)));
async function init(){
 if(!navigator.gpu)return false;
 if(!device){const adapter=await navigator.gpu.requestAdapter();if(!adapter)return false;device=await adapter.requestDevice();pipelines={};for(const [key,code] of Object.entries({bilateral,modes,nearest,spatial}))pipelines[key]=await device.createComputePipelineAsync({layout:'auto',compute:{module:device.createShaderModule({code}),entryPoint:'main'}});
 const weights=constants();weightBuffer=device.createBuffer({size:weights.byteLength,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST});device.queue.writeBuffer(weightBuffer,0,weights);device.lost.then(()=>{device=null;});}
 return true;
}
export async function gpuStage(pixels,w,h,detail,stage='bilateral'){
 const buffers=[];try{if(!await init()||pixels.byteLength>device.limits.maxStorageBufferBindingSize)return null;
  const buffer=(size,usage)=>{const b=device.createBuffer({size,usage});buffers.push(b);return b;};
  const source=buffer(pixels.byteLength,GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST);const output=buffer(pixels.byteLength,GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC);const uniform=buffer(16,GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST);const readback=buffer(pixels.byteLength,GPUBufferUsage.MAP_READ|GPUBufferUsage.COPY_DST);
  device.queue.writeBuffer(source,0,pixels);device.queue.writeBuffer(uniform,0,new Uint32Array([w,h,[7,5,3][detail],[900,400,225][detail]]));
  const pipeline=pipelines[stage];const entries=[source,output,uniform];if(stage==='bilateral')entries.push(weightBuffer);
  const group=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:entries.map((buffer,binding)=>({binding,resource:{buffer}}))});const encoder=device.createCommandEncoder();const pass=encoder.beginComputePass();pass.setPipeline(pipeline);pass.setBindGroup(0,group);pass.dispatchWorkgroups(Math.ceil(w/16),Math.ceil(h/16));pass.end();encoder.copyBufferToBuffer(output,0,readback,0,pixels.byteLength);device.queue.submit([encoder.finish()]);await readback.mapAsync(GPUMapMode.READ);const result=new Uint8Array(readback.getMappedRange().slice(0));readback.unmap();return result;
 }catch{device=null;return null;}finally{for(const b of buffers)b.destroy();}
}
export const gpuFilter=(pixels,w,h,detail)=>gpuStage(pixels,w,h,detail,'bilateral');
export async function gpuPrepare(pixels,w,h,config){
 let result=pixels,accelerated=false;if(config.category==='photo'||config.detail===0){result=await gpuFilter(result,w,h,config.detail);if(!result)return null;accelerated=true;}
 if(config.category==='photo'&&!config.colors&&!config.palette?.length){result=await gpuStage(result,w,h,config.detail,'modes');if(!result)return null;accelerated=true;}
 return accelerated?result:null;
}

export async function gpuAssign(pixels,w,h,palette,strength=200){
 const buffers=[];try{if(!await init()||pixels.byteLength>device.limits.maxStorageBufferBindingSize)return null;
  const buffer=(size,usage)=>{const b=device.createBuffer({size,usage});buffers.push(b);return b;},storage=GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST|GPUBufferUsage.COPY_SRC;
  const source=buffer(pixels.byteLength,GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST),inks=buffer(palette.length*4,GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST),uniform=buffer(16,GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST),phases=[0,1].map(()=>buffer(16,GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST)),a=buffer(w*h*4,storage),b=buffer(w*h*4,storage),readback=buffer(w*h*4,GPUBufferUsage.MAP_READ|GPUBufferUsage.COPY_DST);
  device.queue.writeBuffer(source,0,pixels);device.queue.writeBuffer(inks,0,Uint32Array.from(palette,p=>p[0]|(p[1]<<8)|(p[2]<<16)));device.queue.writeBuffer(uniform,0,new Uint32Array([w,h,palette.length,strength]));for(let i=0;i<2;i++)device.queue.writeBuffer(phases[i],0,new Uint32Array([i,0,0,0]));
  const encoder=device.createCommandEncoder();const dispatch=(pipeline,output,input,phase)=>{const resources=[source,output,uniform,inks,...(input?[input,phases[phase]]:[])];const group=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:resources.map((buffer,binding)=>({binding,resource:{buffer}}))});const pass=encoder.beginComputePass();pass.setPipeline(pipeline);pass.setBindGroup(0,group);pass.dispatchWorkgroups(Math.ceil(w/16),Math.ceil(h/16));pass.end();};
  dispatch(pipelines.nearest,a);let input=a,output=b;if(strength)for(let iteration=0;iteration<2;iteration++)for(let phase=0;phase<2;phase++){dispatch(pipelines.spatial,output,input,phase);[input,output]=[output,input];}
  encoder.copyBufferToBuffer(input,0,readback,0,w*h*4);device.queue.submit([encoder.finish()]);await readback.mapAsync(GPUMapMode.READ);const result=Uint8Array.from(new Uint32Array(readback.getMappedRange()));readback.unmap();return result;
 }catch{device=null;return null;}finally{for(const b of buffers)b.destroy();}
}

export async function gpuDevice(){return await init()?device:null;}
