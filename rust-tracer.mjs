// SPDX-License-Identifier: MIT
export default async function createTracer({wasmBinary,onProgress=()=>{}}={}){
 const bytes=wasmBinary??await(await fetch(new URL('./doctortracer.wasm?v=0.18.0',import.meta.url))).arrayBuffer();
 const {instance}=await WebAssembly.instantiate(bytes,{env:{progress:onProgress}});const api=instance.exports;const decode=new TextDecoder();
 function input(bytes){const p=api.alloc(bytes.byteLength);if(!p)throw Error('Недостаточно памяти');new Uint8Array(api.memory.buffer,p,bytes.byteLength).set(new Uint8Array(bytes.buffer,bytes.byteOffset,bytes.byteLength));return p;}
 function palette(values=[]){if(!values.length){api.set_palette(0,0);return;}const data=new Uint8Array(values.flatMap(c=>typeof c==='string'?c.replace('#','').match(/../g).map(v=>parseInt(v,16)):Array.from(c)));const p=input(data);try{api.set_palette(p,values.length);}finally{api.dealloc(p,data.length);}}
 function output(pointer,text=false){if(!pointer)throw Error('Некорректные параметры трассировки');const bytes=new Uint8Array(api.memory.buffer,pointer,api.result_len());return text?decode.decode(bytes):bytes.slice();}
 return {
  postClean(svg,minArea=4,tolerance=.25,protect=true){const bytes=new TextEncoder().encode(svg),p=input(bytes);try{const value=output(api.result_clean(p,bytes.length,minArea,tolerance,protect?1:0),true);return{svg:value,...this.stats()};}finally{api.dealloc(p,bytes.length);}},
  postSmooth(svg,strength=35,sharp=true){const bytes=new TextEncoder().encode(svg),p=input(bytes);try{const value=output(api.result_smooth(p,bytes.length,strength,sharp?1:0),true);return{svg:value,...this.stats()};}finally{api.dealloc(p,bytes.length);}},
  analyze(pixels,w,h){const p=input(pixels);try{return JSON.parse(output(api.analyze_rgba(p,w,h),true));}finally{api.dealloc(p,pixels.length);}},
  stage(pixels,width,height,{colors=0,detail=1,kind=0,extra=0,palette:inks=[]}={}){palette(inks);const bytes=new Uint8Array(Math.max(pixels.byteLength,width*height*4));bytes.set(new Uint8Array(pixels.buffer,pixels.byteOffset,pixels.byteLength));const p=input(bytes);try{return output(api.desktop_stage(p,width,height,colors,detail,kind,extra));}finally{api.dealloc(p,bytes.length);}},
  filter(pixels,w,h,detail){return this.stage(pixels,w,h,{kind:0,detail});},
  shared(labels,inks,w,h,detail=1,smooth=true,{fixed=false,polygon=false}={}){palette(inks);const p=input(labels);try{const svg=output(api.shared_svg(p,w,h,detail,(smooth?1:0)|(polygon?2:0)|(fixed?4:0)),true);if(!svg.includes('data-boundary-contract="paired"'))throw Error('Не подтверждено совпадение общих границ');return svg;}finally{api.dealloc(p,labels.byteLength);}},
  jointProposal(pixels,labels,w,h,inks){palette(inks);const p=input(pixels),l=input(labels);try{const raw=output(api.joint_proposal(p,l,w,h));return Array.from({length:raw.length/3},(_,i)=>Array.from(raw.slice(i*3,i*3+3)));}finally{api.dealloc(p,pixels.length);api.dealloc(l,labels.length);}},
  jointChoose(pixels,old,candidate,w,h,inks){palette(inks);const p=input(pixels),l=input(old),c=input(candidate);try{return output(api.joint_choose(p,l,c,w,h));}finally{api.dealloc(p,pixels.length);api.dealloc(l,old.length);api.dealloc(c,candidate.length);}},
  sharedInput(){return new Int32Array(output(api.shared_input()).buffer);},
  sharedFinish(coordinates,passes,{unlimited=true,smooth=true,polygon=false}={}){const p=coordinates?input(coordinates):0;try{return output(api.shared_finish(p,coordinates?.length??0,passes,(smooth?1:0)|(polygon?2:0)|(unlimited?0:4)),true);}finally{if(p)api.dealloc(p,coordinates.byteLength);}},
  segments(){return output(api.segment_preview());},
  rasterBase(){return output(api.raster_base(),true);},
  fallback(){return output(api.shared_fallback(),true);},
  stats(){return JSON.parse(decode.decode(new Uint8Array(api.memory.buffer,api.stats_ptr(),api.stats_len()))||'{}');},
  finish(pixels,labels,width,height,{palette:inks,detail=1,speckle=2,unlimited=true,smooth=true,artifact_strength=0,deferShared=false,palette_generated=false,prefinished=false}={}){palette(inks);const p=input(pixels),l=input(labels);try{return output(api.trace_labels(p,l,width,height,detail,speckle,(prefinished?4096:0)|(deferShared?128:0)|(palette_generated?2048:0)|(smooth?0:32)|(Math.min(2,Math.max(0,artifact_strength))<<8),unlimited?1:0),true);}finally{api.dealloc(p,pixels.length);api.dealloc(l,labels.length);}},
  trace(pixels,width,height,{colors=0,detail=1,speckle=2,polygon=false,prefiltered=false,category='photo',palette:inks=[],smooth=true,artifact_strength=0,deferShared=false,palette_generated=false,prefinished=false}={}){
   if(pixels.length!==width*height*4)throw Error('Некорректный размер изображения');palette(inks);const p=input(pixels);
   try{return output(api.trace_rgba(p,width,height,colors,detail,speckle,(palette_generated?2048:0)|(polygon?1:0)|(prefiltered?2:0)|(category==='hard'?4:category==='aa'?8:0)|(!smooth?32:0)|(deferShared?128:0)|(Math.min(2,Math.max(0,artifact_strength))<<8)),true);}finally{api.dealloc(p,pixels.length);}
  }
 };
}
