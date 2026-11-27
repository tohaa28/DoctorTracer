import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import createTracer from '../web/rust-tracer.mjs';
import {auditNative} from '../web/geometry.mjs';
import {svgGroups,pdfBytes,epsText} from '../web/exports.mjs';
import {contours} from '../web/paths.mjs';
import {intermediateResult,reduceNodesResult} from '../web/color-node-tools.mjs';
const fixtures=JSON.parse(await fs.readFile('tests/color_node_cases.json','utf8'));
const svg=paths=>'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><g id="image">'+paths.map(([c,d])=>'<g fill="'+c+'"><path fill="'+c+'" d="'+d+'"/></g>').join('')+'</g></svg>';
const area=s=>svgGroups(s).flatMap(g=>g.paths).flatMap(p=>contours(p.d)).reduce((sum,p)=>sum+p.reduce((a,v,i)=>{const b=p[(i+1)%p.length];return a+v.X*b.Y-v.Y*b.X;},0)/2e14,0);
await auditNative('<svg/>',{wasmBinary:await fs.readFile('web/vendor/audit.wasm')});
const runtime=await createTracer({wasmBinary:await fs.readFile('web/doctortracer.wasm')});
const source=svg(fixtures.strip);
assert.equal((await intermediateResult(runtime,source,0)).svg,source);
assert.equal((await intermediateResult(runtime,source,1)).svg,source);
const clean=await intermediateResult(runtime,source,100);
assert.equal(clean.removed_elements,1,JSON.stringify(clean));
assert.equal(svgGroups(clean.svg).length,2);
assert.equal(area(source),10000);assert.equal(area(clean.svg),10000);
assert.equal((await intermediateResult(runtime,clean.svg,100)).svg,clean.svg);
const unrelated=source.replaceAll('#800080','#00ff00');
assert.equal((await intermediateResult(runtime,unrelated,100)).svg,unrelated);
const island=svg(fixtures.island);assert.equal((await intermediateResult(runtime,island,100)).svg,island);
const curved=source.replace('L51 50 L50 48','L51 50 C51 49 50 49 50 48').replace('L51 50 L50 52','C50 49 51 49 51 50 L50 52');
// The earlier deliberately nonpaired input must remain untouched.
assert.equal((await intermediateResult(runtime,curved,100)).svg,curved);
const circle=svg(fixtures.circle);
assert.equal((await reduceNodesResult(runtime,circle,0)).svg,circle);
const reduced=await reduceNodesResult(runtime,circle,100);
assert.ok(reduced.nodes_after<reduced.nodes_before,JSON.stringify(reduced));
assert.match(reduced.svg,/C/);assert.equal(svgGroups(reduced.svg).length,2);
assert.ok(Math.abs(area(reduced.svg)-10000)<0.001);
assert.equal((await reduceNodesResult(runtime,circle,100)).svg,reduced.svg);
assert.ok(!new TextDecoder().decode(pdfBytes(reduced.svg)).includes('/Subtype /Image'));
assert.match(epsText(reduced.svg),/curveto/);
console.log('PASS intermediate split, exact area, preserve real colors/island, node reduction',clean.nodes_before,clean.nodes_after,reduced.nodes_before,reduced.nodes_after);

const fringes=JSON.parse(await fs.readFile('tests/fringe_cases.json','utf8'));
for(const key of ['annulus','crescent']){
 const input=svg(fringes[key]);assert.equal((await intermediateResult(runtime,input,0)).svg,input);
 assert.equal((await intermediateResult(runtime,input,20)).svg,input);
 const out=await intermediateResult(runtime,input,100);
 assert.equal(out.removed_elements,1,key+' '+JSON.stringify(out));
 assert.equal(svgGroups(out.svg).length,2,key);
 assert.ok(Math.abs(area(input)-area(out.svg))<.001,key+' coverage');
 assert.match(out.svg,/C/,key);
 assert.equal((await intermediateResult(runtime,out.svg,100)).svg,out.svg);
 const sourceGold=svgGroups(input).find(g=>g.color==='#d39f50');
 const targetGold=svgGroups(out.svg).find(g=>g.color==='#d39f50');
 const goldArea=g=>g.paths.flatMap(p=>contours(p.d)).reduce((sum,p)=>sum+p.reduce((a,v,i)=>{const b=p[(i+1)%p.length];return a+v.X*b.Y-v.Y*b.X;},0)/2e14,0);
 assert.ok(Math.abs(goldArea(sourceGold)-goldArea(targetGold))<.001,key+' gold geometry unchanged');
}
for(const key of ['wide','unrelated','alpha']){const input=svg(fringes[key]);assert.equal((await intermediateResult(runtime,input,100)).svg,input,key);}
console.log('PASS JPEG-like gray curved crescent and ring, coverage, exact retained gold, preserve wide gray / third ink / transparency');
