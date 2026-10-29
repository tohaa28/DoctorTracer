import{auditNative}from'./geometry.mjs?v=0.20.0';
export async function cleanResult(runtime,svg,minArea=4,tolerance=.25,protect=true){
 for(const amount of [...Array.from({length:5},(_,i)=>tolerance/2**i),0]){
  const result=runtime.postClean(svg,minArea,amount,protect);
  try{const geometry=await auditNative(result.svg);return{...result,applied_tolerance:amount,limited:amount!==tolerance,geometry};}catch{}
 }
 return{svg,nodes_before:0,nodes_after:0,removed_elements:0,protected_elements:0,limited:true,rejected:true};
}
