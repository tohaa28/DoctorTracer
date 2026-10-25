// SPDX-License-Identifier: MIT
const encoder=new TextEncoder();
export function svgGroups(svg){
 const groups=[];
 for(const match of svg.matchAll(/<g\b[^>]*\bfill="(#[0-9a-f]{6})"[^>]*>([\s\S]*?)<\/g>/gi)){
  const paths=[];for(const p of match[2].matchAll(/<path\b([^>]*)\/?>/g)){
   const d=/\bd="([^"]*)"/.exec(p[1])?.[1];const t=/translate\(([-\d.eE]+)[, ]+([-\d.eE]+)\)/.exec(p[1]);
   if(d)paths.push({d,x:Number(t?.[1]??0),y:Number(t?.[2]??0)});
  }groups.push({color:match[1].toLowerCase(),paths});
 }return groups;
}
export function pdfBytes(svg){
 const w=Number(/\bwidth="([\d.]+)"/.exec(svg)?.[1]),h=Number(/\bheight="([\d.]+)"/.exec(svg)?.[1]);
 if(!(w>0&&h>0))throw Error('Некорректный SVG');
 const objects=['',''],refs=[],page=[];
 const stream=(data,attrs='')=>`<< ${attrs} /Length ${encoder.encode(data).length} >>\nstream\n${data}\nendstream`;
 for(const [index,group] of svgGroups(svg).entries()){
  const parts=[group.color.slice(1).match(/../g).map(v=>parseInt(v,16)/255).join(' ')+' rg'];
  for(const {d,x,y} of group.paths){
   parts.push(`q 1 0 0 1 ${x} ${y} cm`);
   const tokens=d.match(/[MLCZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?/g)||[];
   let i=0,cmd='';while(i<tokens.length){if(/^[MLCZ]$/.test(tokens[i]))cmd=tokens[i++];if(cmd==='Z'){parts.push('h');cmd='';continue;}
    const n={M:2,L:2,C:6}[cmd];if(!n)throw Error('Неподдерживаемая команда SVG');parts.push(tokens.slice(i,i+n).join(' ')+' '+{M:'m',L:'l',C:'c'}[cmd]);i+=n;if(cmd==='M')cmd='L';
   }parts.push('f','Q');
  }
  objects.push(stream(parts.join('\n'),`/Type /XObject /Subtype /Form /FormType 1 /Group << /S /Transparency /CS /DeviceRGB /I true /K false >> /BBox [0 0 ${w} ${h}] /Resources << >>`));
  refs.push(`/Color${index} ${objects.length} 0 R`);page.push(`/Color${index} Do`);
 }
 objects.push(stream(`q\n1 0 0 -1 0 ${h} cm\n${page.join('\n')}\nQ`));const content=objects.length;
 objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${w} ${h}] /Resources << /XObject << ${refs.join(' ')} >> >> /Contents ${content} 0 R >>`);
 objects[0]='<< /Type /Catalog /Pages 2 0 R >>';objects[1]=`<< /Type /Pages /Kids [${objects.length} 0 R] /Count 1 >>`;
 let output='%PDF-1.4\n%DoctorTracer Rust\n';const offsets=[0];for(const [i,obj] of objects.entries()){offsets.push(output.length);output+=`${i+1} 0 obj\n${obj}\nendobj\n`;}
 const start=output.length;output+=`xref\n0 ${offsets.length}\n0000000000 65535 f \n`;
 for(const offset of offsets.slice(1))output+=String(offset).padStart(10,'0')+' 00000 n \n';
 output+=`trailer\n<< /Size ${offsets.length} /Root 1 0 R >>\nstartxref\n${start}\n%%EOF\n`;return encoder.encode(output);
}
