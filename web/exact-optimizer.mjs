// SPDX-License-Identifier: MIT
// Exact collinear test adapted from Relief Forge (MIT), commit 21094e94bde57f789421351442e908b0c473a6c6, web/curve-optimizer.js.
// Coordinates are proved on a decimal integer grid; no floating point geometric tolerance.
function exactInteger(s){
 const m=/^([+-]?)(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(s);
 if(!m||!(m[2]||m[3])||s.length>50)throw Error("unsupported coordinate");
 const e=Number(m[4]||0);if(!Number.isInteger(e)||Math.abs(e)>30)throw Error("unsupported exponent");
 let n=BigInt((m[2]+(m[3]||""))||"0"),shift=7+e-(m[3]||"").length;
 if(shift>=0)n*=10n**BigInt(shift);else{const d=10n**BigInt(-shift);if(n%d)throw Error("coordinate exceeds exact grid");n/=d;}
 if(n>100000000000000n)throw Error("coordinate limit");
 return m[1]==="-"?-n:n;
}

function decimal(n){const neg=n<0n;if(neg)n=-n;const s=n.toString().padStart(8,"0");const f=s.slice(-7).replace(/0+$/,"");return(neg?"-":"")+s.slice(0,-7)+(f?"."+f:"");}

function parseExact(d){
 const re=/[MLCZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?/g;
 const ts=[];let end=0;
 for(const m of d.matchAll(re)){if(!/^[\s,]*$/.test(d.slice(end,m.index)))throw Error("unsupported path syntax");ts.push(m[0]);end=m.index+m[0].length;}
 if(!/^[\s,]*$/.test(d.slice(end))||!ts.length)throw Error("unsupported path");
 const rings=[];let ring=null;let i=0;
 while(i<ts.length){const op=ts[i++],n={M:2,L:2,C:6,Z:0}[op];if(n===undefined||i+n>ts.length)throw Error("explicit commands required");
  const coords=ts.slice(i,i+n).map(exactInteger);i+=n;
  if(op==="M"){if(ring)throw Error("open path");ring=[{op,c:coords}];}
  else if(op==="Z"){if(!ring||ring.length<2)throw Error("empty path");rings.push(ring);ring=null;}
  else{if(!ring)throw Error("missing M");ring.push({op,c:coords});}
 }
 if(ring||!rings.length)throw Error("closed paths required");return rings;
}

function same(a,b){return a[0]===b[0]&&a[1]===b[1];}

function forward(a,b,c){const x=b[0]-a[0],y=b[1]-a[1],u=c[0]-b[0],v=c[1]-b[1];return x*v-y*u===0n&&x*u+y*v>0n;}

function endpoint(s){return s.c.slice(-2);}

function halfMerge(p,a,b){
 if(a.op!=="C"||b.op!=="C")return null;
 const q=a.c.slice(0,2),r=a.c.slice(2,4),m=endpoint(a),s=b.c.slice(0,2),t=b.c.slice(2,4),z=endpoint(b);
 const p1=q.map((v,i)=>2n*v-p[i]),p2=t.map((v,i)=>2n*v-z[i]);
 for(let i=0;i<2;i++)if(4n*r[i]!==p[i]+2n*p1[i]+p2[i]||4n*s[i]!==p1[i]+2n*p2[i]+z[i]||8n*m[i]!==p[i]+3n*p1[i]+3n*p2[i]+z[i])return null;
 if([...p1,...p2].some(v=>v>100000000000000n||v< -100000000000000n))return null;
 return{op:"C",c:[...p1,...p2,...z]};
}

function optimizeExactPath(d){
 let rings;try{rings=parseExact(d);}catch{return{d,before:0,after:0,zero:0,straight:0,cubic:0,skipped:1};}
 let before=0,after=0,zero=0,straight=0,cubic=0;const output=[];
 for(const ring of rings){
  before+=ring.length-1;const stack=[ring[0]];let z=0,l=0,c=0;
  for(const seg of ring.slice(1)){
   const p=endpoint(stack.at(-1));if(seg.c.every((v,i)=>v===p[i%2])){z++;continue;}
   stack.push(seg);
   while(stack.length>=3){
    const a=stack.at(-2),b=stack.at(-1),start=endpoint(stack.at(-3));
    if(a.op==="L"&&b.op==="L"&&forward(start,endpoint(a),endpoint(b))){stack.splice(-2,2,b);l++;continue;}
    const merged=halfMerge(start,a,b);if(merged){stack.splice(-2,2,merged);c++;continue;}break;
   }
  }
  // Do not erase a wholly degenerate ring; preserve its original commands.
  const kept=stack.length===1?ring:stack;if(stack.length>1){zero+=z;straight+=l;cubic+=c;}
  after+=kept.length-1;output.push(kept.map(s=>s.op+s.c.map(decimal).join(" ")).join(" ")+" Z");
 }
 return{d:before===after?d:output.join(" "),before,after,zero,straight,cubic,skipped:0};
}

function optimizeExactSvg(svg){
 // Only ordinary filled paths from DoctorTracer are eligible. Do not change stroke/marker semantics.
 if(/(?:\s(?:stroke(?:-[\w-]+)?|style|class|marker(?:-[\w-]+)?|clip-path|mask|filter|pathLength)\s*=|<(?:style|script|use|image|text|clipPath|mask|filter)\b)/i.test(svg))throw Error("Точная оптимизация поддерживает только обычные залитые контуры");
 const stats={before:0,after:0,zero:0,straight:0,cubic:0,skipped:0};
 const result=svg.replace(/<path\b[^>]*>/g,tag=>tag.replace(/(\s+d=")([^"]*)(")/,(_,a,d,b)=>{
  const r=optimizeExactPath(d);for(const k of Object.keys(stats))stats[k]+=r[k];return a+r.d+b;
 }));
 return{svg:result,...stats,removed:stats.before-stats.after};
}
export {optimizeExactPath,optimizeExactSvg};
