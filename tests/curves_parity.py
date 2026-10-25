"""End-to-end limited-palette desktop/Potrace/Skia browser parity gates."""
import sys,json,subprocess,argparse
from pathlib import Path
import numpy as np,cv2
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from engine import trace
from vector_render import QSvgRenderer
from vector_partition import audit_pieces
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import QByteArray,Qt
import xml.etree.ElementTree as ET
parser=argparse.ArgumentParser();parser.add_argument('--image',action='append',default=[]);parser.add_argument('--reuse',action='store_true');args=parser.parse_args();app=QApplication([]);out=ROOT/'build/curves-parity';out.mkdir(parents=True,exist_ok=True);cases=[]
if not args.reuse:
 for transparent in [False,True]:
  im=Image.new('RGBA',(96,72),(255,255,255,0 if transparent else 255));p=ImageDraw.Draw(im);p.ellipse((9,7,72,62),fill=(210,30,80,255));p.rectangle((51,34,89,59),fill=(20,160,210,255));p.ellipse((25,24,41,40),fill=(255,255,255,0 if transparent else 255));a=np.array(im);base='alpha' if transparent else 'opaque';im.save(out/(base+'.png'));(out/(base+'.rgba')).write_bytes(a.tobytes())
  for category in ['photo','aa','hard']:
   for detail in [0,1,2]:
    name=base+'-'+category+'-'+str(detail);cfg={'category':category,'photo_regions':True,'photo_spatial':True,'detail':detail,'colors':3,'palette':['#ffffff','#d21e50','#14a0d2'],'compute':'cpu','speckle':2,'artifact_strength':2,'segmentation_complexity':5,'curve_tolerance':.12*[4,2,1][detail],'alphamax':1.}
    svg,stats=trace(out/(base+'.png'),cfg);(out/(name+'-reference.svg')).write_text(svg,encoding='utf8');cases.append({'id':name,'source':base+'.rgba','w':96,'h':72,'config':{'category':category,'detail':detail,'colors':3,'palette':cfg['palette'],'speckle':2}})
 for i,source in enumerate(args.image):
  im=Image.open(source).convert('RGBA');name=f'private-{i}';w,h=im.size;im.save(out/(name+'.png'));(out/(name+'.rgba')).write_bytes(im.tobytes());cfg={'category':'photo','photo_regions':True,'photo_spatial':True,'detail':1,'colors':9,'compute':'cpu','speckle':2,'artifact_strength':2,'segmentation_complexity':5,'curve_tolerance':.24,'alphamax':1.};svg,_=trace(out/(name+'.png'),cfg);(out/(name+'-reference.svg')).write_text(svg,encoding='utf8');cases.append({'id':name,'source':name+'.rgba','w':w,'h':h,'config':{'category':'photo','detail':1,'colors':9,'speckle':2}})
 a=np.random.default_rng(37).integers(0,256,(17,19,4),dtype=np.uint8);(out/'resize-input.bin').write_bytes(a.tobytes());(out/'resize-reference.bin').write_bytes(cv2.resize(a,None,fx=2,fy=2,interpolation=cv2.INTER_LINEAR).tobytes())
 (out/'manifest.json').write_text(json.dumps(cases),encoding='utf8')
else:cases=json.loads((out/'manifest.json').read_text(encoding='utf8'))
subprocess.run(['node',str(ROOT/'tests/curves_parity.mjs'),str(out/'manifest.json')],cwd=ROOT,check=True)
def render(path,w,h):
 im=QImage(w,h,QImage.Format_RGBA8888);im.fill(Qt.transparent);p=QPainter(im);QSvgRenderer(QByteArray(path.read_bytes())).render(p);p.end();return np.frombuffer(im.bits(),np.uint8).copy().astype(float)
report=[]
for c in cases:
 ref=render(out/(c['id']+'-reference.svg'),c['w'],c['h']);actual=out/(c['id']+'-wasm.svg');v=render(actual,c['w'],c['h']);mae=float(np.abs(ref-v).mean());doc=ET.fromstring(actual.read_text(encoding='utf8'));audit={};audit_pieces([(p.get('fill'),p.get('d')) for p in doc.iter('{http://www.w3.org/2000/svg}path')],audit);print(c['id'],mae,flush=True);assert mae<.25,(c['id'],mae);report.append({'case':c['id'],'rgba_mae':mae,'audit':audit})
(out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('PASS: limited palette end-to-end desktop parity')
