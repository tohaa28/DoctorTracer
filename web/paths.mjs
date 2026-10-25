// SPDX-License-Identifier: MIT
const SCALE=1e7;
export function contours(d,tx=0,ty=0){
 const tokens=d.match(/[MLCZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?/g)||[];let i=0,cmd='',path=[],current=[0,0],start=[0,0];const out=[];
 const add=p=>{const q={X:Math.round((p[0]+tx)*SCALE),Y:Math.round((p[1]+ty)*SCALE)};if(!path.length||path.at(-1).X!==q.X||path.at(-1).Y!==q.Y)path.push(q);current=p;};
 const cubic=(a,b,c,e,depth=0)=>{const delta=[e[0]-a[0],e[1]-a[1]],den=delta[0]**2+delta[1]**2;const distance=p=>den?((p[0]-a[0])*delta[1]-(p[1]-a[1])*delta[0])**2/den:(p[0]-a[0])**2+(p[1]-a[1])**2;
  if(depth>=14||Math.max(distance(b),distance(c))<=.000025){add(e);return;}const mid=(p,q)=>[(p[0]+q[0])/2,(p[1]+q[1])/2];const ab=mid(a,b),bc=mid(b,c),ce=mid(c,e),abc=mid(ab,bc),bce=mid(bc,ce),m=mid(abc,bce);cubic(a,ab,abc,m,depth+1);cubic(m,bce,ce,e,depth+1);
 };
 const close=()=>{if(path.length>=3)out.push(path);path=[];current=start;};
 while(i<tokens.length){if(/^[MLCZ]$/.test(tokens[i]))cmd=tokens[i++];if(cmd==='Z'){close();cmd='';continue;}if(cmd==='M'||cmd==='L'){const p=[Number(tokens[i++]),Number(tokens[i++])];if(cmd==='M'){if(path.length)close();start=p;cmd='L';}add(p);}else if(cmd==='C'){const b=[+tokens[i++],+tokens[i++]],c=[+tokens[i++],+tokens[i++]],e=[+tokens[i++],+tokens[i++]];cubic(current,b,c,e);}else throw Error('Unsupported path command');}
 if(path.length)close();return out;
}

export function normalizeWinding(data){
 const chunks=data.match(/M[^M]*/g)||[];const rings=chunks.map(d=>contours(d).flat()),areas=rings.map(r=>r.reduce((s,p,i)=>{const q=r[(i+1)%r.length];return s+p.X*q.Y-q.X*p.Y;},0));
 const inside=(ring,p)=>{let yes=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){const a=ring[i],b=ring[j];if((a.Y>p.Y)!==(b.Y>p.Y)&&p.X<(b.X-a.X)*(p.Y-a.Y)/(b.Y-a.Y)+a.X)yes=!yes;}return yes;};
 function reverse(chunk){const t=chunk.match(/[MLCZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?/g)||[];let i=0,cmd='',current=[0,0],segments=[];while(i<t.length){if(/^[MLCZ]$/.test(t[i]))cmd=t[i++];if(cmd==='Z'){cmd='';continue;}const n=cmd==='C'?6:2,p=t.slice(i,i+n).map(Number);i+=n;if(cmd==='M'){current=p;cmd='L';continue;}segments.push({start:current,verb:cmd,p});current=p.slice(-2);}let out='M'+current.join(' ')+' ';for(const s of segments.reverse())out+=(s.verb==='C'?'C'+[...s.p.slice(2,4),...s.p.slice(0,2),...s.start].join(' '):'L'+s.start.join(' '))+' ';return out+'Z';}
 return chunks.map((chunk,i)=>{const depth=rings.reduce((n,r,j)=>n+(j!==i&&Math.abs(areas[j])>Math.abs(areas[i])&&rings[i].some(p=>inside(r,p))?1:0),0);return(areas[i]>=0)===(depth%2===0)?chunk:reverse(chunk);}).join(' ');
}
