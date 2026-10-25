"""Desktop vs Rust WASM stage/geometry gates. User images stay under ignored build/.
python tests/desktop_parity.py --image path.png [--image second.jpg]
"""
import sys,json,argparse,subprocess,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import QByteArray,QRectF,Qt
from vector_render import QSvgRenderer
from engine import load_source,find_palette,segment
import gpu_filter,gpu_meanshift,spatial_palette,accelerator,shared_regions,photo_regions
from vector_partition import audit_pieces
import xml.etree.ElementTree as ET
parser=argparse.ArgumentParser();parser.add_argument('--image',action='append',default=[]);parser.add_argument('--details',default='0,1,2');args=parser.parse_args();app=QApplication([])
out=ROOT/'build/parity';out.mkdir(parents=True,exist_ok=True);cases=[]
images=[]
rng=np.random.default_rng(27)
for i,(w,h) in enumerate([(1,1),(19,17),(32,24)]):
 a=rng.integers(0,256,(h,w,4),dtype=np.uint8);a[:,:,3]=np.where(a[:,:,3]>=96,255,0);images.append((f'synthetic-{i}',a))
a=np.zeros((48,64,4),np.uint8);a[3:45,3:32]=[210,30,80,255];a[3:45,32:61]=[20,160,210,255];a[12,12]=0;images.append(('alpha-hole',a))
for i,path in enumerate(args.image):images.append((f'private-{i}',np.array(Image.open(path).convert('RGBA'))))
for name,a in images:
 h,w=a.shape[:2];path=out/(name+'.png');Image.fromarray(a).save(path);(out/(name+'.rgba')).write_bytes(a.tobytes())
 for detail in map(int,args.details.split(',')):
  prefix=name+'-'+str(detail);print('Reference',prefix,flush=True);t=time.perf_counter();bil=gpu_filter.cpu(a);mode=gpu_meanshift.native_cpu(bil,*[(7,30),(5,20),(3,15)][detail],5)
  (out/(prefix+'-bil.bin')).write_bytes(bil.tobytes());(out/(prefix+'-mode.bin')).write_bytes(mode.tobytes());pal=find_palette(mode,64,True)
  cfg={'category':'photo','photo_regions':True,'colors':0,'compute':'cpu','detail':detail,'speckle':2,'artifact_strength':2,'segmentation_complexity':5,'curve_tolerance':.12*[4,2,1][detail],'alphamax':1.}
  # Same source array/explicit palette isolates assignment/cleanup from palette fitting.
  prepared={'category':'photo','photo_spatial':True,'palette':['#%02x%02x%02x'%tuple(c) for c in pal],'compute':'cpu','spatial_strength':200,'spatial_iterations':2,'speckle':2,'artifact_strength':2,'segmentation_complexity':5,'_source':(mode,(w,h))}
  _,labels,_,_=segment(path,prepared);(out/(prefix+'-labels.bin')).write_bytes(labels.tobytes())
  ref,stats=photo_regions.trace(path,cfg);(out/(prefix+'-reference.svg')).write_text(ref,encoding='utf8')
  cases.append({'id':prefix,'source':name+'.rgba','w':w,'h':h,'detail':detail,'palette':pal,'initial_regions':stats.get('initial_regions',0),'region_target':stats.get('region_target',0),'smoothing_fallback':stats.get('smoothing_fallback',False),'reference_seconds':time.perf_counter()-t})
manifest=out/'manifest.json';manifest.write_text(json.dumps(cases),encoding='utf8')
subprocess.run(['node',str(ROOT/'tests/desktop_parity.mjs'),str(manifest)],cwd=ROOT,check=True)
def render(svg,w,h):
 renderer=QSvgRenderer(QByteArray(svg.encode()));im=QImage(w,h,QImage.Format_RGBA8888);im.fill(Qt.transparent);p=QPainter(im);renderer.render(p,QRectF(0,0,w,h));p.end();return np.frombuffer(im.bits(),np.uint8).reshape(h,w,4).copy()
results=json.loads((out/'rust-results.json').read_text(encoding='utf8'));fail=[]
for case,stats in zip(cases,results):
 prefix=case['id'];ref=(out/(prefix+'-reference.svg')).read_text(encoding='utf8');svg=(out/(prefix+'-rust.svg')).read_text(encoding='utf8');a=render(ref,case['w'],case['h']);b=render(svg,case['w'],case['h']);error=float(np.abs(a.astype(float)-b.astype(float)).mean());stats['rgba_mae']=error
 doc=ET.fromstring(svg);audit={};audit_pieces([(p.get('fill'),p.get('d')) for p in doc.iter('{http://www.w3.org/2000/svg}path')],audit);stats['desktop_geometry_audit']=audit
 if error>.02:fail.append(prefix+' RGBA MAE '+str(error))
 print(prefix,'RGBA MAE',error,'audit',audit['max_intersection_area_px2'],flush=True)
(out/'report.json').write_text(json.dumps(results,indent=2),encoding='utf8')
if fail:raise AssertionError('\n'.join(fail))
print('PASS: desktop/Rust stage equality, final raster and independent desktop overlap audit')
