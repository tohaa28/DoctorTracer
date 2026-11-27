import assert from 'node:assert/strict';
import {chromium} from 'playwright';
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8765/',{waitUntil:'networkidle'});
 await page.waitForFunction(()=>window.doctorTracerInputContract==='native-raster-v1');
 assert.match(await page.locator('footer').innerText(),/0\.21\.7/);
 const output=await page.evaluate(()=>new Promise((resolve,reject)=>{
  const worker=new Worker('./worker.js?v=0.21.7',{type:'module'});
  const timer=setTimeout(()=>{worker.terminate();reject(Error('worker timeout'));},30000);
  worker.onerror=e=>{clearTimeout(timer);worker.terminate();reject(Error(e.message));};
  worker.onmessage=({data})=>{clearTimeout(timer);worker.terminate();data.error?reject(Error(data.error)):resolve(data.exactOptimize);};
  worker.postMessage({operation:'exactOptimize',requestId:1,svg:'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="400"><g fill="#ff0000"><path fill="#ff0000" d="M0 0 L0 0 L128 0 L256 0 L512 0 L512 400 L0 400 Z"/></g></svg>'});
 }));
 assert.equal(output.removed,3);assert.equal(output.straight,2);assert.equal(output.zero,1);
 assert.ok(output.geometry);assert.equal(output.geometry.max_intersection_area_px2,0);
 assert.deepEqual(errors,[]);console.log('PASS Chromium static app load, exact worker, native audit');
}finally{await browser.close();}
