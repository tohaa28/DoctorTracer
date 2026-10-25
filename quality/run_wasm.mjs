import fs from 'node:fs/promises';import path from 'node:path';
import createTracer from '../web/rust-tracer.mjs';
import {curveRuntime,traceFixed} from '../web/desktop-curves.mjs';
import {auditNative} from '../web/geometry.mjs';
const manifest=process.argv[2],folder=path.dirname(manifest),jobs=JSON.parse(await fs.readFile(manifest,'utf8'));
const runtime=await createTracer({wasmBinary:await fs.readFile('web/doctortracer.wasm')});
await curveRuntime({maskBinary:await fs.readFile('web/vendor/mask.wasm'),pathBinary:await fs.readFile('web/vendor/pathkit.wasm')});
await auditNative('<svg/>',{wasmBinary:await fs.readFile('web/vendor/audit.wasm')});
const results={};for(const c of jobs){const start=performance.now();try{
 const pixels=await fs.readFile(path.join(folder,c.source));let svg;
 if(c.config.category==='photo'&&!c.config.colors)svg=runtime.trace(pixels,c.w,c.h,c.config);
 else svg=(await traceFixed(runtime,pixels,c.w,c.h,c.config)).svg;
 const audit=await auditNative(svg);await fs.writeFile(path.join(folder,c.output),svg);
 results[c.output]={status:'ok',seconds:(performance.now()-start)/1000,audit};
 }catch(e){results[c.output]={status:'error',error:String(e)};}console.log(c.id,results[c.output].status);}
await fs.writeFile(path.join(folder,'wasm-results.json'),JSON.stringify(results,null,2));
