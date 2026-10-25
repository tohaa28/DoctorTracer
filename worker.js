// SPDX-License-Identifier: GPL-2.0-or-later
import createTracer from './rust-tracer.mjs?v=0.12.1';
import {gpuPrepare,gpuAssign} from './gpu.js?v=0.12.1';
import {auditNative} from './geometry.mjs?v=0.12.1';
import {traceFixed} from './desktop-curves.mjs?v=0.12.1';
let runtime,loading,lastProgress=0;
function emitProgress(progress,stage){lastProgress=Math.max(lastProgress,progress);self.postMessage({progress:lastProgress,stage});}
const stages=['','Подготовка изображения','Определение палитры','Сегментация','Объединение областей','Построение кривых','Готово'];
self.onmessage=async ({data})=>{
 try{
  lastProgress=0;emitProgress(1,'Загрузка Rust WASM');
  runtime??=await (loading??=createTracer({onProgress:(progress,stage)=>emitProgress(Math.min(85,progress),stages[stage])}));
  if(data.operation==='analyze'){self.postMessage({analysis:runtime.analyze(new Uint8Array(data.pixels),data.width,data.height),requestId:data.requestId});return;}
  if(data.operation==='palette'){const colors=runtime.stage(new Uint8Array(data.pixels),data.width,data.height,{kind:2,colors:data.colors,extra:0});self.postMessage({palette:Array.from({length:colors.length/3},(_,i)=>Array.from(colors.slice(i*3,i*3+3))),requestId:data.requestId});return;}
  let pixels=new Uint8Array(data.pixels);let backend='Rust WASM CPU',prefiltered=false;
  const start=performance.now();
  if(data.gpu&&(data.category!=='hard'||data.detail===0)){
   emitProgress(4,'Фильтрация изображения');
   const accelerated=await gpuPrepare(pixels,data.width,data.height,data);
   if(accelerated){pixels=accelerated;prefiltered=true;backend='WebGPU + Rust WASM';}
  }
  const unlimited=data.category==='photo'&&!data.colors&&!data.palette?.length;
  let svg,segments,metrics,prechecked;
  if(unlimited){
   let labels,palette;if(prefiltered){emitProgress(18,'Определение палитры');const values=runtime.stage(pixels,data.width,data.height,{kind:2,colors:64,extra:1});palette=Array.from({length:values.length/3},(_,i)=>Array.from(values.slice(i*3,i*3+3)));emitProgress(28,'Пространственная сегментация');labels=await gpuAssign(pixels,data.width,data.height,palette,200);}
   svg=labels?runtime.finish(pixels,labels,data.width,data.height,{...data,palette,unlimited:true}):runtime.trace(pixels,data.width,data.height,{...data,prefiltered});metrics=runtime.stats();segments=runtime.segments();
  }
  else{const result=await traceFixed(runtime,pixels,data.width,data.height,{...data,prefiltered},emitProgress);svg=result.svg;segments=result.segments;prechecked=result.geometry;metrics={algorithm:result.algorithm,palette:result.palette};}
  emitProgress(90,'Проверка пересечений');let geometry=prechecked;let smoothing_fallback=false;try{geometry??=await auditNative(svg);}catch(error){if(!unlimited)throw error;svg=runtime.fallback();geometry=await auditNative(svg);smoothing_fallback=true;}
  emitProgress(100,'Готово');self.postMessage({geometry,smoothing_fallback,metrics,segments:segments?.buffer,svg,paths:(svg.match(/<path /g)||[]).length,colors:(svg.match(/id="color-/g)||[]).length,seconds:(performance.now()-start)/1000,backend});
 }catch(error){self.postMessage({error:String(error.message??error),requestId:data.requestId});}
};
