// SPDX-License-Identifier: GPL-3.0-or-later
// Shared planar color graph with analytically paired interfaces.
import initMask from './vendor/mask.mjs?v=0.18.0';import initPaths from './vendor/pathkit.mjs?v=0.18.0';
import {gpuAssign} from './gpu.js?v=0.18.0';
import {auditNative} from './geometry.mjs?v=0.18.0';
let maskRuntime,pathRuntime;
async function binary(url){return new Uint8Array(await(await fetch(url)).arrayBuffer());}
export async function curveRuntime({maskBinary,pathBinary}={}){
 maskRuntime??=await initMask(maskBinary?{wasmBinary:maskBinary}:{locateFile:()=>new URL('./vendor/mask.wasm?v=0.18.0',import.meta.url).href});
 pathRuntime??=await initPaths(pathBinary?{wasmBinary:pathBinary}:{locateFile:()=>new URL('./vendor/pathkit.wasm?v=0.18.0',import.meta.url).href});
 return{mask:maskRuntime,paths:pathRuntime};
}
function data(path){let out='',current=[0,0];for(const command of path.toCmds()){const[verb,...p]=command;if(verb===0){out+='M'+p.join(' ')+' ';current=p;}else if(verb===1){out+='L'+p.join(' ')+' ';current=p;}else if(verb===2){const[cx,cy,x,y]=p;const c1=[current[0]+2/3*(cx-current[0]),current[1]+2/3*(cy-current[1])],c2=[x+2/3*(cx-x),y+2/3*(cy-y)];out+='C'+[...c1,...c2,x,y].join(' ')+' ';current=[x,y];}else if(verb===4){out+='C'+p.join(' ')+' ';current=p.slice(-2);}else if(verb===5)out+='Z ';else throw Error('Unsupported Skia path verb');}return out;}
export function traceMask(runtime,mask,w,h,tolerance=.12,alpha=1){const ptr=runtime._malloc(mask.length);try{runtime.HEAPU8.set(mask,ptr);const result=runtime._trace_mask(ptr,w,h,tolerance,alpha);if(!result)throw Error('Potrace mask failed');return runtime.UTF8ToString(result);}finally{runtime._free(ptr);}}
export async function traceFixed(runtime,pixels,w,h,config,progress=()=>{}){
 const photo=config.category==='photo',aa=config.category==='aa';let a=pixels;
 if(!config.prefiltered&&(photo||config.detail===0))a=runtime.stage(a,w,h,{kind:0});
 const raw=config.palette?.length?config.palette:runtime.stage(a,w,h,{kind:2,colors:config.colors,extra:photo?1:0});const palette=Array.isArray(raw)?raw.map(c=>typeof c==='string'?c.slice(1).match(/../g).map(v=>parseInt(v,16)):c):Array.from({length:raw.length/3},(_,i)=>Array.from(raw.slice(i*3,i*3+3)));
 const layered=aa&&a.some((v,i)=>i%4===3&&v<128),scale=aa&&!layered&&w*h<=2000000&&w<=2048&&h<=2048?2:1;const working=scale===2?runtime.stage(a,w,h,{kind:6}):a,ww=w*scale,hh=h*scale;
 let labels=config.gpu&&photo?await gpuAssign(working,ww,hh,palette,700):null;labels??=runtime.stage(working,ww,hh,{kind:3,palette,extra:photo?700:aa?(65536|((3*scale)<<17)):0});labels=runtime.stage(labels,ww,hh,{kind:4,palette,colors:palette.length,extra:(photo?Math.max(8,config.speckle):Math.max(1,config.speckle))|((config.artifact_strength??0)<<16)});
 // A single planar graph owns every interface. Never fit adjacent color
 // masks independently: subtraction alone prevents overlaps, not gaps.
  progress(70,'Построение общих границ цветов');
  const shared=Int32Array.from(labels,v=>v===255?-1:v);
  let exactGrid=true;for(let i=0;i<a.length;i+=4){if(a[i+3]!==0&&a[i+3]!==255){exactGrid=false;break;}if(a[i+3]===255&&!palette.some(p=>p[0]===a[i]&&p[1]===a[i+1]&&p[2]===a[i+2])){exactGrid=false;break;}}
  let orthogonal=true;
  for(let y=1;y<hh&&orthogonal;y++){let start=-1;for(let x=0;x<=ww;x++){const edge=x<ww&&labels[y*ww+x]!==labels[(y-1)*ww+x];if(edge&&start<0)start=x;else if(!edge&&start>=0){if(x-start<3){orthogonal=false;break;}start=-1;}}}
  for(let x=1;x<ww&&orthogonal;x++){let start=-1;for(let y=0;y<=hh;y++){const edge=y<hh&&labels[y*ww+x]!==labels[y*ww+x-1];if(edge&&start<0)start=y;else if(!edge&&start>=0){if(y-start<3){orthogonal=false;break;}start=-1;}}}
  const polygon=!!config.polygon||exactGrid||orthogonal;
  let svg=runtime.shared(shared,palette,ww,hh,config.detail,!polygon,{fixed:true,polygon});
  svg=svg.replace(/width="[^"]+" height="[^"]+"/,`width="${w}" height="${h}"`);
  let geometry;try{geometry=await auditNative(svg);}catch{
   svg=runtime.shared(shared,palette,ww,hh,config.detail,false,{fixed:true,polygon:true});
   svg=svg.replace(/width="[^"]+" height="[^"]+"/,`width="${w}" height="${h}"`);geometry=await auditNative(svg);
  }
  const segments=new Uint8Array(w*h*4);for(let i=0;i<w*h;i++){const label=labels[(Math.floor(i/w)*scale)*ww+(i%w)*scale];if(label!==255)segments.set([...palette[label],255],i*4);}
  return{svg,segments,palette,geometry,algorithm:'shared planar color graph'};
}
