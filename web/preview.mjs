// SPDX-License-Identifier: MIT
// Desktop ColorRenderer: joint supersampled partition coverage, no underpainting.
let cachedSVG='',cachedImage=null,latestSVG='';
const pendingImages=new Map();
async function decodedImage(svg){
 latestSVG=svg;
 if(cachedSVG===svg&&cachedImage)return cachedImage;
 let pending=pendingImages.get(svg);
 if(!pending){
  const image=new Image();
  const url=URL.createObjectURL(new Blob([svg.replace('<svg ','<svg shape-rendering="crispEdges" ')],{type:'image/svg+xml'}));
  image.src=url;
  pending=image.decode().then(()=>image).finally(()=>{URL.revokeObjectURL(url);pendingImages.delete(svg);});
  pendingImages.set(svg,pending);
 }
 const image=await pending;
 // An older decode must not replace the cache for the newest requested SVG.
 if(latestSVG===svg){cachedSVG=svg;cachedImage=image;}
 return image;
}
export async function partitionPreview(svg,width,height,{viewWidth=width,viewHeight=height,zoom=1,panX=0,panY=0,canvasOnly=false}={}){
 const image=await decodedImage(svg);
 const samples=viewWidth*viewHeight<=1500000?3:viewWidth*viewHeight<=3000000?2:1;
 const high=document.createElement('canvas');high.width=Math.max(1,viewWidth*samples);high.height=Math.max(1,viewHeight*samples);const p=high.getContext('2d');p.scale(samples,samples);p.imageSmoothingEnabled=false;p.drawImage(image,(viewWidth-width*zoom)/2+panX,(viewHeight-height*zoom)/2+panY,width*zoom,height*zoom);
 const out=document.createElement('canvas');out.width=viewWidth;out.height=viewHeight;const q=out.getContext('2d');q.imageSmoothingEnabled=true;q.imageSmoothingQuality='high';q.drawImage(high,0,0,viewWidth,viewHeight);return canvasOnly?out:new Promise(resolve=>out.toBlob(resolve));
}
