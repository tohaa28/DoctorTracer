import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import createTracer from '../web/tracer.mjs';
const wasmBinary=await fs.readFile(new URL('../web/tracer.wasm',import.meta.url));
const runtime=await createTracer({wasmBinary});
function trace(bytes,w,h,colors=3,detail=2,speckle=0,polygon=0){const ptr=runtime._malloc(bytes.length);try{runtime.HEAPU8.set(bytes,ptr);const result=runtime._trace_rgba(ptr,w,h,colors,detail,speckle,polygon);return result?runtime.UTF8ToString(result):null;}finally{runtime._free(ptr);}}
const width=64,height=48,pixels=new Uint8Array(width*height*4);
for(let y=3;y<height-3;y++)for(let x=3;x<width-3;x++){const i=4*(y*width+x);pixels.set(x<width/2?[210,30,80,255]:[20,160,210,255],i);}
// Asymmetric top-left marker checks vertical coordinate orientation.
pixels.set([20,210,40,255],4*(8*width+9));
const a=trace(pixels,width,height),b=trace(pixels,width,height);assert.equal(a,b);assert.match(a,/<svg /);assert.match(a,/<path /);assert.match(a,/C/);assert(!a.includes('<image'));assert(!a.includes('NaN'));assert(runtime._trace_paths()>=2);
const empty=trace(new Uint8Array(12*10*4),12,10);assert(!empty.includes('<path'));
const polygon=trace(pixels,width,height,3,2,0,1);assert(!polygon.includes('C'));assert.match(polygon,/L/);
assert.equal(trace(pixels,0,height),null);assert.equal(trace(pixels,width,height,129),null);
await fs.mkdir(new URL('../build/tests/',import.meta.url),{recursive:true});await fs.writeFile(new URL('../build/tests/synthetic.svg',import.meta.url),a);
console.log(JSON.stringify({ok:true,deterministic:true,transparent:true,polygon:true,invalidInput:true,wasmBytes:wasmBinary.length}));
