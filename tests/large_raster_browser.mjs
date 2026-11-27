import assert from 'node:assert/strict';
import {chromium} from 'playwright';
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
try{
 const page=await browser.newPage();
 await page.goto('http://127.0.0.1:8765/',{waitUntil:'networkidle'});
 const result=await page.evaluate(async()=>{
  const {decodeImage,decodedRasterDpi,validateInputFile}=await import('./input-image.mjs?v=0.21.8');
  validateInputFile({size:150_000_000});
  let rejected=false;try{validateInputFile({size:150_000_001});}catch{rejected=true;}
  const blob=await(await fetch('./native-fixture.tif')).blob();
  const bitmap=await decodeImage(new File([blob],'fixture.tif',{type:'image/tiff'}));
  const canvas=document.createElement('canvas');canvas.width=bitmap.width;canvas.height=bitmap.height;
  const ctx=canvas.getContext('2d');ctx.drawImage(bitmap,0,0);const rgba=ctx.getImageData(0,0,canvas.width,canvas.height);
  const p=(x,y)=>Array.from(rgba.data.slice(4*(y*canvas.width+x),4*(y*canvas.width+x)+4));
  const meta={width:bitmap.width,height:bitmap.height,dpi:decodedRasterDpi(bitmap),red:p(50,50),hole:p(300,300),rejected};
  bitmap.close();
  return meta;
 });
 assert.equal(result.width,5130);assert.equal(result.height,1685);assert.equal(result.dpi,300);
 assert.deepEqual(result.red,[255,0,0,255]);assert.equal(result.hole[3],0);assert.equal(result.rejected,true);
 console.log('PASS real Chromium TIFF decode, native 5130x1685 CMYK+Alpha, DPI, file limit',result);
}finally{await browser.close();}
