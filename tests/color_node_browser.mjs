import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {chromium} from 'playwright';
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
try{
 const fixtures=JSON.parse(await fs.readFile('tests/color_node_cases.json','utf8'));
 const svg=paths=>'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><g id="image">'+paths.map(([c,d])=>'<g fill="'+c+'"><path fill="'+c+'" d="'+d+'"/></g>').join('')+'</g></svg>';
 const page=await browser.newPage();await page.goto('http://127.0.0.1:8765/',{waitUntil:'networkidle'});
 const run=async(operation,source)=>page.evaluate(({operation,source})=>new Promise((resolve,reject)=>{
  const worker=new Worker('./worker.js?v=0.21.9',{type:'module'}),timer=setTimeout(()=>{worker.terminate();reject(Error('timeout'));},30000);
  worker.onerror=e=>{clearTimeout(timer);worker.terminate();reject(Error(e.message));};
  worker.onmessage=({data})=>{if(data.progress!==undefined)return;clearTimeout(timer);worker.terminate();data.error?reject(Error(data.error)):resolve(data[operation]);};
  worker.postMessage({operation,svg:source,strength:100,requestId:1});
 }),{operation,source});
 const a=await run('intermediate',svg(fixtures.strip));assert.equal(a.removed_elements,1);
 const fringes=JSON.parse(await fs.readFile('tests/fringe_cases.json','utf8'));
 const halo=await run('intermediate',svg(fringes.annulus));assert.equal(halo.removed_elements,1);
 const crescent=await run('intermediate',svg(fringes.crescent));assert.equal(crescent.removed_elements,1);
 const b=await run('reduceNodes',svg(fixtures.circle));assert.ok(b.nodes_after<b.nodes_before);
 console.log('PASS Chromium two independent postprocessing worker operations',a.removed_elements,b.nodes_before,b.nodes_after);
}finally{await browser.close();}
