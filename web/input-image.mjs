const PDF_ASSETS = new URL('./vendor/pdfjs/', import.meta.url);
const TIFF_MODULE = new URL('./vendor/tiff.mjs', import.meta.url);
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

async function tiffBitmap(data) {
 const {default: tiff} = await import(TIFF_MODULE.href);
 const [frame] = tiff.decode(data);
 const width = frame?.t256?.[0], height = frame?.t257?.[0];
 if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1 ||
     width > 32767 || height > 32767 || width * height > 40000000) {
  throw Error('Некорректный размер TIFF или превышен предел 40 млн пикселей');
 }
 tiff.decodeImage(data, frame);
 if (!frame.data?.length) throw Error('Не удалось декодировать первую страницу TIFF');
 const pixels = tiff.toRGBA8(frame);
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
 if (!transform) return createImageBitmap(raw);
 const rotated = orientation >= 5;
 const output = canvas(rotated ? height : width, rotated ? width : height);
 const context = output.getContext('2d');
 context.setTransform(...transform);
 context.drawImage(raw, 0, 0);
 return createImageBitmap(output);
}

export function decodeImage(file) {
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

 // Match the shipped Rust valid(w,h) ABI exactly. Never downsample to fit.
export const NATIVE_RASTER_MAX_SIDE=4096;
export const NATIVE_RASTER_MAX_PIXELS=8000000;
export function nativeRasterSize(image){
 const {width,height}=image;
 if(!Number.isSafeInteger(width)||!Number.isSafeInteger(height)||width<1||height<1)
  throw Error('Некорректные размеры исходного растра.');
 if(width>NATIVE_RASTER_MAX_SIDE||height>NATIVE_RASTER_MAX_SIDE||width*height>NATIVE_RASTER_MAX_PIXELS)
  throw Error('Исходный растр '+width+'×'+height+' превышает предел текущего WASM: 4096 px по стороне и 8 млн пикселей. Автоматическое уменьшение запрещено.');
 return {width,height};
}
