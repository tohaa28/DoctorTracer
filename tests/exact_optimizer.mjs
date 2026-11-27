import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {optimizeExactPath,optimizeExactSvg} from '../web/exact-optimizer.mjs';
import {auditNative} from '../web/geometry.mjs';
import {pdfBytes,epsText} from '../web/exports.mjs';
const cases=JSON.parse(await fs.readFile(new URL('exact_optimizer_cases.json',import.meta.url),'utf8'));
for(const t of cases){
 const r=optimizeExactPath(t.d);
 assert.equal(r.before-r.after,t.removed,t.name);
 assert.equal(r.d,t.expected??t.d,t.name);
 assert.equal(r.skipped,t.skipped??0,t.name);
 assert.equal(optimizeExactPath(r.d).d,r.d,'idempotence '+t.name);
}
const base='<svg xmlns="http://www.w3.org/2000/svg" width="512" height="400" viewBox="0 0 512 400"><g fill="#ff0000"><path fill="#ff0000" d="'+cases[0].d+'"/></g></svg>';
const candidate=optimizeExactSvg(base);
assert.equal(candidate.removed,3);
assert.equal(candidate.svg,base.replace(cases[0].d,cases[0].expected));
await auditNative(candidate.svg,{wasmBinary:await fs.readFile('web/vendor/audit.wasm')});
const cubic='<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><g fill="#000000"><path fill="#000000" d="'+cases[1].d+'"/></g></svg>';
const fitted=optimizeExactSvg(cubic);assert.equal(fitted.cubic,1);
await auditNative(fitted.svg);
assert.match(epsText(fitted.svg),/curveto/);
assert.match(new TextDecoder().decode(pdfBytes(fitted.svg)),/8 0 8 8 16 8 c/);
assert.throws(()=>optimizeExactSvg('<svg stroke="red"><path d="M0 0 L1 0 Z"/></svg>'));
console.log('PASS exact geometry: '+cases.length+' cases, true cubics, color/export, audit');
