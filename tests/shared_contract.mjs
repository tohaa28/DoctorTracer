import fs from 'node:fs/promises';import createTracer from '../web/rust-tracer.mjs';
const root='build/shared-contract/',jobs=JSON.parse(await fs.readFile(root+'jobs.json'));
const runtime=await createTracer({wasmBinary:await fs.readFile('web/doctortracer.wasm')});
for(const j of jobs){const raw=await fs.readFile(root+j.name+'.i32'),labels=new Int32Array(Uint8Array.from(raw).buffer);const svg=runtime.shared(labels,j.palette,j.w,j.h,1,j.smooth,{fixed:true,polygon:!j.smooth});if(!svg.includes('data-boundary-contract="paired"'))throw Error('No contract '+j.name);await fs.writeFile(root+j.name+'-wasm.svg',svg);}
console.log(JSON.stringify({ok:true,cases:jobs.length,rustContract:true}));
