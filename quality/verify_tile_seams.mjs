// Independent integer symmetric-difference check of old/new exported coverage.
import fs from 'node:fs/promises';
import Clipper from '../web/vendor/clipper.mjs';
import {svgGroups} from '../web/exports.mjs';
import {contours} from '../web/paths.mjs';
const root='build/quality-public-v2/runs/',rows=[];
for(const image of ['photo-astronaut','photo-chelsea','openmoji-butterfly']){
 const name=image+'--graphic-medium-9.svg';
 const before=svgGroups(await fs.readFile(root+'wasm-joint-release-016/'+name,'utf8'));
 const after=svgGroups(await fs.readFile(root+'wasm-seams-0161/'+name,'utf8'));
 let area=0;
 for(const group of before){
  const next=after.find(g=>g.color===group.color);if(!next)throw Error('Missing color '+JSON.stringify(group));
  const p=group.paths.flatMap(p=>contours(p.d,p.x,p.y)),q=next.paths.flatMap(p=>contours(p.d,p.x,p.y));
  const c=new Clipper.Clipper();c.AddPaths(p,Clipper.PolyType.ptSubject,true);c.AddPaths(q,Clipper.PolyType.ptClip,true);
  const out=[];c.Execute(Clipper.ClipType.ctXor,out,Clipper.PolyFillType.pftNonZero,Clipper.PolyFillType.pftNonZero);
  area+=Math.abs(out.reduce((s,p)=>s+Clipper.Clipper.Area(p),0))/1e14;
 }
 if(area>.0001)throw Error(image+' coverage differs '+area);
 rows.push({image,symmetric_difference_px2:area,paths_before:before.reduce((n,g)=>n+g.paths.length,0),paths_after:after.reduce((n,g)=>n+g.paths.length,0)});
}
await fs.writeFile('build/tile-seams/coverage.json',JSON.stringify(rows,null,2));console.log(JSON.stringify({ok:true,rows}));
