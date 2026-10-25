import assert from 'node:assert/strict';import fs from 'node:fs/promises';import createTracer from '../web/rust-tracer.mjs';import {pdfBytes,svgGroups} from '../web/exports.mjs';
const wasmBinary=await fs.readFile(new URL('../web/doctortracer.wasm',import.meta.url));let progress=[];const runtime=await createTracer({wasmBinary,onProgress:(p)=>progress.push(p)});
const w=64,h=48,pixels=new Uint8Array(w*h*4);
for(let y=2;y<46;y++)for(let x=2;x<62;x++)pixels.set(x<32?[210,30,80,255]:[20,160,210,255],4*(y*w+x));
// Tiny interior alpha hole, not visible to a scanline transparency heuristic.
pixels.fill(0,4*(12*w+12),4*(12*w+12)+4);
const options={colors:2,detail:2,speckle:0,category:'hard'};
const a=runtime.trace(pixels,w,h,options);assert(progress.every((v,i)=>i===0||v>=progress[i-1]));assert.equal(a,runtime.trace(pixels,w,h,options));assert.equal(svgGroups(a).length,2);assert.match(a,/<g id="image">/);assert.match(a,/C/);assert((a.match(/M/g)||[]).length>=3,'one-pixel hole contour');assert(!a.includes('<image'));assert(!a.includes('NaN'));assert.equal(progress.at(-1),100);assert(progress.includes(60));
const polygon=runtime.trace(pixels,w,h,{...options,polygon:true});assert(!/\\bC[-\\d ]/.test(polygon));assert.match(polygon,/L/);
assert.match(runtime.trace(new Uint8Array([30,90,200,255]),1,1,{...options,speckle:0}),/<path /,'visible singleton pixel');
const empty=runtime.trace(new Uint8Array(12*10*4),12,10,options);assert(!empty.includes('<path'));
for(const cfg of [{colors:129},{colors:1},{detail:3},{speckle:101}])assert.throws(()=>runtime.trace(pixels,w,h,{...options,...cfg}));
assert.throws(()=>runtime.trace(pixels,0,h,options));
const pdf=pdfBytes(a),text=new TextDecoder().decode(pdf);assert.equal((text.match(/\/Subtype \/Form/g)||[]).length,2);assert.equal((text.match(/\/Group <</g)||[]).length,2);assert(!text.includes('/Subtype /Image'));assert.equal((text.match(/ Do/g)||[]).length,2);
const xref=Number(/startxref\n(\d+)/.exec(text)[1]);assert.equal(text.slice(xref,xref+4),'xref');
for(const [offset,id] of [...text.matchAll(/(\d+) 0 obj/g)].map(m=>[m.index,Number(m[1])])){assert(text.includes(String(offset).padStart(10,'0')+' 00000 n '),'xref '+id);}
await fs.mkdir(new URL('../build/tests/',import.meta.url),{recursive:true});await fs.writeFile(new URL('../build/tests/rust-synthetic.svg',import.meta.url),a);await fs.writeFile(new URL('../build/tests/rust-synthetic.pdf',import.meta.url),pdf);
console.log(JSON.stringify({ok:true,rustWasmBytes:wasmBinary.length,determinism:true,colorGroups:true,curves:true,transparency:true,polygon:true,invalidInput:true,pdfXref:true,progress:true}));
