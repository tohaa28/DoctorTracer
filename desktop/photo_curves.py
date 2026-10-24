"""Replace short photographic path segments with optimized Potrace Beziers.

MIT licensed adapter; the linked Potrace library is GPL-2.0-or-later.
This operates on vector region geometry, without blurring the source image.
"""
import re,math,xml.etree.ElementTree as ET
import numpy as np
from native_potrace import trace as native_trace
from PySide6.QtGui import QPainterPath,QImage,QPainter
from PySide6.QtCore import Qt
def qpath(data):
 t=re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',data);p=QPainterPath();p.setFillRule(Qt.WindingFill);i=0;cmd=''
 while i<len(t):
  if t[i].isalpha():cmd=t[i];i+=1
  if cmd in ('Z','z'):p.closeSubpath();cmd='';continue
  n={'M':2,'L':2,'C':6}[cmd];v=list(map(float,t[i:i+n]));i+=n
  if cmd=='M':p.moveTo(*v);cmd='L'
  elif cmd=='L':p.lineTo(*v)
  else:p.cubicTo(*v)
 return p

def refit_curves(svg,tol=.4,alpha=1.2):
 root=ET.fromstring(svg);out=ET.Element(root.tag,root.attrib);count=0
 for el in root:
  p=qpath(el.get('d',''));m=re.search(r'translate\(([-\d.]+)[, ]+([-\d.]+)\)',el.get('transform',''))
  if m:p.translate(float(m[1]),float(m[2]))
  b=p.boundingRect()
  x,y=math.floor(b.left())-2,math.floor(b.top())-2;w,h=math.ceil(b.right())-x+2,math.ceil(b.bottom())-y+2
  if w*h>20000000:raise RuntimeError('oversize')
  image=QImage(w,h,QImage.Format_RGBA8888);image.fill(Qt.transparent);paint=QPainter(image);paint.setRenderHint(QPainter.Antialiasing,True);paint.translate(-x,-y);paint.setPen(Qt.NoPen);paint.setBrush(Qt.white);paint.drawPath(p);paint.end();a=np.frombuffer(image.bits(),np.uint8).reshape(h,w,4)[:,:,3]>127
  if not a.any():continue
  paths=native_trace(a,{'detail':1,'curve_tolerance':tol,'alphamax':alpha})
  if paths:ET.SubElement(out,el.tag,{'d':' '.join(paths),'fill':el.get('fill'),'transform':f'translate({x},{y})'})
  count+=1
 return ET.tostring(out,encoding='unicode'),count
