// SPDX-License-Identifier: GPL-2.0-or-later
import createTracer from './rust-tracer.mjs';
import {gpuPrepare,gpuAssign} from './gpu.js';
import {gpuContourCoordinates,preferGpuContours,contourGpuError} from './gpu-contours.mjs';
import {auditNative} from './geometry.mjs';
import{cleanResult}from'./post-clean.mjs';
import {smoothResult} from './post-smooth.mjs';
import {traceFixed} from './desktop-curves.mjs';
let runtime,loading,lastProgress=0;
function emitProgress(progress,stage){lastProgress=Math.max(lastProgress,progress);self.postMessage({progress:lastProgress,stage});}
const stages=['','Подготовка изображения','Определение палитры','Сегментация','Объединение областей','Построение кривых','Готово'];
self.onmessage=async ({data})=>{
 try{
  lastProgress=0;emitProgress(1,'Загрузка Rust WASM');
  runtime??=await (loading??=createTracer({onProgress:(progress,stage)=>emitProgress(Math.min(85,progress),stages[stage])}));
  if(data.operation==='postClean'){const result=await cleanResult(runtime,data.svg,data.minArea,data.tolerance,data.protect);self.postMessage({postClean:result,requestId:data.requestId});return;}
  if(data.operation==='postSmooth'){const result=await smoothResult(runtime,data.svg,data.strength,data.sharp);self.postMessage({postSmooth:result,requestId:data.requestId});return;}
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
  if(data.category==='photo'){
   let labels,palette;if(prefiltered){emitProgress(18,'Определение палитры');if(data.palette?.length)palette=data.palette.map(c=>typeof c==='string'?c.slice(1).match(/../g).map(v=>parseInt(v,16)):c);else{if(!unlimited)data.palette_generated=true;const values=runtime.stage(pixels,data.width,data.height,{kind:2,colors:unlimited?64:data.colors,extra:1});palette=Array.from({length:values.length/3},(_,i)=>Array.from(values.slice(i*3,i*3+3)));}emitProgress(28,'Пространственная сегментация');labels=await gpuAssign(pixels,data.width,data.height,palette,unlimited?200:700);}
   let jointGpuSteps=0;
   if(labels&&!unlimited&&data.palette_generated){
    labels=runtime.stage(labels,data.width,data.height,{kind:4,colors:palette.length,palette,extra:Math.max(8,data.speckle??2)|((data.artifact_strength??0)<<16)});
    for(let step=0;step<3;step++){
     const proposed=runtime.jointProposal(pixels,labels,data.width,data.height,palette);
     if(JSON.stringify(proposed)===JSON.stringify(palette))break;
     const accelerated=await gpuAssign(pixels,data.width,data.height,proposed,700);const candidate=accelerated??runtime.stage(pixels,data.width,data.height,{kind:3,palette:proposed,extra:700});
     labels=runtime.jointChoose(pixels,labels,candidate,data.width,data.height,proposed);palette=proposed;if(accelerated)jointGpuSteps++;
    }
    data={...data,palette_generated:false,prefinished:true};
   }
   const deferShared=data.gpu&&data.smooth!==false&&preferGpuContours(data.width,data.height,{...data,unlimited});
   svg=labels?runtime.finish(pixels,labels,data.width,data.height,{...data,palette,unlimited,deferShared}):runtime.trace(pixels,data.width,data.height,{...data,prefiltered,deferShared});metrics=runtime.stats();metrics.joint_gpu_steps=jointGpuSteps;segments=runtime.segments();
   if(deferShared){emitProgress(72,'Сглаживание общих границ на GPU');const passes=(unlimited?[10,8,5]:[4,2,1])[data.detail],started=performance.now();const coordinates=await gpuContourCoordinates(runtime.sharedInput(),data.width,data.height,passes);svg=runtime.sharedFinish(coordinates,passes,{...data,unlimited});metrics.contour_compute=coordinates?'WebGPU integer':'Rust CPU';metrics.contour_gpu_fallback=coordinates?null:contourGpuError;metrics.contour_seconds=(performance.now()-started)/1000;metrics.raster_refit=runtime.stats().raster_refit;if(coordinates)backend='WebGPU contours + Rust WASM';}
  }
  else{const result=await traceFixed(runtime,pixels,data.width,data.height,{...data,prefiltered},emitProgress);svg=result.svg;segments=result.segments;prechecked=result.geometry;metrics={algorithm:result.algorithm,palette:result.palette,logo_reconstruction:result.logo_reconstruction};}
  emitProgress(90,'Проверка пересечений');let geometry=prechecked;let smoothing_fallback=false;try{geometry??=await auditNative(svg);}catch(error){if(data.category!=='photo')throw error;const base=runtime.rasterBase();try{if(!base)throw error;geometry=await auditNative(base);svg=base;metrics.raster_refit_rejected=true;}catch{svg=runtime.fallback();geometry=await auditNative(svg);smoothing_fallback=true;}}
  emitProgress(100,'Готово');self.postMessage({geometry,smoothing_fallback,metrics,segments:segments?.buffer,svg,paths:(svg.match(/<path /g)||[]).length,colors:(svg.match(/id="color-/g)||[]).length,seconds:(performance.now()-start)/1000,backend},segments?[segments.buffer]:[]);
 }catch(error){self.postMessage({error:String(error.message??error),requestId:data.requestId});}
};
