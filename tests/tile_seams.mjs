import fs from 'node:fs/promises';
import {partitionNative,auditNative} from '../web/geometry.mjs';
import {contours} from '../web/paths.mjs';
const rect=(x,y,w,h)=>`M${x} ${y} L${x+w} ${y} L${x+w} ${y+h} L${x} ${y+h} Z`;
await auditNative('<svg/>',{wasmBinary:await fs.readFile('web/vendor/audit.wasm')});
const cases=[
 {name:'solid',shapes:[{color:'#ff0000',d:rect(16,16,480,480)}],rings:1,area:480*480},
 {name:'same-color-neighbors',shapes:[{color:'#ff0000',d:rect(16,16,240,480)},{color:'#ff0000',d:rect(256,16,240,480)}],rings:1,area:480*480},
 {name:'hole-crossing-tiles',shapes:[{color:'#ff0000',d:rect(16,16,480,480)+' M96 96 L96 416 L416 416 L416 96 Z'}],rings:2,area:480*480-320*320}
];
for(const test of cases){
 const groups=await partitionNative(test.shapes,512,512),paths=groups.get('#ff0000');
 if(paths.length!==1)throw Error(test.name+': color still split into paths');
 const rings=contours(paths[0]);if(rings.length!==test.rings)throw Error(test.name+': tile rings remain '+rings.length);
 const area=Math.abs(rings.reduce((sum,r)=>sum+r.reduce((s,p,i)=>{const q=r[(i+1)%r.length];return s+p.X*q.Y-q.X*p.Y;},0)/2,0))/1e14;
 if(Math.abs(area-test.area)>.0001)throw Error(test.name+': coverage changed '+area);
 if(rings.some(r=>r.some(p=>[128,256,384].some(n=>p.X===n*1e7||p.Y===n*1e7))))throw Error(test.name+': internal grid vertex remains');
}
const groups=await partitionNative([{color:'#ff0000',d:rect(16,16,480,480)},{color:'#0000ff',d:rect(96,96,320,320)}],512,512);
const svg='<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512">'+[...groups].map(([c,p])=>`<g fill="${c}"><path fill="${c}" d="${p.join(' ')}"/></g>`).join('')+'</svg>';
await auditNative(svg);await fs.mkdir('build/tile-seams',{recursive:true});await fs.writeFile('build/tile-seams/stitched.svg',svg);
console.log(JSON.stringify({ok:true,cases:4,internalTileEdges:0,exactArea:true,holesPreserved:true,noOverlap:true}));
