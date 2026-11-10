import fs from 'node:fs/promises';import assert from 'node:assert/strict';import createTracer from '../web/rust-tracer.mjs';import{auditNative}from'../web/geometry.mjs';import{smoothResult}from'../web/post-smooth.mjs';
const root='build/post-smooth/',jobs=JSON.parse(await fs.readFile(root+'jobs.json'));
await auditNative('<svg/>',{wasmBinary:await fs.readFile('web/vendor/audit.wasm')});
const runtime=await createTracer({wasmBinary:await fs.readFile('web/doctortracer.wasm')});
for(const j of jobs){const source=await fs.readFile(root+j.name+'-input.svg','utf8');const native=await fs.readFile(root+j.name+'-native.svg','utf8');const result=await smoothResult(runtime,source,j.strength,true);await fs.writeFile(root+j.name+'-wasm.svg',result.svg);assert.equal(result.svg,native,j.name+' geometry differs');console.log(j.name,result.applied_strength,result.moved);}
console.log('PASS: native/WASM byte-identical finished vectors, strength zero, corners, palette, overlap audit');
