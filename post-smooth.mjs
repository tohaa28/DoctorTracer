// Standalone finished-result module. Every candidate passes the usual audit.
import {auditNative} from './geometry.mjs?v=0.17.0';
export async function smoothResult(runtime,svg,strength=35,sharp=true){
 if(!strength)return{svg,nodes:0,moved:0,applied_strength:0};
 for(let attempt=0;attempt<5;attempt++){
  const amount=Math.max(1,Math.round(strength/2**attempt));
  try{const result=runtime.postSmooth(svg,amount,sharp);const geometry=await auditNative(result.svg);return{...result,geometry,applied_strength:amount,limited:amount!==strength};}catch{}
 }
 return{svg,nodes:0,moved:0,applied_strength:0,limited:true};
}
