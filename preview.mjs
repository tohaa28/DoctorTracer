// SPDX-License-Identifier: MIT
// Desktop ColorRenderer: joint supersampled partition coverage, no underpainting.
let cachedSVG='',cachedImage;
export async function partitionPreview(svg,width,height,{viewWidth=width,viewHeight=height,zoom=1,panX=0,panY=0,canvasOnly=false}={}){
 if(cachedSVG!==svg){const image=new Image();const url=URL.createObjectURL(new Blob([svg.replace('<svg ','<svg shape-rendering="crispEdges" ')],{type:'image/svg+xml'}));image.src=url;try{await image.decode();}finally{URL.revokeObjectURL(url);}cachedSVG=svg;cachedImage=image;}
 const samples=viewWidth*viewHeight<=1500000?3:viewWidth*viewHeight<=3000000?2:1;
 const high=document.createElement('canvas');high.width=Math.max(1,viewWidth*samples);high.height=Math.max(1,viewHeight*samples);const p=high.getContext('2d');p.scale(samples,samples);p.imageSmoothingEnabled=false;p.drawImage(cachedImage,(viewWidth-width*zoom)/2+panX,(viewHeight-height*zoom)/2+panY,width*zoom,height*zoom);
 const out=document.createElement('canvas');out.width=viewWidth;out.height=viewHeight;const q=out.getContext('2d');q.imageSmoothingEnabled=true;q.imageSmoothingQuality='high';q.drawImage(high,0,0,viewWidth,viewHeight);return canvasOnly?out:new Promise(resolve=>out.toBlob(resolve));
}
