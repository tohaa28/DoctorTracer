// SPDX-License-Identifier: GPL-2.0-or-later
import {icon} from './icons.js';
import {pdfBytes,svgGroups} from './exports.mjs';
const $=id=>document.getElementById(id);
const defaults=()=>({mode:'basic',category:'photo',detail:1,colors:0,speckle:3,flatten:false,polygon:false,gpu:true});
let config=defaults(),step=0,source=null,sourceUrl='',vectorUrl='',outlineUrl='',svg='',worker=null,busy=false,name='image',elapsed=0,backend='',progress=0,stage='',loadToken=0;
const titles=['Режим Мастера','Тип Изображения','Прозрачность','Уровень Детализации','Цвета','Обзор Результата','Сохранение Результата'];
function status(text){$('status').textContent=text;}
function card(title,description,symbol,selected,action){
 const b=document.createElement('button');b.className='card'+(selected?' selected':'');b.innerHTML='<span class="symbol">'+icon(symbol)+'</span><span class="text"><strong></strong><small></small><span class="choiceTag"></span></span>';
 b.querySelector('strong').textContent=title;b.querySelector('small').textContent=description;b.querySelector('.choiceTag').textContent=selected?'Выбор':'';b.onclick=action;return b;
}
function action(text,fn,selected=false){const b=document.createElement('button');b.className='action';b.textContent=text;b.setAttribute('aria-pressed',String(selected));b.onclick=fn;return b;}
function colorsForm(parent){
 const f=document.createElement('fieldset');f.innerHTML='<legend>Настройка палитры</legend><label class="formrow">Количество цветов <input id="colors" type="number" min="2" max="128" step="1" value="'+(config.colors||16)+'"></label><p class="hint">От 2 до 128 цветов. Палитра определяется по изображению.</p>';parent.append(f);
 $('colors').onchange=()=>readConfig();
}
function show(){
 $('stepTitle').textContent=titles[step];const p=$('page');p.replaceChildren();$('back').disabled=busy||step===0;$('home').disabled=busy;$('next').disabled=busy||!source||(step>=5&&!svg);$('next').textContent=step===6?'Сохранить':step===5?'Вперёд ▶':'Вперёд ▶';
 const add=(title,desc,symbol,selected,fn)=>p.append(card(title,desc,symbol,selected,fn));const advance=()=>{step++;show();};
 if(busy){p.innerHTML='<div class="processing"><strong id="processingStage"></strong><progress id="progress" max="100"></progress><p id="percent"></p><button id="cancel">Отмена</button></div>';$('cancel').onclick=cancel;updateProgress();return;}
 if(step===0){
  add('Автоматический','Подобрать параметры и построить вектор.','auto',config.mode==='auto',()=>{config.mode='auto';if(source)run();else show();});
  add('Базовый','Ответьте на несколько вопросов об изображении.','basic',config.mode==='basic',()=>{config.mode='basic';advance();});
  add('Расширенный','Настройте цвета, кривые и мелкие детали.','advanced',config.mode==='advanced',()=>{config.mode='advanced';step=4;show();});
  const hint=document.createElement('p');hint.className='hint';hint.textContent='Откройте изображение, затем выберите режим. Все вычисления выполняются на вашем устройстве.';p.append(hint);
 }else if(step===1){
  for(const [value,title,desc,symbol] of [['photo','Фотоснимок','Фотографии, акварель, сложные переходы цветов.','photo'],['aa','Рисунок со Смешанными Краями','Логотипы и рисунки со сглаженными границами.','aa'],['hard','Рисунок с Чистыми Краями','Чёткие края без сглаживания.','hard']])add(title,desc,symbol,config.category===value,()=>{config.category=value;config.colors=value==='photo'?0:value==='aa'?16:8;advance();});
 }else if(step===2){
  add('Оставить Прозрачность','Сохранить прозрачные участки изображения.','alpha',!config.flatten,()=>{config.flatten=false;advance();});
  add('Свести в Белый Цвет','Заменить прозрачность белым фоном.','white',config.flatten,()=>{config.flatten=true;advance();});
 }else if(step===3){
  for(const [value,title,desc] of [[2,'Высокое Качество','Сохранить больше мелких деталей.'],[1,'Среднее Качество','Обычная детализация и гладкие кривые.'],[0,'Низкое Качество','Упростить изображение и удалить мелкие области.']])add(title,desc,'quality',config.detail===value,()=>{config.detail=value;config.speckle=[8,3,1][value];advance();});
 }else if(step===4){
  add('Цвета Без Ограничений','Автоматические цветовые области для фотографии.','palette',config.colors===0,()=>{config.colors=0;show();});
  add('Настраиваемые Цвета','Ограничить число цветов в результате.','palette',config.colors>0,()=>{config.colors=config.colors||16;show();});
  if(config.colors>0)colorsForm(p);
  const f=document.createElement('fieldset');f.innerHTML='<legend>Дополнительные Параметры</legend><label class="formrow">Мелкие области (пикс.) <input id="speckle" type="number" min="0" max="100" value="'+config.speckle+'"></label><label class="formrow">Построение <select id="curve"><option value="spline">Кривые Безье</option><option value="polygon">Многоугольники</option></select></label><label class="checkrow"><input id="gpu" type="checkbox">Использовать WebGPU, если доступен</label>';p.append(f);$('curve').value=config.polygon?'polygon':'spline';$('gpu').checked=config.gpu;
 }else if(step===5){
  add('Рецензия Сделанного','Нажмите здесь для продолжения. Далее можно сохранить результат.','review',true,()=>{step=6;show();});
  const f=document.createElement('fieldset');f.innerHTML='<legend>Улучшение Результата</legend><span class="sectionlabel">Уровень Детализации</span>';
  for(const [d,text] of [[2,'Высокое Качество'],[1,'Среднее Качество'],[0,'Низкое Качество']])f.append(action('↻ '+text,()=>{config.detail=d;config.speckle=[8,3,1][d];run();},config.detail===d));
  const label=document.createElement('span');label.className='sectionlabel';label.textContent='Цвета';f.append(label);
  f.append(action('🌈 Цвета Без Ограничений',()=>{config.colors=0;run();},config.colors===0),action('◉ Настраиваемые Цвета',()=>{config.colors=config.colors||16;step=4;show();},config.colors>0));
  if(svg){const palette=document.createElement('div');palette.className='palette';for(const {color} of svgGroups(svg).slice(0,64)){const swatch=document.createElement('span');swatch.className='swatch';swatch.style.backgroundColor=color;swatch.title=color;palette.append(swatch);}f.append(palette);}
  f.append(action('↶ Вернуться к Настройкам',()=>{step=4;show();}));p.append(f);
  const hint=document.createElement('p');hint.className='hint';hint.textContent=svg?elapsed.toFixed(2)+' с · '+(new Blob([svg]).size/1024).toFixed(1)+' КБ · '+backend:'';p.append(hint);
 }else{
  add('Сохранение Результата','Выберите формат и скачайте файл на компьютер.','save',true,()=>save());
  const f=document.createElement('fieldset');f.innerHTML='<legend>Файл</legend><label class="savefield">Имя файла<input id="saveName" maxlength="120"></label><label class="savefield">Формат<select id="format"><option value="svg">SVG — вектор с группами цветов</option><option value="pdf">PDF — группы для CorelDRAW</option><option value="png">PNG — растровое изображение</option></select></label><button id="download" class="download">Сохранить на компьютер</button><p class="hint">PDF: общая группа изображения → подгруппы по цветам → кривые. SVG сохраняет ту же структуру. PNG не содержит векторов.</p>';p.append(f);$('saveName').value=name;$('download').onclick=()=>save();
 }
}
function readConfig(){
 if(step!==4)return true;
 const c=$('colors')?Number($('colors').value):0,s=Number($('speckle').value);
 if(($('colors')&&(!Number.isInteger(c)||c<2||c>128))||!Number.isInteger(s)||s<0||s>100){status('Цвета: 2–128; мелкие области: 0–100 целых пикселей');return false;}
 config.colors=c;config.speckle=s;config.polygon=$('curve').value==='polygon';config.gpu=$('gpu').checked;return true;
}
function display(vector=false){
 const img=$('preview');img.src=vector&&vectorUrl?vectorUrl:sourceUrl;img.hidden=!source;img.style.width=source?Math.round(source.width*Number($('zoom').value)/100)+'px':'';
 $('zoomValue').textContent=$('zoom').value+'%';$('bitmap').setAttribute('aria-pressed',String(!vector));$('vector').setAttribute('aria-pressed',String(vector));$('empty').hidden=!!source;
 if(vector&&svg&&$('outlines').checked){if(!outlineUrl){const doc=new DOMParser().parseFromString(svg,'image/svg+xml');for(const g of doc.querySelectorAll('g'))g.setAttribute('fill','none');for(const p of doc.querySelectorAll('path')){p.setAttribute('fill','none');p.setAttribute('stroke','#143d61');p.setAttribute('stroke-width','.5');}outlineUrl=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(doc)],{type:'image/svg+xml'}));}img.src=outlineUrl;}
}
function fit(){if(!source)return;const v=$('viewport');$('zoom').value=Math.max(10,Math.min(100,Math.floor(100*Math.min((v.clientWidth-45)/source.width,(v.clientHeight-45)/source.height))));display($('vector').getAttribute('aria-pressed')==='true');}
function updateProgress(){if($('progress')){$('progress').value=progress;$('processingStage').textContent=stage;$('percent').textContent=progress+'%';}status(stage+' · '+progress+'%');}
async function run(){
 if(!source||busy||!readConfig())return;busy=true;step=5;svg='';progress=0;stage='Подготовка изображения';$('outlines').checked=false;$('vector').disabled=true;show();
 const canvas=document.createElement('canvas');canvas.width=source.width;canvas.height=source.height;const context=canvas.getContext('2d',{willReadFrequently:true});
 if(config.flatten){context.fillStyle='#fff';context.fillRect(0,0,canvas.width,canvas.height);}context.drawImage(source,0,0);const pixels=context.getImageData(0,0,canvas.width,canvas.height).data;
 worker??=new Worker(new URL('./worker.js',import.meta.url),{type:'module'});
 worker.onmessage=({data})=>{
  if(data.progress!==undefined){progress=data.progress;stage=data.stage;updateProgress();return;}
  busy=false;if(data.error){status(data.error);show();return;}svg=data.svg;elapsed=data.seconds;backend=data.backend;
  for(const url of [vectorUrl,outlineUrl])if(url)URL.revokeObjectURL(url);outlineUrl='';vectorUrl=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'}));$('vector').disabled=false;display(true);show();status(source.width+'×'+source.height+' · '+data.colors+' цветов · '+data.paths+' кривых · '+elapsed.toFixed(2)+' с · '+backend);
 };
 worker.onerror=event=>{cancel();status('Ошибка WASM: '+event.message);};
 worker.postMessage({pixels:pixels.buffer,width:source.width,height:source.height,...config},[pixels.buffer]);
}
function cancel(){worker?.terminate();worker=null;busy=false;show();if(!svg){$('outlines').checked=false;display(false);}}
function download(bytes,type,extension,filename){const url=URL.createObjectURL(new Blob([bytes],{type}));const a=document.createElement('a');a.href=url;a.download=filename+'.'+extension;a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);}
async function save(){
 if(!svg)return;if(step!==6){step=6;show();return;}
 const filename=($('saveName').value.trim()||name).replace(/[<>:"/\\|?*]/g,'_');const format=$('format').value;
 try{if(format==='svg')download(svg,'image/svg+xml','svg',filename);else if(format==='pdf')download(pdfBytes(svg),'application/pdf','pdf',filename);else{
  const img=new Image();img.src=vectorUrl;await img.decode();const canvas=document.createElement('canvas');canvas.width=source.width;canvas.height=source.height;canvas.getContext('2d').drawImage(img,0,0);const blob=await new Promise(resolve=>canvas.toBlob(resolve));download(blob,'image/png','png',filename);
 }status('Сохранено: '+filename+'.'+format);}catch(e){status('Ошибка сохранения: '+e.message);}
}
async function load(file){
 const token=++loadToken;cancel();status('Открытие изображения…');
 try{const original=await createImageBitmap(file);if(token!==loadToken){original.close();return;}const scale=Math.min(1,2400/Math.max(original.width,original.height),Math.sqrt(8e6/(original.width*original.height)));const width=Math.max(1,Math.round(original.width*scale)),height=Math.max(1,Math.round(original.height*scale));
  const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;canvas.getContext('2d').drawImage(original,0,0,width,height);original.close();const next=await createImageBitmap(canvas),blob=await new Promise(resolve=>canvas.toBlob(resolve));if(token!==loadToken){next.close();return;}
  source?.close();source=next;for(const url of [sourceUrl,vectorUrl,outlineUrl])if(url)URL.revokeObjectURL(url);vectorUrl='';outlineUrl='';sourceUrl=URL.createObjectURL(blob);name=(file.name||'image').replace(/\.[^.]+$/,'');svg='';$('outlines').checked=false;$('vector').disabled=true;config=defaults();step=0;display();show();fit();$('filename').textContent=file.name||'Пример';status(width+'×'+height+' · '+(file.name||'Пример')+(scale<1?' · уменьшено для обработки':''));
 }catch(error){status('Не удалось открыть изображение: '+error.message);}
}
$('file').onchange=e=>{if(e.target.files[0])load(e.target.files[0]);e.target.value='';};
$('demo').onclick=async()=>{const blob=await (await fetch(new URL('./demo.png',import.meta.url))).blob();await load(new File([blob],'Пример.png',{type:'image/png'}));};
$('next').onclick=()=>{if(step===6)save();else if(step===5){step=6;show();}else if(config.mode==='auto'||step===4)run();else{step++;show();}};
$('back').onclick=()=>{if(readConfig()){step=Math.max(0,step-1);show();}};$('home').onclick=()=>{step=0;show();};
$('bitmap').onclick=()=>display(false);$('vector').onclick=()=>display(true);$('zoom').oninput=()=>display($('vector').getAttribute('aria-pressed')==='true');$('fit').onclick=fit;$('outlines').onchange=()=>{if(!svg)$('outlines').checked=false;display(!!svg);};
$('help').onclick=()=>$('helpDialog').showModal();$('closeHelp').onclick=()=>$('helpDialog').close();
$('viewport').ondragover=e=>e.preventDefault();$('viewport').ondrop=e=>{e.preventDefault();if(e.dataTransfer.files[0])load(e.dataTransfer.files[0]);};
window.addEventListener('resize',()=>{if(source)fit();});
// Avoid exporting a result for settings that have just been edited.
document.addEventListener('keydown',e=>{if(/INPUT|SELECT|TEXTAREA/.test(e.target.tagName))return;if(e.key.toLowerCase()==='b')display(false);if(e.key.toLowerCase()==='v'&&svg)display(true);if(e.key==='Escape'&&busy){cancel();status('Трассировка отменена');}});show();
