// SPDX-License-Identifier: MIT
export default async function createTracer({wasmBinary,onProgress=()=>{}}={}){
 const bytes=wasmBinary??await(await fetch(new URL('./doctortracer.wasm',import.meta.url))).arrayBuffer();
 const {instance}=await WebAssembly.instantiate(bytes,{env:{progress:onProgress}});const api=instance.exports;const decode=new TextDecoder();
 function input(bytes){const p=api.alloc(bytes.byteLength);if(!p)throw Error('Недостаточно памяти');new Uint8Array(api.memory.buffer,p,bytes.byteLength).set(new Uint8Array(bytes.buffer,bytes.byteOffset,bytes.byteLength));return p;}
 function palette(values=[]){if(!values.length){api.set_palette(0,0);return;}const data=new Uint8Array(values.flatMap(c=>typeof c==='string'?c.replace('#','').match(/../g).map(v=>parseInt(v,16)):Array.from(c)));const p=input(data);try{api.set_palette(p,values.length);}finally{api.dealloc(p,data.length);}}
 function output(pointer,text=false){if(!pointer)throw Error('Некорректные параметры трассировки');const bytes=new Uint8Array(api.memory.buffer,pointer,api.result_len());return text?decode.decode(bytes):bytes.slice();}
 return {
  analyze(pixels,w,h){const p=input(pixels);try{return JSON.parse(output(api.analyze_rgba(p,w,h),true));}finally{api.dealloc(p,pixels.length);}},
  stage(pixels,width,height,{colors=0,detail=1,kind=0,extra=0,palette:inks=[]}={}){palette(inks);const bytes=new Uint8Array(Math.max(pixels.byteLength,width*height*4));bytes.set(new Uint8Array(pixels.buffer,pixels.byteOffset,pixels.byteLength));const p=input(bytes);try{return output(api.desktop_stage(p,width,height,colors,detail,kind,extra));}finally{api.dealloc(p,bytes.length);}},
  filter(pixels,w,h,detail){return this.stage(pixels,w,h,{kind:0,detail});},
  shared(labels,inks,w,h,detail=1,smooth=true){palette(inks);const p=input(labels);try{return output(api.shared_svg(p,w,h,detail,smooth?1:0),true);}finally{api.dealloc(p,labels.byteLength);}},
  segments(){return output(api.segment_preview());},
  fallback(){return output(api.shared_fallback(),true);},
  stats(){return JSON.parse(decode.decode(new Uint8Array(api.memory.buffer,api.stats_ptr(),api.stats_len()))||'{}');},
  finish(pixels,labels,width,height,{palette:inks,detail=1,speckle=2,unlimited=true,smooth=true}={}){palette(inks);const p=input(pixels),l=input(labels);try{return output(api.trace_labels(p,l,width,height,detail,speckle,smooth?0:32,unlimited?1:0),true);}finally{api.dealloc(p,pixels.length);api.dealloc(l,labels.length);}},
  trace(pixels,width,height,{colors=0,detail=1,speckle=2,polygon=false,prefiltered=false,category='photo',palette:inks=[],smooth=true}={}){
   if(pixels.length!==width*height*4)throw Error('Некорректный размер изображения');palette(inks);const p=input(pixels);
   try{return output(api.trace_rgba(p,width,height,colors,detail,speckle,(polygon?1:0)|(prefiltered?2:0)|(category==='hard'?4:category==='aa'?8:0)|(!smooth?32:0)),true);}finally{api.dealloc(p,pixels.length);}
  }
 };
}
