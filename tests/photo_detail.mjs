import fs from 'node:fs/promises';import path from 'node:path';import assert from 'node:assert/strict';
import createTracer from '../web/rust-tracer.mjs';import {auditNative} from '../web/geometry.mjs';
const job=JSON.parse(await fs.readFile(process.argv[2],'utf8')),r=await createTracer({wasmBinary:await fs.readFile('web/doctortracer.wasm')});
const a=await fs.readFile(path.join(job.folder,'input.rgba'));const svg=r.trace(a,96,64,job.config);assert(svg.includes('data-shared-boundaries'));
const segments=r.segments();let stroke=0;for(let x=8;x<88;x++)if(segments[(30*96+x)*4]<180)stroke++;assert(stroke>=70,'WASM default cleanup erased thin stroke');
await auditNative(svg,{wasmBinary:await fs.readFile('web/vendor/audit.wasm')});
const detailed=await fs.readFile(path.join(job.folder,'detail.rgba'));
function countDark(p){let n=0;for(let i=0;i<p.length;i+=4)if(p[i]<200)n++;return n;}
r.trace(detailed,272,200,{detail:1});const preserved=countDark(r.segments());r.trace(detailed,272,200,{detail:1,artifact_strength:2});const erased=countDark(r.segments());assert(preserved>erased*1.1,'Default cleanup must retain the thin-detail fixture');console.log({preserved,erased});
console.log('WASM thin-stroke regression fixture passed');
