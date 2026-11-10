const PDF_ASSETS = new URL('./vendor/pdfjs/', import.meta.url);
const TIFF_MODULE = new URL('./vendor/tiff.mjs?v=0.21.0', import.meta.url);
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
  const viewport = page.getViewport({scale: Math.min(3, 2400 / longest)});
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
