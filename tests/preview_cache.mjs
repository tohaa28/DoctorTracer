// Regression for rapid zoom/preview changes while SVG decoding is asynchronous.
// Runs in Node with a fake DOM; does not require Rust, GPU or a browser.
import assert from 'node:assert/strict';
import {partitionPreview} from '../web/preview.mjs';
const pending=[];
let created=0,revoked=0;
globalThis.URL.createObjectURL=()=>`blob:preview-${++created}`;
globalThis.URL.revokeObjectURL=()=>{revoked++;};
globalThis.Image=class {
 set src(value){this.url=value;}
 decode(){return new Promise((resolve,reject)=>pending.push({image:this,resolve,reject}));}
};
globalThis.document={createElement(kind){
 assert.equal(kind,'canvas');
 const canvas={width:0,height:0,drawn:[],getContext(){return {
  scale(){},drawImage(image){canvas.drawn.push(image);},
  set imageSmoothingEnabled(value){},set imageSmoothingQuality(value){}
 };},toBlob(resolve){resolve(new Blob(['test']));}};
 return canvas;
}};
const svgA='<svg data-id="a" />',svgB='<svg data-id="b" />';
const a1=partitionPreview(svgA,64,64,{canvasOnly:true});
const a2=partitionPreview(svgA,64,64,{canvasOnly:true});
assert.equal(pending.length,1,'same SVG must share one decode');
const b=partitionPreview(svgB,64,64,{canvasOnly:true});
assert.equal(pending.length,2,'different SVG must decode independently');
pending[1].resolve();
const bResult=await b;
assert.equal(bResult.drawn.length,1);
assert.equal(bResult.drawn[0].drawn[0],pending[1].image);
pending[0].resolve();
const [aResult,aResult2]=await Promise.all([a1,a2]);
assert.equal(aResult.drawn[0].drawn[0],pending[0].image);
assert.equal(aResult2.drawn[0].drawn[0],pending[0].image);
const bAgain=await partitionPreview(svgB,64,64,{canvasOnly:true});
assert.equal(pending.length,2,'stale A decode must not evict latest B cache');
assert.equal(bAgain.drawn[0].drawn[0],pending[1].image);
assert.equal(created,2);assert.equal(revoked,2);
const c=partitionPreview('<svg data-id="fail" />',64,64,{canvasOnly:true});
assert.equal(pending.length,3);
pending[2].reject(Error('decode failed'));
await assert.rejects(c,/decode failed/);
assert.equal(created,3);assert.equal(revoked,3);
const retry=partitionPreview('<svg data-id="fail" />',64,64,{canvasOnly:true});
assert.equal(pending.length,4,'failed decode must be retryable');
pending[3].resolve();await retry;
assert.equal(created,4);assert.equal(revoked,4);
console.log('PASS: shared decode, out-of-order cache, retry, URL cleanup');
