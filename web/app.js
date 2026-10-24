// SPDX-License-Identifier: GPL-2.0-or-later
const $=id=>document.getElementById(id);
const defaults=()=>({mode:'basic',category:'photo',detail:2,colors:32,speckle:2,flatten:false,polygon:false});
let config=defaults(),step=0,source=null,sourceUrl='',vectorUrl='',svg='',worker=null,busy=false,name='image',elapsed=0,outlineUrl='';
const titles=['Режим Мастера','Тип Изображения','Прозрачность','Качество Вывода','Цветовой Режим','Обзор Результата'];
function status(text){$('status').textContent=text;}
function card(title,description,symbol,selected,action){const b=document.createElement('button');b.className='card'+(selected?' selected':'');const icon=document.createElement('span');icon.className='symbol';icon.textContent=symbol;const text=document.createElement('span');const strong=document.createElement('strong');strong.textContent=title;const small=document.createElement('small');small.textContent=description;text.append(strong,small);b.append(icon,text);b.onclick=action;return b;}
function show(){
 $('stepTitle').textContent=titles[step];const p=$('page');p.replaceChildren();$('back').disabled=busy||step===0;$('home').disabled=busy;$('next').disabled=busy||!source||(step===5&&!svg);$('next').textContent=step===5?'Сохранить SVG':'Вперёд ▶';
 const add=(title,desc,symbol,selected,action)=>p.append(card(title,desc,symbol,selected,action));
 const advance=()=>{step++;show();};
 if(step===0){
  add('Автоматический','Векторизация с текущими параметрами.','●',config.mode==='auto',()=>{config.mode='auto';if(source)run();else show();});
  add('Базовый','Пошаговая настройка изображения.','▦',config.mode==='basic',()=>{config.mode='basic';advance();});
  add('Расширенный','Настройка цветов, кривых и мелких деталей.','☷',config.mode==='advanced',()=>{config.mode='advanced';step=4;show();});
  const hint=document.createElement('p');hint.className='hint';hint.textContent='WASM preview: 2–128 цветов, прозрачность, кривые Безье и SVG. Режим фотографий рабочего стола с неограниченными цветами пока не перенесён.';p.append(hint);
 }else if(step===1){
  for(const [value,title,desc,symbol] of [['photo','Фотоснимок','Много оттенков и плавные переходы.','▧'],['aa','Смешанные края','Иллюстрации со сглаживанием.','◩'],['hard','Чистые края','Изображения без сглаживания.','◼']])add(title,desc,symbol,config.category===value,()=>{config.category=value;advance();});
 }else if(step===2){
  add('Оставить Прозрачность','Сохранить прозрачные области PNG.','▨',!config.flatten,()=>{config.flatten=false;advance();});
  add('Свести в Белый Цвет','Заменить прозрачные области белым.','□',config.flatten,()=>{config.flatten=true;advance();});
 }else if(step===3){
  for(const [value,title,desc] of [[2,'Высокое Качество','Точные кривые и больше деталей.'],[1,'Среднее Качество','Баланс детализации и размера SVG.'],[0,'Низкое Качество','Более простые контуры.']])add(title,desc,'▥',config.detail===value,()=>{config.detail=value;config.speckle=[6,3,2][value];advance();});
 }else if(step===4){
  const f=document.createElement('div');f.className='form';
  f.innerHTML='<label>Количество цветов <input id="colors" type="number" min="2" max="128"></label><label>Мелкие области (пикс.) <input id="speckle" type="number" min="0" max="100"></label><label>Построение <select id="curve"><option value="spline">Кривые Безье</option><option value="polygon">Многоугольники</option></select></label><p class="hint">Все вычисления выполняет WASM-ядро. Для акварели попробуйте 64–128 цветов. Порог прозрачности — 128/255.</p>';p.append(f);
  $('colors').value=config.colors;$('speckle').value=config.speckle;$('curve').value=config.polygon?'polygon':'spline';
 }else{
  if(busy){const progress=document.createElement('progress');p.append(progress);const b=document.createElement('button');b.textContent='Отмена';b.onclick=cancel;p.append(b);return;}
  add('Рецензия Сделанного','Проверьте результат и сохраните SVG.','✓',true,save);
  const quality=document.createElement('fieldset');const legend=document.createElement('legend');legend.textContent='Уровень Детализации';quality.append(legend);
  for(const [d,text] of [[2,'Высокое Качество'],[1,'Среднее Качество'],[0,'Низкое Качество']]){const b=document.createElement('button');b.className='action';b.textContent='↻ '+text;b.setAttribute('aria-pressed',String(config.detail===d));b.onclick=()=>{config.detail=d;config.speckle=[6,3,2][d];run();};quality.append(b);}p.append(quality);
  const b=document.createElement('button');b.textContent='Вернуться к Настройкам';b.className='action';b.onclick=()=>{step=4;show();};p.append(b);
  const hint=document.createElement('p');hint.className='hint';hint.textContent=svg?`${elapsed.toFixed(2)} с • SVG ${(new Blob([svg]).size/1024).toFixed(1)} КБ`:'Результат ещё не построен.';p.append(hint);
 }
}
function readConfig(){if(step!==4)return true;const colors=Number($('colors').value),speckle=Number($('speckle').value);if(!Number.isInteger(colors)||colors<2||colors>128||!Number.isInteger(speckle)||speckle<0||speckle>100){status('Цвета: 2–128; мелкие области: 0–100 целых пикселей');return false;}config.colors=colors;config.speckle=speckle;config.polygon=$('curve').value==='polygon';return true;}
function display(vector=false){const img=$('preview');img.src=vector&&vectorUrl?vectorUrl:sourceUrl;img.hidden=!source;img.style.width=source?Math.round(source.width*Number($('zoom').value)/100)+'px':'';$('bitmap').setAttribute('aria-pressed',String(!vector));$('vector').setAttribute('aria-pressed',String(vector));$('empty').hidden=!!source;}
function fit(){if(!source)return;const viewport=$('viewport');$('zoom').value=Math.max(20,Math.min(100,Math.floor(100*Math.min((viewport.clientWidth-48)/source.width,(viewport.clientHeight-48)/source.height))));display($('vector').getAttribute('aria-pressed')==='true');}
async function run(){
 if(!source||busy)return;if(!readConfig())return;
 busy=true;step=5;svg='';$('outlines').checked=false;$('vector').disabled=true;show();status('Сегментация и построение кривых…');
 const canvas=document.createElement('canvas');canvas.width=source.width;canvas.height=source.height;const context=canvas.getContext('2d',{willReadFrequently:true});
 if(config.flatten){context.fillStyle='#fff';context.fillRect(0,0,canvas.width,canvas.height);}context.drawImage(source,0,0);const pixels=context.getImageData(0,0,canvas.width,canvas.height).data;
 worker??=new Worker('./worker.js',{type:'module'});
 worker.onmessage=({data})=>{busy=false;if(data.error){status(data.error);show();return;}svg=data.svg;elapsed=data.seconds;if(vectorUrl)URL.revokeObjectURL(vectorUrl);vectorUrl=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'}));$('vector').disabled=false;display(true);show();status(`${source.width}×${source.height} • ${data.paths} контуров • ${elapsed.toFixed(2)} с • WASM CPU`);};
 worker.onerror=event=>{cancel();status('Ошибка WASM: '+event.message);};
 worker.postMessage({pixels:pixels.buffer,width:source.width,height:source.height,...config},[pixels.buffer]);
}
function cancel(){worker?.terminate();worker=null;busy=false;if(!svg){$('outlines').checked=false;display(false);}show();status('Трассировка отменена');}
function save(){if(!svg)return;const a=document.createElement('a');a.href=vectorUrl;a.download=name+'.svg';a.click();}
$('file').onchange=async event=>{const file=event.target.files[0];if(!file)return;cancel();try{const original=await createImageBitmap(file);const scale=Math.min(1,2400/Math.max(original.width,original.height),Math.sqrt(8000000/(original.width*original.height)));const width=Math.max(1,Math.round(original.width*scale)),height=Math.max(1,Math.round(original.height*scale));const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;canvas.getContext('2d').drawImage(original,0,0,width,height);original.close();source?.close();source=await createImageBitmap(canvas);if(sourceUrl)URL.revokeObjectURL(sourceUrl);sourceUrl=URL.createObjectURL(await new Promise(resolve=>canvas.toBlob(resolve)));name=file.name.replace(/\.[^.]+$/,'');svg='';$('vector').disabled=true;step=0;display();show();fit();status(`${width}×${height} • ${file.name}${scale<1?' • уменьшено для обработки':''}`);}catch(error){status('Не удалось открыть изображение: '+error.message);}};
$('next').onclick=()=>{if(step===5)save();else if(config.mode==='auto'||step===4)run();else{step++;show();}};
$('back').onclick=()=>{if(readConfig()){step=Math.max(0,step-1);show();}};
$('home').onclick=()=>{step=0;show();};$('bitmap').onclick=()=>display(false);$('vector').onclick=()=>display(true);$('zoom').oninput=()=>display($('vector').getAttribute('aria-pressed')==='true');
$('outlines').onchange=()=>{if(!svg){$('outlines').checked=false;return;}if(outlineUrl)URL.revokeObjectURL(outlineUrl);if($('outlines').checked){const doc=new DOMParser().parseFromString(svg,'image/svg+xml');for(const p of doc.querySelectorAll('path')){p.setAttribute('fill','none');p.setAttribute('stroke','#173d64');p.setAttribute('stroke-width','.5');}outlineUrl=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(doc)],{type:'image/svg+xml'}));$('preview').src=outlineUrl;}else display(true);};
document.addEventListener('keydown',e=>{if(/INPUT|SELECT/.test(e.target.tagName))return;if(e.key.toLowerCase()==='b')display(false);if(e.key.toLowerCase()==='v'&&svg)display(true);if(e.key==='Escape'&&busy)cancel();});show();
