// SPDX-License-Identifier: GPL-2.0-or-later
import createTracer from './tracer.mjs';
let runtime;
self.onmessage=async ({data})=>{
 let pointer=0;
 try{
  runtime??=await createTracer();
  const {pixels,width,height,colors,detail,speckle,polygon}=data;
  const bytes=new Uint8Array(pixels);
  if(bytes.length!==width*height*4)throw Error('Некорректный размер изображения');
  pointer=runtime._malloc(bytes.length);if(!pointer)throw Error('Недостаточно памяти');
  runtime.HEAPU8.set(bytes,pointer);
  const start=performance.now();const output=runtime._trace_rgba(pointer,width,height,colors,detail,speckle,polygon?1:0);
  if(!output)throw Error('Не удалось построить вектор. Уменьшите размер изображения.');
  self.postMessage({svg:runtime.UTF8ToString(output),paths:runtime._trace_paths(),seconds:(performance.now()-start)/1000});
 }catch(error){self.postMessage({error:String(error.message??error)});}
 finally{if(pointer)runtime._free(pointer);}
};
