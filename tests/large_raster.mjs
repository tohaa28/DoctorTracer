import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import createTracer from '../web/rust-tracer.mjs';
import {auditNative} from '../web/geometry.mjs';
import {svgGroups} from '../web/exports.mjs';
const w=5130,h=1685,pixels=new Uint8Array(w*h*4);
const palette=[[255,0,0],[0,255,0],[0,0,255],[0,0,0]];
for(let y=16;y<1660;y++)for(let x=16;x<5110;x++){
 if(x>=200&&x<400&&y>=200&&y<400)continue;
 const k=Math.min(3,Math.floor(x/1280));pixels.set([...palette[k],255],4*(y*w+x));
}
const runtime=await createTracer({wasmBinary:await fs.readFile('web/doctortracer.wasm')});
const svg=runtime.trace(pixels,w,h,{category:'hard',colors:4,palette,detail:2,speckle:0,prefiltered:true,smooth:false,polygon:true});
assert.match(svg,/width="5130" height="1685"/);
assert.equal(svgGroups(svg).length,4);
assert.ok(svg.includes('data-boundary-contract="paired"'));
await auditNative(svg,{wasmBinary:await fs.readFile('web/vendor/audit.wasm')});
assert.equal(runtime.segments().byteLength,w*h*4);
console.log('PASS native rebuilt WASM trace, 5130x1685, 4 colors, alpha hole, audited');
