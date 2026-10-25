// SPDX-License-Identifier: GPL-3.0-or-later
// Same Potrace 1.16 masks and Skia PathOps visibility subtraction as desktop.
import initMask from './vendor/mask.mjs?v=0.12.0.1';import initPaths from './vendor/pathkit.mjs?v=0.12.0.1';
import {gpuAssign} from './gpu.js?v=0.12.0.1';
import {normalizeWinding} from './paths.mjs?v=0.12.0.1';
import {partitionNative,auditNative} from './geometry.mjs?v=0.12.0.1';
let maskRuntime,pathRuntime;
async function binary(url){return new Uint8Array(await(await fetch(url)).arrayBuffer());}
export async function curveRuntime({maskBinary,pathBinary}={}){
 maskRuntime??=await initMask(maskBinary?{wasmBinary:maskBinary}:{locateFile:()=>new URL('./vendor/mask.wasm?v=0.12.0.1',import.meta.url).href});
 pathRuntime??=await initPaths(pathBinary?{wasmBinary:pathBinary}:{locateFile:()=>new URL('./vendor/pathkit.wasm?v=0.12.0.1',import.meta.url).href});
 return{mask:maskRuntime,paths:pathRuntime};
}
function data(path){let out='',current=[0,0];for(const command of path.toCmds()){const[verb,...p]=command;if(verb===0){out+='M'+p.join(' ')+' ';current=p;}else if(verb===1){out+='L'+p.join(' ')+' ';current=p;}else if(verb===2){const[cx,cy,x,y]=p;const c1=[current[0]+2/3*(cx-current[0]),current[1]+2/3*(cy-current[1])],c2=[x+2/3*(cx-x),y+2/3*(cy-y)];out+='C'+[...c1,...c2,x,y].join(' ')+' ';current=[x,y];}else if(verb===4){out+='C'+p.join(' ')+' ';current=p.slice(-2);}else if(verb===5)out+='Z ';else throw Error('Unsupported Skia path verb');}return out;}
export function traceMask(runtime,mask,w,h,tolerance=.12,alpha=1){const ptr=runtime._malloc(mask.length);try{runtime.HEAPU8.set(mask,ptr);const result=runtime._trace_mask(ptr,w,h,tolerance,alpha);if(!result)throw Error('Potrace mask failed');return runtime.UTF8ToString(result);}finally{runtime._free(ptr);}}
export async function traceFixed(runtime,pixels,w,h,config,progress=()=>{}){
 const {mask,paths:pk}=await curveRuntime();const photo=config.category==='photo',aa=config.category==='aa';let a=pixels;
 if(!config.prefiltered&&(photo||config.detail===0))a=runtime.stage(a,w,h,{kind:0});
 const raw=config.palette?.length?config.palette:runtime.stage(a,w,h,{kind:2,colors:config.colors,extra:photo?1:0});const palette=Array.isArray(raw)?raw.map(c=>typeof c==='string'?c.slice(1).match(/../g).map(v=>parseInt(v,16)):c):Array.from({length:raw.length/3},(_,i)=>Array.from(raw.slice(i*3,i*3+3)));
 const layered=aa&&a.some((v,i)=>i%4===3&&v<128),scale=aa&&!layered&&w*h<=2000000&&w<=2048&&h<=2048?2:1;const working=scale===2?runtime.stage(a,w,h,{kind:6}):a,ww=w*scale,hh=h*scale;
 let labels=config.gpu&&photo?await gpuAssign(working,ww,hh,palette,700):null;labels??=runtime.stage(working,ww,hh,{kind:3,palette,extra:photo?700:aa?(65536|((3*scale)<<17)):0});labels=runtime.stage(labels,ww,hh,{kind:4,colors:palette.length,extra:(photo?Math.max(8,config.speckle):Math.max(1,config.speckle))|(2<<16)});
 const counts=new Uint32Array(palette.length);for(const label of labels)if(label!==255)counts[label]++;const order=Array.from(counts.keys()).filter(k=>counts[k]).sort((a,b)=>counts[b]-counts[a]||a-b);const shapes=[];
 for(const [done,k] of order.entries()){progress(35+Math.floor(35*done/Math.max(1,order.length)),'Построение контуров');const silhouette=layered&&done===0,bitmap=silhouette?Uint8Array.from(runtime.stage(a,w,h,{kind:6}),v=>v):Uint8Array.from(labels,v=>v===k?1:0);const maskBytes=silhouette?Uint8Array.from({length:w*h*4},(_,i)=>bitmap[4*i+3]>=128?1:0):bitmap;let d=traceMask(mask,maskBytes,silhouette?w*2:ww,silhouette?h*2:hh,(config.curveTolerance??.12)*[4,2,1][config.detail],config.polygon?0:config.alphamax??1);if(d&&(scale>1||silhouette)){const fitted=pk.FromSVGString(d);const factor=silhouette?.5:1/scale;fitted.transform(factor,0,0,0,factor,0,0,0,1);d=data(fitted);fitted.delete();}if(d)shapes.push({color:'#'+palette[k].map(v=>v.toString(16).padStart(2,'0')).join(''),d});}
 let groups=new Map();const originalShapes=[...shapes],covered=pk.NewPath();
 let curvesFailed=false;try{for(const item of shapes.reverse()){const original=pk.FromSVGString(item.d);if(!original)throw Error('Invalid fitted path');let visible;try{visible=pk.MakeFromOp(original,covered,pk.PathOp.DIFFERENCE);if(!visible)throw Error('Skia difference failed');const d=normalizeWinding(data(visible));if(d){if(!groups.has(item.color))groups.set(item.color,[]);groups.get(item.color).push(d);const material=pk.FromSVGString(d);covered.addPath(material);material.delete();}}finally{original.delete();visible?.delete();}}}catch{curvesFailed=true;}finally{covered.delete();}
 if(curvesFailed||w>128||h>128){progress(80,'Объединение цветов и устранение наложений');groups=await partitionNative(originalShapes,w,h);}
 const makeSVG=()=>`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" data-color-objects="merged"><g id="image">`+[...groups].map(([color,paths])=>`<g id="color-${color.slice(1)}" fill="${color}" fill-rule="nonzero">${paths.map(d=>`<path fill="${color}" d="${d}"/>`).join('')}</g>`).join('')+'</g></svg>';
 let svg=makeSVG(),geometry;try{geometry=await auditNative(svg);}catch{groups=await partitionNative(originalShapes,w,h);svg=makeSVG();geometry=await auditNative(svg);}
 const segments=new Uint8Array(w*h*4);for(let i=0;i<w*h;i++){const label=labels[(Math.floor(i/w)*scale)*ww+(i%w)*scale];if(label!==255)segments.set([...palette[label],255],i*4);}return{svg,segments,palette,geometry,algorithm:'desktop-potrace-skia'};
}
