// SPDX-License-Identifier: GPL-2.0-or-later
import {icon} from './icons.js?v=0.19.0';
import {pdfBytes,svgGroups,epsText,connectedPaths} from './exports.mjs?v=0.19.0';
import {zip} from './zip.mjs?v=0.19.0';
import {opaqueCount,paletteKey,paintPalette,transparentSwatch,latestSelection} from './palette-ui.mjs?v=0.19.0';
import {partitionPreview} from './preview.mjs?v=0.19.0';
const $=id=>document.getElementById(id);
const hasTransparentSlot=()=>sourceHasAlpha&&!config.flatten;
const defaults=()=>({mode:'basic',category:'photo',detail:2,colors:0,speckle:2,flatten:false,polygon:false,gpu:true});
let config=defaults(),step=-1,source=null,sourceUrl='',vectorUrl='',outlineUrl='',svg='',worker=null,busy=false,name='image',elapsed=0,backend='',progress=0,stage='',loadToken=0;
const titles=['Режим Мастера','Тип Изображения','Прозрачность','Качество Ввода','Цветовой Режим','Обзор Результата','Экспорт Результата','Выбор Палитры'];titles[-1]='Загрузка Изображения';titles[8]='Редактирование Результата';titles[9]='Удаление Фона';
let editTool='pan',vectorUndo=[],vectorRedo=[];
let pageHistory=[],segmentUrl='',paletteWorker,requestId=0,pendingPalettes=new Map(),paletteCache=new Map(),palettePage=0,recommendedPaletteCount=9,sourceHasAlpha=false,view='bitmap',previewToken=0,panX=0,panY=0,exportDir=null;
function go(target){if(step!==target)pageHistory.push(step);step=target;show();}
function navImage(kind){return '<img alt="" src="'+new URL('./desktop-icons/nav-'+kind+'.png',import.meta.url).href+'">';}
function status(text){$('status').textContent=text;}
function card(title,description,symbol,selected,action){
 const b=document.createElement('button');b.className='card'+(selected?' selected':'');b.innerHTML='<span class="symbol">'+icon(symbol)+'</span><span class="text"><strong></strong><small></small><span class="choiceTag"></span></span>';
 b.querySelector('strong').textContent=title;b.querySelector('small').textContent=description;b.querySelector('.choiceTag').textContent=selected?'Выбор':'';b.onclick=action;return b;
}
function action(text,fn,selected=false){const b=document.createElement('button');b.className='action';const kind=text.includes('Качество')?(text.includes('Высокое')?'high':text.includes('Среднее')?'medium':'low'):text.includes('Цвета Без')?'flex':text.includes('Настраиваемые')?'fixed':null;if(kind){const image=document.createElement('img');image.className='small-icon';image.src=new URL('./desktop-icons/'+kind+'.png',import.meta.url);b.append(image,document.createTextNode(text.replace(/^[↻🌈◉]\s*/u,'')));}else b.textContent=text;b.setAttribute('aria-pressed',String(selected));b.onclick=fn;return b;}
function colorsForm(parent){
 const f=document.createElement('fieldset');f.innerHTML='<legend>Настройка палитры</legend><label class="formrow">Количество цветов <input id="colors" type="number" min="2" max="128" step="1" value="'+(config.colors||16)+'"></label><p class="hint">От 2 до 128 цветов. Палитра определяется по изображению.</p>';parent.append(f);
 $('colors').onchange=()=>readConfig();
}
function show(){
 $('stepTitle').textContent=titles[step];const p=$('page');p.replaceChildren();p.classList.toggle('review-page',step===5&&!busy);$('back').disabled=!busy&&pageHistory.length===0;$('home').disabled=busy;$('next').disabled=busy||!source||(step>=5&&!svg);$('next').innerHTML=navImage('next')+(step===6?'Сохранить':'Вперёд');$('home').innerHTML=navImage(step===-1?'reset':'home')+(step===-1?'Сброс':'В начало');$('back').innerHTML=navImage(busy?'cancel':'back')+(busy?'Отмена':'Назад');$('utility').hidden=step!==0&&step!==-1;
 const add=(title,desc,symbol,selected,fn)=>p.append(card(title,desc,symbol,selected,fn));const advance=()=>go(step+1);
 if(busy){p.innerHTML='<div class="processing"><img class="processing-icon" alt="" src="'+new URL('./desktop-icons/gears.png',import.meta.url).href+'"><strong id="processingStage"></strong><progress id="progress" max="100"></progress><p id="percent"></p><button id="cancel">Отмена</button></div>';$('cancel').onclick=cancel;updateProgress();return;}
 if(step===-1){
  add('Импорт из Папки','• Откройте изображение на компьютере.\n• Клавиши быстрого доступа: Ctrl-O.','folder',false,()=>$('file').click());
  add('Вставить из Буфера Обмена','• Изображение из буфера обмена будет показано слева.','clipboard',false,pasteImage);
  add('Пакетная Обработка','• Обработка нескольких изображений с одинаковыми параметрами.','batch',false,()=>batchInput.click());
  p.append(action('▶ Последние Папки',()=>status('Для открытия файла нажмите «Импорт из Папки».')),action('▶ Последние Изображения',()=>status('Файлы остаются на устройстве. Откройте нужное изображение.')));
 }else if(step===0){
  add('Автоматический','• Векторизация в один клик.','auto',config.mode==='auto',()=>{config.mode='auto';if(source)run();else show();});
  add('Базовый','• Простые вопросы с несколькими вариантами.\n• Пошаговый выбор параметров.','basic',config.mode==='basic',()=>{config.mode='basic';advance();});
  add('Расширенный','• Тонкие настройки управления.\n• Более сложные варианты.','advanced',config.mode==='advanced',()=>{config.mode='advanced';config.colors=config.colors||recommendedPaletteCount;go(7);});
  const hint=document.createElement('p');hint.className='hint';hint.textContent='Откройте изображение, затем выберите режим. Все вычисления выполняются на вашем устройстве.';p.append(hint);
 }else if(step===1){
  for(const [value,title,desc,symbol] of [['photo','Фотоснимок','• Захват с помощью фото- или веб-камеры.','photo'],['aa','Смешанные Края','• Сглаживание.\n• Наиболее распространённая категория.','aa'],['hard','Чистые Края','• Без сглаживания.\n• Чёткие пиксельные границы.','hard']])add(title,desc,symbol,config.category===value,()=>{config.category=value;config.colors=0;config.palette=null;go(sourceHasAlpha?2:3);});
 }else if(step===2){
  add('Оставить Прозрачность','• Подходит для изображений PNG.','alpha',!config.flatten,()=>{if(config.flatten)config.palette=null;config.flatten=false;advance();});
  add('Свести в Белый Цвет','• Если изображение было сглажено в белый цвет.','white',config.flatten,()=>{if(!config.flatten)config.palette=null;config.flatten=true;advance();});
 }else if(step===3){
  for(const [value,title,desc] of [[2,'Высокое Качество','• Большая резкость.\n• Очень мало артефактов сжатия и другого шума.'],[1,'Среднее Качество','• Небольшое ухудшение качества.\n• Небольшие артефакты сжатия и другой шум.'],[0,'Низкое Качество','• Размытость.\n• Много артефактов сжатия и другого шума.']])add(title,desc,['low','medium','high'][value],config.detail===value,()=>{config.detail=value;advance();});
 }else if(step===4){
  add('Два Цвета','• Использование только двух цветов.','two',config.colors===2,()=>{config.colors=2;config.palette=null;run();});
  add('Настраиваемые Цвета','• Выбор цветов на ваше усмотрение.\n• Используются только указанные вами цвета.','fixed',config.colors>2,()=>{config.colors=config.colors||recommendedPaletteCount;go(7);});
  add('Цвета Без Ограничений','• Используются имеющиеся цвета.\n• Подбор градиентов.','flex',config.colors===0,()=>{config.colors=0;config.palette=null;run();});
 }else if(step===7){
  buildPalettes(p);
 }else if(step===5){
  add('Рецензия Сделанного','• Кликните здесь для продолжения.\n• Далее можно сохранить результат.','review',true,()=>{go(6);});
  const f=document.createElement('fieldset');f.innerHTML='<legend>Улучшение Результата</legend><span class="sectionlabel">Уровень Детализации</span>';
  for(const [d,text] of [[2,'Высокое Качество'],[1,'Среднее Качество'],[0,'Низкое Качество']])f.append(action('↻ '+text,()=>{config.detail=d;run();},config.detail===d));
  const separator=document.createElement('hr');separator.className='hr';f.append(separator);const label=document.createElement('span');label.className='sectionlabel';label.textContent='Цвета';f.append(label);
  f.append(action('🌈 Цвета Без Ограничений',()=>{config.colors=0;config.palette=null;run();},config.colors===0),action('◉ Настраиваемые Цвета',()=>{config.colors=config.colors||recommendedPaletteCount;go(7);},config.colors>0));
  if(svg){const link=document.createElement('a');link.href='#';link.textContent='Текущая Палитра (изменить):';link.onclick=e=>{e.preventDefault();config.colors=config.colors||recommendedPaletteCount;go(7);};f.append(link);const palette=document.createElement('div');palette.className='palette';if(hasTransparentSlot())palette.append(transparentSwatch());for(const {color} of svgGroups(svg).slice(0,64)){const swatch=document.createElement('span');swatch.className='swatch';swatch.style.backgroundColor=color;swatch.title=color;palette.append(swatch);}f.append(palette);}
  const hr=document.createElement('hr');hr.className='hr';const advanced=document.createElement('span');advanced.className='sectionlabel';advanced.textContent='Расширенный';f.append(hr,advanced,action('✂ Удаление Фона',()=>{editTool='cut';go(9);}),action('✎ Редактирование Результата',()=>{editTool='pan';go(8);}),action('↶ Вернуться к Настройкам',()=>go(0)));p.append(f);
  postSmoothTools(p);
  const skip=document.createElement('label');skip.className='checkrow review-footer';const check=document.createElement('input');check.type='checkbox';check.checked=!!config.skipReview;check.onchange=()=>{config.skipReview=check.checked;};skip.append(check,document.createTextNode('Пропускать эту страницу в следующий раз'));p.append(skip);

 }else if(step===8||step===9){
  buildVectorEditor(p);
  postSmoothTools(p);
 }else{
  buildExport(p,add);
  postSmoothTools(p);

 }
}
function readConfig(){
 if(step!==7)return true;
 const count=Number($('colors').value),speckle=Number($('speckle').value);
 if(!Number.isInteger(count)||count<2||count>64||!Number.isInteger(speckle)||speckle<0||speckle>100){status('Цвета: 2–64; минимальное количество пикселей: 0–100.');return false;}
 if(count!==config.colors){config.colors=count;config.palette=null;}config.speckle=speckle;config.polygon=$('curve').value==='polygon';config.gpu=$('gpu').checked;return true;
}

