import assert from 'node:assert/strict';
import {pngRasterDpi} from '../web/input-image.mjs';
const sample=ppm=>{
 const p=new Uint8Array(80),d=new DataView(p.buffer);
 d.setUint32(0,0x89504e47);d.setUint32(4,0x0d0a1a0a);d.setUint32(8,13);d.setUint32(12,0x49484452);
 d.setUint32(16,1200);d.setUint32(20,1200);d.setUint32(33,9);d.setUint32(37,0x70485973);
 d.setUint32(41,ppm);d.setUint32(45,ppm);p[49]=1;
 return new Blob([p],{type:'image/png'});
};
for(const dpi of [300,600,1200]){
 const ppm=Math.round(dpi/.0254);
 const detected=await pngRasterDpi(sample(ppm));
 assert.ok(Math.abs(detected-dpi)<.015,detected+' vs '+dpi);
}
assert.equal(await pngRasterDpi(new Blob([new Uint8Array(80)],{type:'image/png'})),null);
assert.equal(await pngRasterDpi(new Blob([new Uint8Array(80)],{type:'image/jpeg'})),null);
console.log('PASS native PNG pHYs 300/600/1200 dpi measured without pixel transformations');
