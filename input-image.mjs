const PDF_ASSETS = new URL('./vendor/pdfjs/', import.meta.url);
const TIFF_MODULE = new URL('./vendor/tiff.mjs?v=0.21.8', import.meta.url);
export const acceptedImages = 'image/png,image/jpeg,image/webp,image/bmp,image/tiff,.tif,.tiff,application/pdf,.pdf';

function canvas(width, height) {
 const result = document.createElement('canvas');
 result.width = width;
 result.height = height;
 return result;
}

async function pdfBitmap(data) {
 const pdf = await import(new URL('pdf.min.mjs', PDF_ASSETS).href);
 pdf.GlobalWorkerOptions.workerSrc = new URL('pdf.worker.min.mjs', PDF_ASSETS).href;
 const task = pdf.getDocument({
  data, isEvalSupported: false, enableXfa: false,
  cMapUrl: new URL('cmaps/', PDF_ASSETS).href,
  standardFontDataUrl: new URL('standard_fonts/', PDF_ASSETS).href,
  wasmUrl: new URL('wasm/', PDF_ASSETS).href,
  iccUrl: new URL('iccs/', PDF_ASSETS).href,
 });
 try {
  const document = await task.promise;
  const page = await document.getPage(1);
  const natural = page.getViewport({scale: 1});
  const longest = Math.max(natural.width, natural.height);
  if (!Number.isFinite(longest) || longest <= 0) throw Error('Неверный размер страницы PDF');
  const viewport = page.getViewport({scale: 3});
  nativeRasterSize({width:Math.max(1,Math.round(viewport.width)),height:Math.max(1,Math.round(viewport.height))});
  const result = canvas(Math.max(1, Math.round(viewport.width)), Math.max(1, Math.round(viewport.height)));
  await page.render({canvas: result, viewport, background: 'rgba(0,0,0,0)'}).promise;
  return await createImageBitmap(result);
 } finally {
  await task.destroy();
 }
}

const bitmapDpi=new WeakMap();
export function decodedRasterDpi(bitmap){return bitmapDpi.get(bitmap)??null;}
async function tiffBitmap(data) {
 const {default: tiff} = await import(TIFF_MODULE.href);
 const [frame] = tiff.decode(data);
 const width = frame?.t256?.[0], height = frame?.t257?.[0];
 nativeRasterSize({width,height});
 tiff.decodeImage(data, frame);
 if (!frame.data?.length) throw Error('Не удалось декодировать первую страницу TIFF');
 let pixels;
 if(frame.t262?.[0]===5&&frame.t277?.[0]===5){
  if(frame.t284?.[0]!==1&&frame.t284?.[0]!==undefined||frame.t258?.length!==5||frame.t258.some(n=>n!==8)||frame.t338?.[0]!==2||frame.data.length!==width*height*5)
   throw Error('Поддерживается CMYK TIFF с пятью 8-битными каналами и независимой прозрачностью');
  pixels=new Uint8Array(width*height*4);
  for(let i=0,j=0;i<pixels.length;i+=4,j+=5){
   const black=255-frame.data[j+3];
   for(let c=0;c<3;c++)pixels[i+c]=Math.round((255-frame.data[j+c])*black/255);
   pixels[i+3]=frame.data[j+4];
  }
 }else pixels=tiff.toRGBA8(frame);
 if (frame.t338?.[0] === 1 && frame.t262?.[0] === 2 && frame.t277?.[0] === 4) {
  for (let i = 0; i < pixels.length; i += 4) {
   const alpha = pixels[i + 3];
   if (alpha > 0 && alpha < 255) {
    for (let channel = 0; channel < 3; channel++) {
     pixels[i + channel] = Math.min(255, Math.round(pixels[i + channel] * 255 / alpha));
    }
   }
  }
 }
 const raw = canvas(width, height);
 raw.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(pixels.buffer), width, height), 0, 0);

 // TIFF orientation maps storage coordinates to display coordinates.
 const orientation = frame.t274?.[0] ?? 1;
 const transforms = [
  null, null, [-1,0,0,1,width,0], [-1,0,0,-1,width,height], [1,0,0,-1,0,height],
  [0,1,1,0,0,0], [0,1,-1,0,height,0], [0,-1,-1,0,height,width], [0,-1,1,0,0,width],
 ];
 const transform = transforms[orientation];
 const unit=frame.t296?.[0]??2,rx=frame.t282?.[0],ry=frame.t283?.[0];
 const dpi=Number.isFinite(rx)&&rx===ry&&[2,3].includes(unit)?rx*(unit===3?2.54:1):null;
 const finish=async c=>{const bitmap=await createImageBitmap(c);if(dpi>0)bitmapDpi.set(bitmap,dpi);return bitmap;};
 if (!transform) return finish(raw);
 const rotated = orientation >= 5;
 const output = canvas(rotated ? height : width, rotated ? width : height);
 const context = output.getContext('2d');
 context.setTransform(...transform);
 context.drawImage(raw, 0, 0);
 return finish(output);
}