function display(vector=false){
 const img=$('preview');img.src=vector&&vectorUrl?vectorUrl:sourceUrl;img.hidden=!source;img.style.width=source?Math.round(source.width*Number($('zoom').value)/100)+'px':'';
 $('zoomValue').textContent=$('zoom').value+'%';view=vector?'vector':'bitmap';$('bitmap').setAttribute('aria-pressed',String(!vector));$('vector').setAttribute('aria-pressed',String(vector));$('empty').hidden=!!source;
 if(vector&&svg&&$('outlines').checked){if(!outlineUrl){const doc=new DOMParser().parseFromString(svg,'image/svg+xml');for(const g of doc.querySelectorAll('g'))g.setAttribute('fill','none');for(const p of doc.querySelectorAll('path')){p.setAttribute('fill','none');p.setAttribute('stroke','#143d61');p.setAttribute('stroke-width','.5');}outlineUrl=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(doc)],{type:'image/svg+xml'}));}img.src=outlineUrl;}
 if(vector&&svg&&!$('outlines').checked&&svg.includes('data-shared-boundaries'))renderJointPreview();else{img.classList.remove('joint-preview');img.style.transform='translate('+panX+'px,'+panY+'px)';}
}
function fit(){if(!source)return;const v=$('viewport');panX=0;panY=0;$('zoom').value=Math.max(10,Math.min(800,Math.floor(100*Math.min((v.clientWidth-2)/source.width,(v.clientHeight-2)/source.height))));refreshView();}
function updateProgress(){if($('progress')){$('progress').value=progress;$('processingStage').textContent=stage;$('percent').textContent=progress+'%';}status(stage+' · '+progress+'%');}
async function run(){
 if(!source||busy||!readConfig())return;busy=true;if(step!==5){pageHistory.push(step);step=5;}svg='';progress=0;stage='Подготовка изображения';$('outlines').checked=false;$('vector').disabled=true;show();
 if(config.colors>0&&!config.palette?.length&&hasTransparentSlot()){try{const generation=loadToken,palette=await requestPalette(config.colors);if(generation!==loadToken||!busy)return;config.palette=palette;config.palette_generated=true;}catch(error){busy=false;step=pageHistory.pop()??4;show();status(error.message);return;}}
 const canvas=document.createElement('canvas');canvas.width=source.width;canvas.height=source.height;const context=canvas.getContext('2d',{willReadFrequently:true});
 if(config.flatten){context.fillStyle='#fff';context.fillRect(0,0,canvas.width,canvas.height);}context.drawImage(source,0,0);const pixels=context.getImageData(0,0,canvas.width,canvas.height).data;
 worker??=new Worker(new URL('./worker.js?v=0.19.0',import.meta.url),{type:'module'});
 worker.onmessage=({data})=>{
  if(data.progress!==undefined){progress=data.progress;stage=data.stage;updateProgress();return;}
  busy=false;if(data.error){worker?.terminate();worker=null;status(data.error);step=pageHistory.pop()??0;show();return;}svg=data.svg;vectorUndo=[];vectorRedo=[];elapsed=data.seconds;backend=data.backend;panX=0;panY=0;if(data.segments)awaitSegments(data.segments);$('segments').hidden=!data.segments;
  for(const url of [vectorUrl,outlineUrl])if(url)URL.revokeObjectURL(url);outlineUrl='';vectorUrl=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'}));$('vector').disabled=false;if(config.skipReview)step=6;display(true);show();status(source.width+'×'+source.height+' · '+(data.colors+Number(hasTransparentSlot()))+' цветов · '+data.paths+' кривых · '+elapsed.toFixed(2)+' с · '+backend);
 };
 worker.onerror=event=>{cancel();status('Ошибка WASM: '+event.message);};
 worker.postMessage({pixels:pixels.buffer,width:source.width,height:source.height,...config},[pixels.buffer]);
}
function cancel(){if(busy&&step===5)step=pageHistory.pop()??0;batchAbort?.();worker?.terminate();worker=null;busy=false;show();if(!svg){$('outlines').checked=false;display(false);}}
async function download(bytes,type,extension,filename){
 const blob=new Blob([bytes],{type});if(exportDir){const handle=await exportDir.getFileHandle(filename+'.'+extension,{create:true});const stream=await handle.createWritable();await stream.write(blob);await stream.close();return;}
 const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=filename+'.'+extension;a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);
}
async function save(){
 if(!svg)return;if(step!==6){go(6);return;}const filename=($('saveName').value.trim()||name).replace(/[<>:"/\\|?*]/g,'_'),format=$('format').value;
 try{if(format==='svg')await download(svg,'image/svg+xml','svg',filename);else if(format==='pdf')await download(pdfBytes(svg),'application/pdf','pdf',filename);else await download(epsText(svg),'application/postscript','eps',filename);status('Сохранено: '+filename+'.'+format);}catch(error){status('Ошибка сохранения: '+error.message);}
}

async function load(file){
 const token=++loadToken;cancel();status('Открытие изображения…');
 try{const original=await createImageBitmap(file);if(token!==loadToken){original.close();return;}const scale=Math.min(1,2400/Math.max(original.width,original.height),Math.sqrt(8e6/(original.width*original.height)));const width=Math.max(1,Math.round(original.width*scale)),height=Math.max(1,Math.round(original.height*scale));
  const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;canvas.getContext('2d').drawImage(original,0,0,width,height);original.close();const next=await createImageBitmap(canvas),blob=await new Promise(resolve=>canvas.toBlob(resolve));if(token!==loadToken){next.close();return;}
  source?.close();source=next;for(const url of [sourceUrl,vectorUrl,outlineUrl])if(url)URL.revokeObjectURL(url);vectorUrl='';outlineUrl='';sourceUrl=URL.createObjectURL(blob);const rgba=canvas.getContext('2d').getImageData(0,0,width,height).data;sourceHasAlpha=rgba.some((v,i)=>i%4===3&&v<255);paletteCache.clear();config.palette=null;name=(file.name||'image').replace(/\.[^.]+$/,'');svg='';$('outlines').checked=false;$('vector').disabled=true;config=defaults();pageHistory=[];step=0;display();busy=true;progress=0;stage='Анализ изображения';show();fit();const analysis=await analyzeSource();if(token!==loadToken)return;config.category=analysis?.category||'photo';recommendedPaletteCount=Math.max(2,Math.min(12,(analysis?.palette?.length||8)+Number(hasTransparentSlot())));busy=false;show();$('filename').textContent=file.name||'Пример';status(width+'×'+height+' · '+(file.name||'Пример')+(scale<1?' · уменьшено для обработки':''));
 }catch(error){busy=false;show();status('Не удалось открыть изображение: '+error.message);}
}
$('file').onchange=e=>{if(e.target.files[0])load(e.target.files[0]);e.target.value='';};
$('demo').onclick=async()=>{const blob=await (await fetch(new URL('./demo.png',import.meta.url))).blob();await load(new File([blob],'Пример.png',{type:'image/png'}));};
$('next').onclick=()=>{if(step===6)save();else if(step===5){go(6);}else if(config.mode==='auto'||step===7)run();else if(step===8||step===9){go(5);}else if(step===4){config.colors=0;run();}else go(step===1?(sourceHasAlpha?2:3):step+1);};
$('back').onclick=()=>{if(busy){cancel();status('Трассировка отменена');return;}if(readConfig()){step=pageHistory.pop()??(step===7?4:Math.max(0,step-1));show();}};$('home').onclick=()=>{pageHistory=[];step=source?0:-1;show();};
$('bitmap').onclick=()=>display(false);$('vector').onclick=()=>display(true);$('zoom').oninput=()=>refreshView();$('fit').onclick=fit;$('outlines').onchange=()=>{if(!svg)$('outlines').checked=false;display(!!svg);};
$('help').onclick=()=>$('helpDialog').showModal();$('closeHelp').onclick=()=>$('helpDialog').close();
$('viewport').ondragover=e=>e.preventDefault();$('viewport').ondrop=e=>{e.preventDefault();if(e.dataTransfer.files[0])load(e.dataTransfer.files[0]);};
window.addEventListener('resize',()=>{if(source)fit();});
// Avoid exporting a result for settings that have just been edited.
document.addEventListener('keydown',e=>{if(document.querySelector('#postSmoothDialog[open]')){if(e.ctrlKey&&['s','o'].includes(e.key.toLowerCase()))e.preventDefault();return;}if(e.ctrlKey&&e.key.toLowerCase()==='o'){e.preventDefault();$('file').click();return;}if(e.ctrlKey&&e.key.toLowerCase()==='s'){e.preventDefault();save();return;}if(/INPUT|SELECT|TEXTAREA/.test(e.target.tagName))return;if(step===8||step===9){if(e.key.toLowerCase()==='d'){editTool='cut';show();}if(e.key.toLowerCase()==='a'){editTool='pan';show();}if(e.key.toLowerCase()==='z'&&vectorUndo.length){vectorRedo.push(svg);applyVector(vectorUndo.pop(),false);}if(e.key.toLowerCase()==='y'&&vectorRedo.length){vectorUndo.push(svg);applyVector(vectorRedo.pop(),false);}}if(e.key.toLowerCase()==='b')display(false);if(e.key.toLowerCase()==='v'&&svg)display(true);if(e.key==='Escape'&&busy){cancel();status('Трассировка отменена');}});show();

async function renderJointPreview(){
 const token=++previewToken,v=$('viewport');try{const blob=await partitionPreview(svg,source.width,source.height,{viewWidth:Math.max(1,v.clientWidth),viewHeight:Math.max(1,v.clientHeight),zoom:Number($('zoom').value)/100,panX,panY});if(token!==previewToken||view!=='vector'||$('outlines').checked)return;const url=URL.createObjectURL(blob);const img=$('preview');img.classList.add('joint-preview');img.style.transform='none';img.src=url;setTimeout(()=>URL.revokeObjectURL(url),60000);}catch(error){status('Предпросмотр: '+error.message);}
}
async function awaitSegments(buffer){
 if(segmentUrl)URL.revokeObjectURL(segmentUrl);const c=document.createElement('canvas');c.width=source.width;c.height=source.height;c.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(buffer),c.width,c.height),0,0);segmentUrl=URL.createObjectURL(await new Promise(r=>c.toBlob(r)));
}
async function requestPalette(n){
 const generation=loadToken,flatten=config.flatten,transparent=hasTransparentSlot(),key=generation+':'+Number(flatten)+':'+n;
 if(paletteCache.has(key))return paletteCache.get(key);
 const canvas=document.createElement('canvas'),scale=Math.min(1,500/Math.max(source.width,source.height));canvas.width=Math.max(1,Math.round(source.width*scale));canvas.height=Math.max(1,Math.round(source.height*scale));const context=canvas.getContext('2d');if(flatten){context.fillStyle='#fff';context.fillRect(0,0,canvas.width,canvas.height);}context.drawImage(source,0,0,canvas.width,canvas.height);const pixels=context.getImageData(0,0,canvas.width,canvas.height).data;
 paletteService();const id=++requestId,promise=new Promise((resolve,reject)=>pendingPalettes.set(id,value=>Array.isArray(value)?resolve(value):reject(Error('Не удалось определить палитру'))));
 paletteCache.set(key,promise);paletteWorker.postMessage({operation:'palette',requestId:id,pixels:pixels.buffer,width:canvas.width,height:canvas.height,colors:opaqueCount(n,transparent)},[pixels.buffer]);
 try{return await promise;}catch(error){paletteCache.delete(key);throw error;}
}
function paletteSwatches(node,palette,editable=false){paintPalette(node,palette,{transparent:hasTransparentSlot(),editable,onChange:(i,rgb)=>{config.palette_generated=false;config.palette[i]=rgb;syncPaletteSelection();}});}
function syncPaletteSelection(){const key=config.palette?paletteKey(config.palette):'';for(const b of $('paletteList')?.querySelectorAll('button')||[])b.setAttribute('aria-pressed',String(b.dataset.paletteKey===key));}
function buildPalettes(parent){
 const page=++palettePage;const f=document.createElement('fieldset');f.innerHTML='<legend>Предлагаемые Палитры</legend><div id="paletteList" class="palette-list"><p class="hint">Определение цветов…</p></div>';parent.append(f);
 const edit=document.createElement('fieldset');edit.innerHTML='<legend>Выбор Палитры</legend><div id="editablePalette" class="palette"></div><label class="formrow">Количество Цветов: <input id="colors" type="number" min="2" max="64"></label><p class="hint">Выберите палитру сверху. Для изменения цвета нажмите на цветной образец.</p>';parent.append(edit);$('colors').value=config.colors||recommendedPaletteCount;
 const advanced=document.createElement('fieldset');advanced.innerHTML='<legend>Дополнительные Параметры</legend><label class="formrow">Минимальное Количество Пикселей: <input id="speckle" type="number" min="0" max="100"></label><label class="formrow">Построение <select id="curve"><option value="spline">Кривые Безье</option><option value="polygon">Прямые отрезки</option></select></label><label class="checkrow"><input id="gpu" type="checkbox">Использовать WebGPU, если доступен</label>';parent.append(advanced);$('speckle').value=config.speckle;$('curve').value=config.polygon?'polygon':'spline';$('gpu').checked=config.gpu;
 const choose=latestSelection();
 const selected=n=>{const generation=loadToken;const previous=config.colors;config.colors=n;$('next').disabled=true;
  choose(()=>requestPalette(n),palette=>{if(step!==7||page!==palettePage||generation!==loadToken)return;config.palette=palette.map(c=>[...c]);config.palette_generated=true;config.colors=Math.max(2,palette.length+Number(hasTransparentSlot()));paletteSwatches($('editablePalette'),config.palette,true);$('colors').value=config.colors;$('next').disabled=false;syncPaletteSelection();},error=>{if(step!==7||page!==palettePage)return;config.colors=previous;$('next').disabled=!config.palette?.length;status(error.message);});
 };
 if(config.palette?.length){config.colors=Math.max(2,config.palette.length+Number(hasTransparentSlot()));$('colors').value=config.colors;paletteSwatches($('editablePalette'),config.palette,true);$('next').disabled=false;}else selected(config.colors||recommendedPaletteCount);
 $('colors').oninput=$('colors').onchange=()=>{const n=Number($('colors').value);if(Number.isInteger(n)&&n>=2&&n<=64)selected(n);};
 (async()=>{const list=$('paletteList'),seen=new Set();list.replaceChildren();try{for(const n of [2,3,4,5,6,7,8,9,10,11,12]){const palette=await requestPalette(n);if(step!==7||page!==palettePage)return;const key=paletteKey(palette);if(seen.has(key))continue;seen.add(key);const b=document.createElement('button');b.className='palette-row';b.dataset.count=n;b.dataset.paletteKey=key;b.setAttribute('aria-label','Палитра: '+(palette.length+Number(hasTransparentSlot()))+' цветов');const arrow=document.createElement('span');arrow.className='palette-arrow';arrow.textContent=n===recommendedPaletteCount?'▶▶':'';const swatches=document.createElement('span');swatches.className='palette';paletteSwatches(swatches,palette);b.append(arrow,swatches);b.onclick=()=>selected(n);list.append(b);syncPaletteSelection();}}catch(error){if(step===7&&page===palettePage)status(error.message);}})();
}
function buildExport(parent,add){
 add('Сохранение Результата','• Совет: Попробуйте перетащить изображение в нужное вам место.\n• Клавиши быстрого доступа: Ctrl-S.','save',false,()=>save());
 const drag=document.createElement('fieldset');drag.innerHTML='<legend>Перетаскивание Файла</legend><div class="formrow"><div id="dragFile" class="drag-file" draggable="true">'+icon('save')+'</div><div><select id="dragFormat"><option>.pdf</option><option>.svg</option><option>.eps</option></select><p>Перетащите файл в нужную директорию.</p></div></div><label class="checkrow"><input type="checkbox" disabled title="Размер окна управляется браузером">Минимизировать окно</label>';parent.append(drag);$('dragFile').ondragstart=e=>{const ext=$('dragFormat').value.slice(1),type=ext==='pdf'?'application/pdf':ext==='eps'?'application/postscript':'image/svg+xml',bytes=ext==='pdf'?pdfBytes(svg):ext==='eps'?epsText(svg):svg;const url=URL.createObjectURL(new Blob([bytes],{type}));e.dataTransfer.setData('DownloadURL',type+':'+name+'.'+ext+':'+url);setTimeout(()=>URL.revokeObjectURL(url),60000);};
 const section=(title,html)=>{const button=document.createElement('button');button.className='export-toggle';button.textContent='▶ '+title;const body=document.createElement('div');body.className='export-body';body.hidden=true;body.innerHTML=html;button.onclick=()=>{body.hidden=!body.hidden;button.textContent=(body.hidden?'▶ ':'▼ ')+title;};parent.append(button,body);return body;};
 section('Быстрое Сохранение','<div class="row"><input id="folderName" aria-label="Папка экспорта" value="Папка загрузок браузера" readonly><button id="browseFolder">Обзор ▾</button></div><div class="row"><label for="saveName">Имя:</label><input id="saveName"><select id="format" aria-label="Формат"><option value="pdf">.pdf</option><option value="svg">.svg</option><option value="eps">.eps</option></select></div><button id="download">Сохранить</button>');$('saveName').value=name;$('download').onclick=()=>save();$('browseFolder').onclick=async()=>{if(!window.showDirectoryPicker){status('Браузер сохраняет файлы в выбранную папку загрузок.');return;}try{exportDir=await window.showDirectoryPicker({mode:'readwrite'});$('folderName').value=exportDir.name;}catch(error){if(error.name!=='AbortError')status(error.message);}};
 section('Экспорт Bitmap','<div class="row"><label>Имя:</label><input id="pngName"><select aria-label="Формат Bitmap"><option>.png</option></select></div><label class="formrow">Ширина: <input id="pngWidth" type="number" min="1" max="8192"></label><label class="formrow">Высота: <input id="pngHeight" type="number" min="1" max="8192"></label><div class="row">Масштаб: <button data-png-scale="1">x1</button><button data-png-scale="2">x2</button><button data-png-scale="4">x4</button></div><button id="pngSave">Сохранить</button>');$('pngName').value=name+'_vectorized';$('pngWidth').value=source.width;$('pngHeight').value=source.height;for(const b of parent.querySelectorAll('[data-png-scale]'))b.onclick=()=>{$('pngWidth').value=source.width*Number(b.dataset.pngScale);$('pngHeight').value=source.height*Number(b.dataset.pngScale);};$('pngSave').onclick=async()=>{const w=Number($('pngWidth').value),h=Number($('pngHeight').value);if(!Number.isInteger(w)||!Number.isInteger(h)||w<1||h<1||w>8192||h>8192||w*h>16000000){status('Размер PNG: не более 8192 px по стороне и 16 млн пикселей.');return;}const blob=await partitionPreview(svg,source.width,source.height,{viewWidth:w,viewHeight:h,zoom:w/source.width});await download(blob,'image/png','png',$('pngName').value||name);status('PNG сохранён');};
 section('Параметры Экспорта','<p>SVG / EPS / PDF: кривые Безье и составные контуры.<br>PNG: прозрачный фон, заданный размер.<br>AI, EMF и DXF в этой версии не поддерживаются.</p>');
 const settings=section('Сохранение Настроек','<button id="saveSettings">Сохранить Настройки...</button>');$('saveSettings').onclick=()=>download(JSON.stringify(config,null,2),'application/json','json','vector-settings');
}
async function pasteImage(){try{for(const item of await navigator.clipboard.read()){const type=item.types.find(t=>t.startsWith('image/'));if(type){const blob=await item.getType(type);await load(new File([blob],'clipboard.png',{type}));return;}}status('В буфере обмена нет изображения.');}catch(error){status('Вставка из буфера: '+error.message);}}
const batchInput=document.createElement('input');batchInput.type='file';batchInput.multiple=true;batchInput.accept='image/png,image/jpeg,image/webp,image/bmp';batchInput.hidden=true;document.body.append(batchInput);batchInput.onchange=()=>runBatch(Array.from(batchInput.files));
$('about').onclick=()=>$('helpDialog').showModal();$('more').onclick=()=>{$('computeGpu').checked=config.gpu;$('computeCpu').checked=!config.gpu;$('advancedSettings').disabled=!source;$('settingsDialog').showModal();};$('closeSettings').onclick=()=>$('settingsDialog').close();$('computeGpu').onchange=()=>{config.gpu=true;if($('gpu'))$('gpu').checked=true;};$('computeCpu').onchange=()=>{config.gpu=false;if($('gpu'))$('gpu').checked=false;};$('advancedSettings').onclick=()=>{$('settingsDialog').close();config.mode='advanced';config.colors=config.colors||recommendedPaletteCount;go(7);};
$('segments').onclick=()=>{if(!segmentUrl)return;view='segments';previewToken++;$('preview').classList.remove('joint-preview');$('preview').src=segmentUrl;$('preview').style.transform='translate('+panX+'px,'+panY+'px)';$('bitmap').setAttribute('aria-pressed','false');$('vector').setAttribute('aria-pressed','false');};
for(const b of document.querySelectorAll('[data-pan]'))b.onclick=()=>{if(b.dataset.pan==='fit'){fit();return;}const [x,y]=b.dataset.pan.split(',').map(Number);panX+=x;panY+=y;refreshView();};
let panStart;const viewport=$('viewport');viewport.onpointerdown=e=>{if(!source||e.target.closest('button'))return;if((step===8||step===9)&&editTool==='cut'){removeVectorAt(e.clientX,e.clientY);return;}panStart=[e.clientX,e.clientY,panX,panY];viewport.setPointerCapture(e.pointerId);};viewport.onpointermove=e=>{if(!panStart)return;panX=panStart[2]+e.clientX-panStart[0];panY=panStart[3]+e.clientY-panStart[1];refreshView();};viewport.onpointerup=()=>{panStart=null;};

