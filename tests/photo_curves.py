"""Regression for the enlarged stepped-boundary defect and native DLL ABI."""
import sys,math,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from photo_curves import refit_curves,qpath
from native_potrace import trace
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import Qt
import numpy as np

def raster(svg):
 from PySide6.QtSvg import QSvgRenderer
 from PySide6.QtCore import QByteArray,QRectF
 image=QImage(128,128,QImage.Format_RGBA8888);image.fill(Qt.transparent);p=QPainter(image);QSvgRenderer(QByteArray(svg.encode())).render(p,QRectF(0,0,128,128));p.end();return np.frombuffer(image.bits(),np.uint8).reshape(128,128,4).copy()
points=[(round(64+43*math.cos(i*2*math.pi/200)),round(64+35*math.sin(i*2*math.pi/200))) for i in range(200)]
data='M'+'L'.join(f'{x} {y}' for x,y in points)+'Z'
svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128"><path fill="#209cb5" d="{data}"/><path fill="#fff" d="M48 50L80 50L80 78L48 78Z"/></svg>'
fitted,n=refit_curves(svg,.4,1.2);root=ET.fromstring(fitted);assert n==2 and len(root)==2
assert root[0].get('fill')=='#209cb5' and root[0].get('d').count('C')<30
a,b=raster(svg),raster(fitted);union=(a[:,:,3]>127)|(b[:,:,3]>127)
iou=((a[:,:,3]>127)&(b[:,:,3]>127)).sum()/union.sum()
print('synthetic silhouette IoU',float(iou))
assert iou>.98
assert np.all(b[64,64,:3]==255) and b[0,0,3]==0
mask=np.zeros((13,37),bool);mask[2:5,3:9]=True;mask[9:11,29:34]=True
out=trace(mask,{'curve_tolerance':.2,'alphamax':1.});path=qpath(out[0]);assert path.contains(__import__('PySide6.QtCore',fromlist=['QPointF']).QPointF(5,3));assert not path.contains(__import__('PySide6.QtCore',fromlist=['QPointF']).QPointF(5,10))
assert trace(np.zeros((9,33),bool),{})==[]
for i in range(30):assert trace(mask,{})==trace(mask,{})
print('PASS: smooth Beziers, silhouette IoU > .98, colors, white interior, transparency, odd bitmap stride/orientation, deterministic repeated native calls')
