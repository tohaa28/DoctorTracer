// SPDX-License-Identifier: GPL-3.0-or-later
// Pixel-aware vector fitting: the original binary raster remains byte-identical.
// A 1-pixel cell lattice conveys a +/-0.5-pixel crossing uncertainty.
// Potrace fits global optimal polygons and subpixel cubic curves; two faces
// reuse exactly reversed edges to prevent color gaps or overlaps.
import {contours} from './paths.mjs';
const p=a=>a.map(n=>Number(n.toFixed(2))).join(' ');
const equal=(a,b)=>a[0]===b[0]&&a[1]===b[1];
function parse(d){
 const ts=d.match(/[MLCZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?/g)||[];
 const result=[];let i=0,op='',start=null,at=null,edges=[];
 const close=()=>{if(!start)return;if(!equal(start,at))edges.push({a:at,b:start});if(edges.length)result.push(edges);start=at=null;edges=[];};
 while(i<ts.length){
  if(/^[MLCZ]$/.test(ts[i]))op=ts[i++];
  if(op==='Z'){close();op='';continue;}
  if(op==='M'){if(start)close();start=[+ts[i++],+ts[i++]];at=start;op='L';continue;}
  if(op==='L'){const b=[+ts[i++],+ts[i++]];edges.push({a:at,b});at=b;continue;}
  if(op==='C'){const c=[+ts[i++],+ts[i++]],d=[+ts[i++],+ts[i++]],b=[+ts[i++],+ts[i++]];edges.push({a:at,b,c,d});at=b;continue;}
  throw Error('Malformed Potrace path '+op);
 }if(start)close();return result;
}
function print(parts,reverse=false){
 let out='';
 for(const part of parts){if(!part.length)continue;
  const edges=reverse?part.slice().reverse().map(e=>({a:e.b,b:e.a,c:e.d,d:e.c})):part;
  out+='M'+p(edges[0].a)+' ';
  for(const e of edges)out+=(e.c?'C'+p(e.c)+' '+p(e.d)+' ':'L')+p(e.b)+' ';
  out+='Z ';
 }return out;
}
const area=part=>part.reduce((a,e)=>a+e.a[0]*e.b[1]-e.b[0]*e.a[1],0);
const rectangle=(w,h,back)=>print([[{a:[0,0],b:[w,0]},{a:[w,0],b:[w,h]},{a:[w,h],b:[0,h]},{a:[0,h],b:[0,0]}]],back);
const hex=rgb=>'#'+rgb.map(x=>x.toString(16).padStart(2,'0')).join('');
const paint=(color,d)=>{const ink=hex(color);return '<g id="color-'+ink.slice(1)+'" fill="'+ink+'" fill-rule="nonzero"><path fill="'+ink+'" d="'+d+'"/></g>';};
export function binaryGridClasses(labels,palette,w,h){
 if(labels.length!==w*h||!palette?.length)return null;
 const counts=new Map(),border=new Map();
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){const k=labels[y*w+x];
  if(k!==-1&&(!Number.isInteger(k)||k<0||k>=palette.length))return null;
  counts.set(k,(counts.get(k)||0)+1);
  if(x===0||x===w-1||y===0||y===h-1)border.set(k,(border.get(k)||0)+1);
 }
 if(counts.size!==2)return null;
 const bg=[...border].sort((a,b)=>b[1]-a[1])[0]?.[0],fg=[...counts.keys()].find(k=>k!==bg);
 if(fg===undefined||fg<0||bg===undefined)return null;
 if(border.get(bg)!==2*w+2*h-4)return null; // unsafe edge-touching topology
 return {bg,fg,foreground:counts.get(fg)};
}
export function pixelCenterError(d,mask,w,h,limit=Infinity){
 const rows=Array.from({length:h},()=>[]);
 for(const loop of contours(d))for(let j=0;j<loop.length;j++){
  const a=loop[j],b=loop[(j+1)%loop.length],ax=a.X/1e7,ay=a.Y/1e7,bx=b.X/1e7,by=b.Y/1e7;
  if(ay===by)continue;
  const first=Math.max(0,Math.ceil(Math.min(ay,by)-.5)),last=Math.min(h-1,Math.ceil(Math.max(ay,by)-.5)-1);
  for(let y=first;y<=last;y++)rows[y].push({x:ax+(y+.5-ay)*(bx-ax)/(by-ay),d:by>ay?1:-1});
 }
 let errors=0;
 for(let y=0;y<h;y++){const r=rows[y].sort((a,b)=>a.x-b.x);let wind=0,k=0;
  for(let x=0;x<w;x++){while(k<r.length&&r[k].x<x+.5+1e-9)wind+=r[k++].d;
   if((wind!==0)!==(mask[y*w+x]!==0)&&++errors>limit)return errors;
  }
 }return errors;
}
export async function fitPixelGrid(labels,palette,w,h,{curveRuntime,traceMask,audit,inputDpi,limitFraction=.25,report=()=>{}}={}){
 const cls=binaryGridClasses(labels,palette,w,h);
 if(!cls||cls.foreground<4||!traceMask||!audit||!curveRuntime){report('classes');return null;}
 const mask=new Uint8Array(w*h);let perimeter=0;
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const i=y*w+x,on=labels[i]===cls.fg;mask[i]=+on;
  if(x&&on!==(labels[i-1]===cls.fg))perimeter++;
  if(y&&on!==(labels[i-w]===cls.fg))perimeter++;
 }
 const {mask:engine}=await curveRuntime();
 // 0.18 px tolerance is (0.18 * 25.4/dpi) millimeters. No raster resampling.
 const raw=traceMask(engine,mask,w,h,.18,1.0);
 if(!raw||!raw.includes('C')){report({step:'curve',len:raw?.length||0});return null;}
 const parts=parse(raw);if(!parts.length)return null;
 const face=print(parts),maxErrors=Math.max(2,Math.floor(perimeter*limitFraction));
 const errors=pixelCenterError(face,mask,w,h,maxErrors);
 if(errors>maxErrors){report({step:'pixel centers',errors,maxErrors,perimeter});return null;}
 const opposite=print(parts,true);
 const dominant=parts.reduce((a,b)=>Math.abs(area(b))>Math.abs(area(a))?b:a);
 const bgShape=rectangle(w,h,area(dominant)<0)+' '+opposite;
 const pitch=Number.isFinite(inputDpi)&&inputDpi>0?25.4/inputDpi:null;
 const svg='<svg xmlns="http://www.w3.org/2000/svg" width="'+w+'" height="'+h+'" viewBox="0 0 '+w+' '+h+'" data-shared-boundaries="true" data-boundary-contract="paired" data-quantization-band-px="0.5"'+
  (pitch?' data-pixel-pitch-mm="'+pitch.toFixed(9)+'" data-source-dpi="'+inputDpi+'"':'')+'><g id="image">'+
  (cls.bg<0?'':paint(palette[cls.bg],bgShape))+paint(palette[cls.fg],face)+'</g></svg>';
 try{await audit(svg);}catch(error){report({step:'audit',message:String(error)});return null;}
 return {svg,metrics:{algorithm:'Potrace quantization-aware paired curves',inputDpi:inputDpi??null,pixelPitchMm:pitch,
  uncertaintyPx:.5,sourceBoundaryEdges:perimeter,mismatchedPixelCenters:errors,allowedErrors:maxErrors,estimatedCrossingErrorPx:errors/perimeter,
  bezierSegments:(face.match(/C/g)||[]).length}};
}
