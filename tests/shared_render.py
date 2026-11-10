"""Touching colours cover the pixel together, without a transparent AA seam."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import Qt,QByteArray,QRectF
from vector_render import QSvgRenderer
app=QApplication([])
svg=b'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" data-color-objects="merged" data-shared-boundaries="true"><path fill="#ff0000" d="M0 0 L64 0 L0 64 Z"/><path fill="#0000ff" d="M64 0 L64 64 L0 64 Z"/></svg>'
r=QSvgRenderer(QByteArray(svg))
def render(bounds):
    im=QImage(64,64,QImage.Format_RGBA8888);im.fill(Qt.transparent);p=QPainter(im);r.render(p,bounds);p.end();return np.frombuffer(im.bits(),np.uint8).reshape(64,64,4).copy()
a=render(QRectF(0,0,64,64));assert a[:,:,3].min()==255;assert a[:,:,1].max()==0
assert np.array_equal(a,render(QRectF(0,0,64,64)))
b=render(QRectF(-5,-7,64,64));assert np.array_equal(a[7:,5:],b[:57,:59])
c=render(QRectF(-640,-640,1280,1280));assert c[:,:,3].min()==255
print('Shared coverage: opaque diagonal, no white seam, cached equality, panning and large zoom passed')