let batchAbort=null;
async function runBatch(files){
 if(!files.length||busy)return;const options=structuredClone(config),result=[];busy=true;step=5;progress=0;stage='Пакетная Обработка';show();const batchWorker=new Worker(new URL('./worker.js?v=0.19.0',import.meta.url),{type:'module'});let aborted=false,rejectJob;
 batchAbort=()=>{aborted=true;batchWorker.terminate();rejectJob?.(Error('Трассировка отменена'));};
 try{for(const [index,file] of files.entries()){if(aborted)break;const image=await createImageBitmap(file),scale=Math.min(1,2400/Math.max(image.width,image.height));const c=document.createElement('canvas');c.width=Math.max(1,Math.round(image.width*scale));c.height=Math.max(1,Math.round(image.height*scale));const ctx=c.getContext('2d');if(options.flatten){ctx.fillStyle='#fff';ctx.fillRect(0,0,c.width,c.height);}ctx.drawImage(image,0,0,c.width,c.height);image.close();const pixels=ctx.getImageData(0,0,c.width,c.height).data;
 const traced=await new Promise((resolve,reject)=>{rejectJob=reject;batchWorker.onerror=e=>reject(Error(e.message));batchWorker.onmessage=({data})=>{if(data.progress!==undefined){progress=Math.floor((index+data.progress/100)/files.length*100);stage=(index+1)+' / '+files.length+' · '+data.stage;updateProgress();}else if(data.error)reject(Error(data.error));else resolve(data.svg);};batchWorker.postMessage({pixels:pixels.buffer,width:c.width,height:c.height,...options},[pixels.buffer]);});
 const base=String(index+1).padStart(3,'0')+'-'+file.name.replace(/\.[^.]+$/,'');result.push({name:base+'.svg',data:traced},{name:base+'.pdf',data:pdfBytes(traced)});}
 if(!aborted){await download(zip(result),'application/zip','zip','DoctorTracer-batch');status('Пакетная обработка завершена: '+files.length+' файлов');}
 }catch(error){status(error.message);}finally{batchWorker.terminate();batchAbort=null;busy=false;step=source?0:-1;show();}
}

