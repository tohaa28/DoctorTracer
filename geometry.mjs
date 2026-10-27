// SPDX-License-Identifier: MIT
// Desktop's independent Clipper intersection audit, with shared-boundary fallback.
import ClipperLib from './vendor/clipper.mjs?v=0.16.0';
import {svgGroups} from './exports.mjs?v=0.16.0';
import {contours} from './paths.mjs?v=0.16.0';
const SCALE=1e7;
const bounds=paths=>{let l=Infinity,t=Infinity,r=-Infinity,b=-Infinity;for(const path of paths)for(const p of path){l=Math.min(l,p.X);r=Math.max(r,p.X);t=Math.min(t,p.Y);b=Math.max(b,p.Y);}return[l,t,r,b];};
const cells=b=>{const keys=[];const span=128*SCALE;for(let y=Math.floor(b[1]/span);y<=Math.floor(b[3]/span);y++)for(let x=Math.floor(b[0]/span);x<=Math.floor(b[2]/span);x++)keys.push(x+','+y);return keys;};
export function audit(svg){
 const seen=[],grid=new Map();let pairs=0,maxArea=0;
 for(const group of svgGroups(svg)){
  const polygons=group.paths.flatMap(p=>contours(p.d,p.x,p.y));if(!polygons.length)continue;const b=bounds(polygons);const keys=cells(b),candidates=new Set(keys.flatMap(k=>grid.get(k)||[]));
  for(const j of candidates){const other=seen[j];const c=other.bounds;if(b[0]>=c[2]||b[2]<=c[0]||b[1]>=c[3]||b[3]<=c[1])continue;const clip=new ClipperLib.Clipper();clip.AddPaths(polygons,ClipperLib.PolyType.ptSubject,true);clip.AddPaths(other.polygons,ClipperLib.PolyType.ptClip,true);const result=new ClipperLib.Paths();clip.Execute(ClipperLib.ClipType.ctIntersection,result,ClipperLib.PolyFillType.pftNonZero,ClipperLib.PolyFillType.pftNonZero);pairs++;const area=Math.abs(result.reduce((s,p)=>s+ClipperLib.Clipper.Area(p),0))/SCALE**2;maxArea=Math.max(maxArea,area);if(area>.0001)throw Error('Vector overlap '+area+' px²');}
  const id=seen.length;seen.push({bounds:b,polygons});for(const k of keys){if(!grid.has(k))grid.set(k,[]);grid.get(k).push(id);}
 }
 return{pairs,max_intersection_area_px2:maxArea,tolerance_px2:.0001};
}

let native;
export async function auditNative(svg,{wasmBinary}={}){
 if(!native){const {default:init}=await import('./vendor/audit.mjs?v=0.16.0');native=await init(wasmBinary?{wasmBinary}:{locateFile:()=>new URL('./vendor/audit.wasm?v=0.16.0',import.meta.url).href});}
 native._audit_start();let maxArea=0;
 for(const group of svgGroups(svg)){
  const paths=group.paths.flatMap(p=>contours(p.d,p.x,p.y));if(!paths.length)continue;
  let size=0;for(const p of paths)size+=1+p.length*2;const bytes=new Float64Array(size);let i=0;for(const p of paths){bytes[i++]=p.length;for(const point of p){bytes[i++]=point.X;bytes[i++]=point.Y;}}
  const ptr=native._malloc(bytes.byteLength);if(!ptr)throw Error('Недостаточно памяти при проверке геометрии');let area;try{native.HEAPF64.set(bytes,ptr/8);area=native._audit_add(ptr,bytes.length);}finally{native._free(ptr);}if(area<0||area>.0001)throw Error('Vector overlap '+area+' px²');maxArea=Math.max(maxArea,area);
 }return{pairs:native._audit_pairs(),max_intersection_area_px2:maxArea,tolerance_px2:.0001};
}

export async function partitionNative(shapes,w,h,{wasmBinary}={}){
 if(!native){const {default:init}=await import('./vendor/audit.mjs?v=0.16.0');native=await init(wasmBinary?{wasmBinary}:{locateFile:()=>new URL('./vendor/audit.wasm?v=0.16.0',import.meta.url).href});}native._partition_start(w,h);const groups=new Map();
 for(const item of [...shapes].reverse()){
  const paths=contours(item.d);if(!paths.length)continue;let size=0;for(const p of paths)size+=1+p.length*2;const bytes=new Float64Array(size);let i=0;for(const p of paths){bytes[i++]=p.length;for(const point of p){bytes[i++]=point.X;bytes[i++]=point.Y;}}
  const ptr=native._malloc(bytes.byteLength);if(!ptr)throw Error('Недостаточно памяти');let data;try{native.HEAPF64.set(bytes,ptr/8);const result=native._partition_add(ptr,bytes.length);if(!result)throw Error('Clipper partition failed');data=native.UTF8ToString(result);}finally{native._free(ptr);}if(data){if(!groups.has(item.color))groups.set(item.color,[]);groups.get(item.color).push(data);}
 }return groups;
}
