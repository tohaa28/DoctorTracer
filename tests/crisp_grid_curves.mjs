import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import createTracer from '../web/rust-tracer.mjs';
import {traceFixed} from '../web/desktop-curves.mjs';
import {auditNative} from '../web/geometry.mjs';
// Run the shipped Rust/WASM binary and the real JS routing, not a fake SVG.
const wasmBinary=await fs.readFile(new URL('../web/doctortracer.wasm',import.meta.url));
const runtime=await createTracer({wasmBinary});
await auditNative('<svg/>',{wasmBinary:await fs.readFile(new URL('../web/vendor/audit.wasm',import.meta.url))});
const w=96,h=88;
const raster=(sample)=>{
 const pixels=new Uint8Array(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const on=sample(x,y),i=4*(y*w+x);
  pixels[i]=pixels[i+1]=pixels[i+2]=on?0:255;pixels[i+3]=255;
 }
 return pixels;
};
const opts={category:'hard',colors:2,detail:2,speckle:0,gpu:false,polygon:false,smooth:true};
const rectangle=raster((x,y)=>x>=14&&x<78&&y>=19&&y<64);
const circle=raster((x,y)=>(x-48)**2+(y-44)**2<26**2);
const mixed=raster((x,y)=>((x>=4&&x<30&&y>=6&&y<25)||((x-58)**2+(y-47)**2<22**2)));
const rect=await traceFixed(runtime,rectangle,w,h,opts);
assert.equal(rect.adaptiveCrispCurves,false,'pure horizontal/vertical rectangle stays polygon');
assert.doesNotMatch(rect.svg,/\bC[-\d. ]/,'rectilinear artwork must retain exact corners');
const curved=await traceFixed(runtime,circle,w,h,opts);
assert.equal(curved.adaptiveCrispCurves,true,'a binary pixelated circle needs curves');
assert.match(curved.svg,/\bC[-\d. ]/,'smooth common boundaries must use cubic Beziers');
assert.match(curved.svg,/data-boundary-contract="paired"/,'contract must remain paired');
const forced=await traceFixed(runtime,circle,w,h,{...opts,polygon:true});
assert.equal(forced.adaptiveCrispCurves,false);
assert.doesNotMatch(forced.svg,/\bC[-\d. ]/);
const off=await traceFixed(runtime,circle,w,h,{...opts,smooth:false});
assert.equal(off.adaptiveCrispCurves,false);
assert.doesNotMatch(off.svg,/\bC[-\d. ]/);
const combo=await traceFixed(runtime,mixed,w,h,opts);
assert.equal(combo.adaptiveCrispCurves,true);
assert.match(combo.svg,/\bC[-\d. ]/);
for(const result of [rect,curved,forced,off,combo]){
 assert.ok(!result.svg.includes('NaN'));
 assert.ok(result.svg.includes('data-boundary-contract="paired"'));
 assert.deepEqual(result.geometry?.issues||[],[],'no topology defects');
}
console.log('PASS adaptive no-AA curve tracing: exact rectangles, cubic binary circle, explicit polygon off, mixed contours and paired ownership');
