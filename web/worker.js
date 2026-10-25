// SPDX-License-Identifier: GPL-2.0-or-later
import createTracer from './rust-tracer.mjs';
import {gpuFilter} from './gpu.js';
let runtime;
const stages=['','Подготовка изображения','Определение палитры','Сегментация','Объединение областей','Построение кривых','Готово'];
self.onmessage=async ({data})=>{
 try{
  self.postMessage({progress:1,stage:'Загрузка Rust WASM'});
  runtime??=await createTracer({onProgress:(progress,stage)=>self.postMessage({progress,stage:stages[stage]})});
  let pixels=new Uint8Array(data.pixels);let backend='Rust WASM CPU',prefiltered=false;
  const start=performance.now();
  if(data.gpu&&data.category!=='hard'){
   self.postMessage({progress:4,stage:'Фильтрация изображения'});
   const accelerated=await gpuFilter(pixels,data.width,data.height,data.detail);
   if(accelerated){pixels=accelerated;prefiltered=true;backend='WebGPU + Rust WASM';}
  }
  const svg=runtime.trace(pixels,data.width,data.height,{...data,prefiltered});
  self.postMessage({svg,paths:(svg.match(/<path /g)||[]).length,colors:(svg.match(/id="color-/g)||[]).length,seconds:(performance.now()-start)/1000,backend});
 }catch(error){self.postMessage({error:String(error.message??error)});}
};
