// SPDX-License-Identifier: MIT
// Transparency is a display slot, never an RGB ink passed to the tracing core.
export function opaqueCount(total,transparent){return Math.max(1,Number(total)-Number(transparent));}
export function paletteKey(palette){return palette.map(c=>c.join(',')).sort().join(';');}
export function transparentSwatch(){
 const s=document.createElement('span');s.className='swatch transparent-swatch';s.setAttribute('role','img');s.setAttribute('aria-label','Прозрачный цвет');s.title='Прозрачный цвет — фон сохраняется';return s;
}
export function paintPalette(node,palette,{transparent=false,editable=false,onChange=()=>{}}={}){
 node.replaceChildren();node.style.setProperty('--palette-count',String(palette.length+Number(transparent)));
 if(transparent)node.append(transparentSwatch());
 for(const [i,rgb] of palette.entries()){
  const hex='#'+rgb.map(v=>v.toString(16).padStart(2,'0')).join('');let s;
  if(editable){s=document.createElement('input');s.type='color';s.value=hex;s.className='swatch-input';s.setAttribute('aria-label','Цвет '+(i+1));s.dataset.paletteIndex=i;s.oninput=()=>{s.title=s.value;onChange(i,s.value.slice(1).match(/../g).map(v=>parseInt(v,16)));};}
  else{s=document.createElement('span');s.className='swatch';s.style.backgroundColor=hex;}
  s.title=hex;node.append(s);
 }
}
export function latestSelection(){let token=0;return async(load,apply,onError)=>{const id=++token;try{const value=await load();if(id===token)apply(value);}catch(error){if(id===token)onError(error);}};}