export const MAX_INPUT_BYTES=150_000_000;
export function validateInputFile(file){
 if(!Number.isSafeInteger(file?.size)||file.size<0)throw Error('Некорректный размер файла');
 if(file.size>MAX_INPUT_BYTES)throw Error('Файл превышает 150 МБ (150 000 000 байт).');
 return file;
}
export function decodeImage(file) {
 validateInputFile(file);
 if (file.type === 'application/pdf' || /\.pdf$/i.test(file.name)) {
  return file.arrayBuffer().then(data => pdfBitmap(new Uint8Array(data)));
 }
 if (file.type === 'image/tiff' || /\.tiff?$/i.test(file.name)) {
  return file.arrayBuffer().then(tiffBitmap);
 }
 return createImageBitmap(file);
}

// Crisp preview is enabled for the integrated wizard. Processing preserves
// native raster dimensions for both integrated and standalone input.
export function isCrispRasterHandoff(href,parentHref=null){
 const current=new URL(href);
 if(current.searchParams.get('raster')==='crisp')return true;
 if(!parentHref)return false;
 const parent=new URL(parentHref);
 return parent.origin===current.origin&&/^\/relief-forge(?:\/|$)/.test(parent.pathname);
}

export function drawInputRaster(context,image,width,height,{crisp=false,flatten=false}={}){
 if(image.width!==width||image.height!==height)throw Error('Изменение размеров исходного растра запрещено.');
 context.imageSmoothingEnabled=false;
 if(flatten){context.fillStyle='#fff';context.fillRect(0,0,width,height);}
 context.drawImage(image,0,0,width,height);
}

// Match actual WASM32 signed allocation/indexing limits, not arbitrary dimensions.
export function nativeRasterSize(image){
 const {width,height}=image;
 if(!Number.isSafeInteger(width)||!Number.isSafeInteger(height)||width<1||height<1)
  throw Error('Некорректные размеры исходного растра.');
 const rgba=width*height*4,grid=(width+1)*(height+1)*16;
 if(!Number.isSafeInteger(rgba)||!Number.isSafeInteger(grid)||rgba>0x7fffffff||grid>0x7fffffff||width>0x3fffffff||height>0x3fffffff)
  throw Error('Исходный растр '+width+'×'+height+' не помещается в адресное пространство текущего WASM32. Изображение не уменьшено; используйте Windows-версию.');
 return {width,height};
}


// PNG pHYs stores integer pixels/meter. This is read-only metadata: do
// not decode/re-encode the PNG, normalize alpha, or alter any source pixel.
export async function pngRasterDpi(file){
 if(!file||!(file.type==='image/png'||/\.png$/i.test(file.name||'')))return null;
 const bytes=new Uint8Array(await file.slice(0,4096).arrayBuffer());
 if(bytes.length<33)return null;
 const v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
 if(v.getUint32(0)!==0x89504e47||v.getUint32(4)!==0x0d0a1a0a)return null;
 for(let i=8;i+12<=bytes.length;){
  const len=v.getUint32(i),type=v.getUint32(i+4);
  if(i+12+len>bytes.length)break;
  if(type===0x70485973&&len===9&&bytes[i+16]===1){
   const x=v.getUint32(i+8),y=v.getUint32(i+12);
   if(x>0&&x===y){const dpi=x*.0254;return dpi>=36&&dpi<=9600?Math.round(dpi*1000)/1000:null;}
  }
  if(type===0x49444154)break;
  i+=12+len;
 }
 return null;
}
