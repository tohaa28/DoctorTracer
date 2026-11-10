import fs from 'node:fs/promises';import {pdfBytes,epsText} from '../web/exports.mjs';
const svg='<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80" viewBox="10 20 200 160"><g fill="#ff0000"><path d="M10 20 L110 20 L110 180 L10 180 Z"/></g><g fill="#0000ff"><path d="M110 20 L210 20 L210 180 L110 180 Z"/></g></svg>';
const pdf=pdfBytes(svg),text=new TextDecoder().decode(pdf),eps=epsText(svg);
if(!text.includes('0.5 0 0 -0.5 -5 90 cm')||!text.includes('/BBox [10 20 210 180]'))throw Error('PDF viewBox transform');
if(!eps.includes('0 80 translate 0.5 -0.5 scale -10 -20 translate'))throw Error('EPS viewBox transform');
if((text.match(/\/Subtype \/Form/g)||[]).length!==2||text.includes('/Subtype /Image'))throw Error('Color groups/vector export');
await fs.mkdir('build/shared-boundary-fix',{recursive:true});await fs.writeFile('build/shared-boundary-fix/viewbox.pdf',pdf);
console.log('PASS: shared-viewBox PDF/EPS, vector color groups retained');
