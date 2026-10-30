"""Render large merged color objects without Qt SVG parser element limits."""
import xml.etree.ElementTree as ET
from PySide6.QtSvg import QSvgRenderer as NativeRenderer
from PySide6.QtCore import Qt,QRectF,QSize
from PySide6.QtGui import QPainterPath,QColor,QPen,QPainter,QImage
import math
from photo_curves import qpath

class ColorRenderer:
    def __init__(self,data):
        self.root=ET.fromstring(data);r=self.root
        self.view=QRectF(*map(float,r.get('viewBox',f"0 0 {r.get('width')} {r.get('height')}").split()))
        self.size=QSize(round(float(r.get('width'))),round(float(r.get('height'))));self.shapes={}
        self.shared=r.get('data-shared-boundaries')=='true';self.cache=None
        for el in r.iter('{http://www.w3.org/2000/svg}path'):
            key=(el.get('fill','#000000'),el.get('stroke','none'),el.get('stroke-width','1'))
            if key not in self.shapes:
                p=QPainterPath();p.setFillRule(Qt.WindingFill);self.shapes[key]=p
            self.shapes[key].addPath(qpath(el.get('d','')))
    def isValid(self):return True
    def defaultSize(self):return self.size
    def viewBoxF(self):return self.view
    def render(self,painter,bounds=None):
        bounds=bounds or QRectF(0,0,self.size.width(),self.size.height())
        if not self.shared or not painter.worldTransform().isIdentity() or any(fill=='none' for fill,_,_ in self.shapes):
            return self.draw(painter,bounds,True)
        # Rasterize a partition jointly. Source-over antialiasing each colour
        # separately makes two touching half-covered pixels only 75% opaque.
        clip=bounds.intersected(painter.clipBoundingRect() if painter.hasClipping() else QRectF(painter.viewport()))
        if clip.isEmpty():return
        ratio=painter.device().devicePixelRatioF();w=max(1,math.ceil(clip.width()*ratio));h=max(1,math.ceil(clip.height()*ratio))
        samples=3 if w*h<=1500000 else 2 if w*h<=3000000 else 1
        key=(bounds.x(),bounds.y(),bounds.width(),bounds.height(),clip.x(),clip.y(),clip.width(),clip.height(),w,h,samples)
        if self.cache is None or self.cache[0]!=key:
            im=QImage(w*samples,h*samples,QImage.Format_ARGB32_Premultiplied);im.fill(Qt.transparent)
            p=QPainter(im);p.scale(samples*ratio,samples*ratio);p.translate(-clip.x(),-clip.y());self.draw(p,bounds,False);p.end()
            if samples>1:im=im.scaled(w,h,Qt.IgnoreAspectRatio,Qt.SmoothTransformation)
            self.cache=(key,im)
        painter.save();painter.setRenderHint(QPainter.SmoothPixmapTransform);painter.drawImage(clip,self.cache[1]);painter.restore()
    def draw(self,painter,bounds,antialias):
        painter.save();painter.setClipRect(bounds);painter.setRenderHint(QPainter.Antialiasing,antialias)
        painter.translate(bounds.left(),bounds.top());painter.scale(bounds.width()/self.view.width(),bounds.height()/self.view.height());painter.translate(-self.view.left(),-self.view.top())
        for (fill,stroke,width),path in self.shapes.items():
            painter.setBrush(Qt.NoBrush if fill=='none' else QColor(fill))
            painter.setPen(Qt.NoPen if stroke=='none' else QPen(QColor(stroke),float(width)))
            painter.drawPath(path)
        painter.restore()

def QSvgRenderer(data):
    if isinstance(data,str):return NativeRenderer(data)
    raw=bytes(data)
    return ColorRenderer(raw) if b'data-color-objects="merged"' in raw else NativeRenderer(data)
