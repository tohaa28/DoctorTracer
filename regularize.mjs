import{auditNative}from'./geometry.mjs?v=0.20.1';
export async function regularizeResult(runtime,svg,tolerance=.15,straight=true,curved=true,protect=true){
 let valid=false;for(const amount of [...Array.from({length:5},(_,i)=>tolerance/2**i),0]){
  try{const result=runtime.regularize(svg,amount,straight,curved,protect);valid=true;const geometry=await auditNative(result.svg);return{...result,applied_tolerance:amount,limited:amount!==tolerance,geometry};}catch{}
 }
 if(!valid)throw Error('Неподдерживаемая геометрия результата');
 return{svg,nodes_before:0,nodes_after:0,straightened:0,curves_fitted:0,limited:true,rejected:true};
}
