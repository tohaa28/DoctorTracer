// SPDX-License-Identifier: MIT
export default async function createTracer({wasmBinary,onProgress=()=>{}}={}) {
 const bytes=wasmBinary??await (await fetch(new URL('./doctortracer.wasm',import.meta.url))).arrayBuffer();
 const {instance}=await WebAssembly.instantiate(bytes,{env:{progress:onProgress}});
 const api=instance.exports;
 return {filter(pixels,width,height,detail){
  if(pixels.length!==width*height*4)throw Error('Некорректный размер изображения');
  const pointer=api.alloc(pixels.length);if(!pointer)throw Error('Недостаточно памяти');
  try{new Uint8Array(api.memory.buffer,pointer,pixels.length).set(pixels);const result=api.filter_rgba(pointer,width,height,detail);if(!result)throw Error('Некорректные параметры фильтрации');return new Uint8Array(api.memory.buffer,result,api.result_len()).slice();}
  finally{api.dealloc(pointer,pixels.length);}
 },trace(pixels,width,height,{colors=0,detail=1,speckle=3,polygon=false,prefiltered=false,category='photo'}={}){
  if(pixels.length!==width*height*4)throw Error('Некорректный размер изображения');
  const pointer=api.alloc(pixels.length);if(!pointer)throw Error('Недостаточно памяти');
  try{
   new Uint8Array(api.memory.buffer,pointer,pixels.length).set(pixels);
   const result=api.trace_rgba(pointer,width,height,colors,detail,speckle,(polygon?1:0)|(prefiltered?2:0)|(category==='hard'?4:0));
   if(!result)throw Error('Не удалось построить вектор. Проверьте параметры и размер изображения.');
   return new TextDecoder().decode(new Uint8Array(api.memory.buffer,result,api.result_len()));
  }finally{api.dealloc(pointer,pixels.length);}
 }};
}
