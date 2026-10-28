import fs from 'node:fs/promises';import createTracer from '../web/rust-tracer.mjs';
const root='build/aa-support/',jobs=JSON.parse(await fs.readFile(root+'jobs.json'));
const runtime=await createTracer({wasmBinary:await fs.readFile('web/doctortracer.wasm')});
for(const j of jobs){const pixels=await fs.readFile(root+j.key+'.rgba'),expected=await fs.readFile(root+j.key+'.labels');const labels=runtime.stage(pixels,j.w,j.h,{kind:3,palette:j.palette,extra:65536|(3<<17)});if(!Buffer.from(labels).equals(expected))throw Error('Rust assignment differs '+j.key);}
console.log(JSON.stringify({ok:true,cases:jobs.length,rustExact:true}));
