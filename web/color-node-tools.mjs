
import {auditNative} from './geometry.mjs';
import {regularizeResult} from './regularize.mjs';
// Slider controls tolerance, not a promise to remove a percentage of nodes.
export async function intermediateResult(runtime,svg,strength=35){
 const requested=Math.max(0,Math.min(100,Math.round(strength)));
 if(!requested)return{svg,removed_elements:0,protected_elements:0,nodes_before:0,nodes_after:0,applied_strength:0};
 for(const amount of [...new Set(Array.from({length:5},(_,i)=>Math.max(1,Math.round(requested/2**i))))]){
  try{const result=runtime.intermediate(svg,amount);if(result.removed_elements)result.svg=result.svg.replace(/<g\b[^>]*\bfill="#[0-9a-f]{6}"[^>]*>\s*<\/g>/gi,'');const geometry=await auditNative(result.svg);return{...result,geometry,applied_strength:amount,limited:amount!==requested};}catch{}
 }
 return{svg,removed_elements:0,protected_elements:0,nodes_before:0,nodes_after:0,applied_strength:0,limited:true,rejected:true};
}
export async function reduceNodesResult(runtime,svg,strength=35){
 const requested=Math.max(0,Math.min(100,Math.round(strength)));
 if(!requested)return{svg,nodes_before:0,nodes_after:0,reduction:0,applied_tolerance:0};
 const result=await regularizeResult(runtime,svg,requested/50,true,true,true);
 const before=result.nodes_before,after=result.nodes_after;
 if(!(before>after))return{...result,svg,nodes_after:before,reduction:0};
 return{...result,reduction:100*(before-after)/before};
}
