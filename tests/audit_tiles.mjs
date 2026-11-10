import fs from 'node:fs/promises';import path from 'node:path';import {auditNative,partitionNative} from '../web/geometry.mjs';
const file=process.argv[2],folder=path.dirname(file),cases=JSON.parse(await fs.readFile(file));
await auditNative('<svg/>',{wasmBinary:await fs.readFile('web/vendor/audit.wasm')});
for(const c of cases){let accepted=true;try{await auditNative(await fs.readFile(path.join(folder,c.file),'utf8'));}catch{accepted=false;}if(accepted!==c.accepted)throw Error('Audit acceptance differs '+c.file);}
const shapes=[];for(let i=0;i<100;i++){const x=(i%10)*47,y=Math.floor(i/10)*47;shapes.push({color:i%2?'#000000':'#ffffff',d:`M${x} ${y} L${x+60} ${y} L${x+60} ${y+60} L${x} ${y+60} Z`});}
const groups=await partitionNative(shapes,512,512);const svg='<svg>'+[...groups].map(([c,paths])=>`<g fill="${c}"><path fill="${c}" d="${paths.join(' ')}"/></g>`).join('')+'</svg>';const audit=await auditNative(svg);if(audit.max_intersection_area_px2>.0001)throw Error('Partition overlaps');
console.log(JSON.stringify({ok:true,wasmCases:cases.length,tiledPartition:true,audit}));