function expandedDocument(){const doc=new DOMParser().parseFromString(svg,'image/svg+xml');for(const p of Array.from(doc.querySelectorAll('path'))){const pieces=connectedPaths(p.getAttribute('d'));if(pieces.length>1){for(const d of pieces){const copy=p.cloneNode(true);copy.setAttribute('d',d);p.before(copy);}p.remove();}}return doc;}
function applyVector(value,remember=true){if(remember){vectorUndo.push(svg);vectorUndo=vectorUndo.slice(-20);vectorRedo=[];}svg=value;if(vectorUrl)URL.revokeObjectURL(vectorUrl);if(outlineUrl)URL.revokeObjectURL(outlineUrl);outlineUrl='';vectorUrl=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'}));display(true);show();status('Результат обновлён');}
function removeVectorAt(clientX,clientY){
 const r=$('viewport').getBoundingClientRect(),zoom=Number($('zoom').value)/100;const x=(clientX-r.left-(r.width-source.width*zoom)/2-panX)/zoom,y=(clientY-r.top-(r.height-source.height*zoom)/2-panY)/zoom,doc=expandedDocument();const ctx=document.createElement('canvas').getContext('2d');for(const p of Array.from(doc.querySelectorAll('path')).reverse()){const t=/translate\(([-\d.eE]+)[, ]+([-\d.eE]+)\)/.exec(p.getAttribute('transform')||'');if(ctx.isPointInPath(new Path2D(p.getAttribute('d')),x-Number(t?.[1]??0),y-Number(t?.[2]??0),'nonzero')){p.remove();for(const g of Array.from(doc.querySelectorAll('g[fill]')))if(!g.querySelector('path'))g.remove();applyVector(new XMLSerializer().serializeToString(doc));return;}}
 status('В этой точке нет векторного объекта.');
}
function buildVectorEditor(parent){
 display(true);const tools=document.createElement('fieldset');tools.innerHTML='<legend>'+(step===9?'Инструмент Удаления Фона':'Инструменты')+'</legend><p class="hint">Выберите «Удаление» и нажмите на отдельную область изображения. Контур и принадлежащие ему отверстия удаляются вместе.</p>';tools.append(action('Перемещение (A)',()=>{editTool='pan';show();},editTool==='pan'),action('Удаление Области (D)',()=>{editTool='cut';show();},editTool==='cut'),action('Отменить (Z)',()=>{if(vectorUndo.length){vectorRedo.push(svg);applyVector(vectorUndo.pop(),false);}}),action('Повторить (Y)',()=>{if(vectorRedo.length){vectorUndo.push(svg);applyVector(vectorRedo.pop(),false);}}));parent.append(tools);
 if(step===8){const colors=document.createElement('fieldset');colors.innerHTML='<legend>Изменение Цветов</legend><p class="hint">Изменение образца заменяет этот цвет во всех соответствующих кривых.</p>';const palette=document.createElement('div');palette.className='palette';for(const group of svgGroups(svg).slice(0,128)){const input=document.createElement('input');input.type='color';input.value=group.color;input.className='swatch-input';input.title=group.color;input.onchange=()=>{const doc=new DOMParser().parseFromString(svg,'image/svg+xml');for(const g of doc.querySelectorAll('g[fill]'))if(g.getAttribute('fill').toLowerCase()===group.color.toLowerCase()){g.setAttribute('fill',input.value);g.setAttribute('id','color-'+input.value.slice(1));for(const p of g.querySelectorAll('path'))p.setAttribute('fill',input.value);}const combined=new Map();for(const g of doc.querySelectorAll('g[fill]')){const color=g.getAttribute('fill');if(combined.has(color)){for(const p of Array.from(g.children))combined.get(color).append(p);g.remove();}else combined.set(color,g);}applyVector(new XMLSerializer().serializeToString(doc));};palette.append(input);}colors.append(palette);parent.append(colors);}
 parent.append(action('Обзор Результата',()=>go(5)),action('Сохранить Результат',()=>go(6)));
}

function paletteService(){
 if(!paletteWorker){paletteWorker=new Worker(new URL('./worker.js?v=0.19.0',import.meta.url),{type:'module'});paletteWorker.onmessage=({data})=>{if(data.requestId!==undefined&&(data.palette||data.analysis||data.error)){const resolve=pendingPalettes.get(data.requestId);pendingPalettes.delete(data.requestId);resolve?.(data.palette||data.analysis||null);}};}return paletteWorker;
}
async function analyzeSource(){
 const c=document.createElement('canvas'),scale=Math.min(1,900/Math.max(source.width,source.height));c.width=Math.max(1,Math.round(source.width*scale));c.height=Math.max(1,Math.round(source.height*scale));const ctx=c.getContext('2d');ctx.drawImage(source,0,0,c.width,c.height);const pixels=ctx.getImageData(0,0,c.width,c.height).data,id=++requestId,promise=new Promise(resolve=>pendingPalettes.set(id,resolve));paletteService().postMessage({operation:'analyze',requestId:id,pixels:pixels.buffer,width:c.width,height:c.height},[pixels.buffer]);return promise;
}

function refreshView(){if(view==='segments'){$('segments').click();const zoom=Number($('zoom').value)/100;$('preview').style.width=source.width*zoom+'px';$('preview').style.height=source.height*zoom+'px';}else display(view==='vector');}

function postSmoothTools(parent){
 const box=document.createElement('fieldset');box.innerHTML='<legend>Готовый вектор</legend>';
 box.append(action('Сглаживание результата…',()=>openPostSmooth(false)));box.append(action('Очистка и упрощение…',()=>openPostSmooth(true)));
 const undo=action('Отменить изменение',()=>{if(vectorUndo.length){vectorRedo.push(svg);applyVector(vectorUndo.pop(),false);}});undo.disabled=!vectorUndo.length;box.append(undo);parent.append(box);
}
function openPostSmooth(cleanup=false){
 if(!svg||busy)return;const base=svg;let candidate=base,token=0,closed=false,timer;
 const dialog=document.createElement('dialog');dialog.id='postSmoothDialog';dialog.style.cssText='width:min(440px,85vw);padding:20px;border:1px solid #888;border-radius:5px;background:#eee;font:13px Arial';
 dialog.innerHTML='<h3>Сглаживание готового результата</h3><p>Дополнительная обработка готовых векторов. Общие границы цветов изменяются совместно.</p><label>Сила сглаживания: <output>35%</output><input id="postStrength" aria-label="Сила сглаживания" type="range" min="0" max="100" value="35" style="display:block;width:100%"></label><p><label><input id="postSharp" type="checkbox" checked> Сохранять острые углы</label></p><p><label><input id="postPreview" type="checkbox" checked> Предпросмотр на изображении</label></p><p id="postInfo" role="status">Подготовка…</p><div style="display:flex;gap:8px"><button id="postReset">Сброс</button><span style="flex:1"></span><button id="postApply" disabled>Применить</button><button id="postCancel">Отмена</button></div>';
 if(cleanup){dialog.querySelector('h3').textContent='Очистка и упрощение результата';dialog.querySelector('p').innerHTML='Удаление замкнутых мелких островков и отверстий. Детали на стыках цветов сохраняются.<br><label>Площадь до (пкс²): <input id="postArea" type="number" min="0" max="10000" step="0.25" value="4" style="width:90px"></label>';dialog.querySelector('#postStrength').value=25;dialog.querySelector('#postSharp').parentElement.lastChild.textContent=' Защищать углы и тонкие элементы';}
 document.body.append(dialog);const range=dialog.querySelector('#postStrength'),sharp=dialog.querySelector('#postSharp'),preview=dialog.querySelector('#postPreview'),info=dialog.querySelector('#postInfo'),apply=dialog.querySelector('#postApply');
 const area=dialog.querySelector('#postArea');if(cleanup){range.parentElement.firstChild.textContent='Допуск упрощения: ';range.setAttribute('aria-label','Допуск упрощения');}
 const service=new Worker(new URL('./worker.js?v=0.19.0',import.meta.url),{type:'module'});
 function paint(value){svg=value;if(vectorUrl)URL.revokeObjectURL(vectorUrl);if(outlineUrl)URL.revokeObjectURL(outlineUrl);outlineUrl='';vectorUrl=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'}));display(true);}
 function draw(){paint(preview.checked?candidate:base);}
 function schedule(){token++;apply.disabled=true;dialog.querySelector('output').textContent=cleanup?(Number(range.value)/100).toFixed(2)+' пкс':range.value+'%';info.textContent='Расчёт предпросмотра…';clearTimeout(timer);timer=setTimeout(()=>service.postMessage({operation:cleanup?'postClean':'postSmooth',svg:base,strength:Number(range.value),sharp:sharp.checked,minArea:area?Math.max(0,Math.min(10000,Number(area.value))):0,tolerance:Number(range.value)/100,protect:sharp.checked,requestId:token}),180);}
 service.onmessage=({data})=>{if(closed||data.requestId!==token)return;if(data.error){info.textContent='Не удалось обработать: '+data.error;return;}const result=cleanup?data.postClean:data.postSmooth;if(!result)return;candidate=result.svg;apply.disabled=candidate===base;info.textContent=candidate===base?'Результат не изменён. Попробуйте другую силу или отключите сохранение углов.':result.limited?'Сила уменьшена для защиты геометрии.':'Предпросмотр готов. Границы и мелкие детали защищены.';if(cleanup)info.textContent=`Удалено островков: ${result.removed_elements}; защищено: ${result.protected_elements}. Узлов: ${result.nodes_before} → ${result.nodes_after}.`+(result.limited?' Допуск уменьшен для защиты геометрии.':'');draw();};
 service.onerror=()=>{info.textContent='Не удалось загрузить модуль обработки.';};
 function finish(accepted){if(closed)return;closed=true;clearTimeout(timer);service.terminate();svg=base;if(accepted&&candidate!==base)applyVector(candidate);else{paint(base);status('Обработка отменена');}dialog.close();dialog.remove();}
 range.oninput=schedule;if(area)area.oninput=schedule;sharp.onchange=schedule;preview.onchange=draw;dialog.querySelector('#postReset').onclick=()=>{range.value=0;if(area)area.value=0;schedule();};apply.onclick=()=>finish(true);dialog.querySelector('#postCancel').onclick=()=>finish(false);dialog.oncancel=e=>{e.preventDefault();finish(false);};dialog.showModal();schedule();
}
