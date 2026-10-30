"""Cursor anchoring and fractional-wheel regression; no tracing involved."""
import os, sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF,QPoint,Qt
from PySide6.QtGui import QPixmap,QWheelEvent
from refined import Canvas
app=QApplication([]); c=Canvas(); c.resize(900,700); c.pix=QPixmap(800,600); c.fit()
pos=QPointF(220,180)
def point():
 r=c.image_rect(); return ((pos.x()-r.x())/r.width(),(pos.y()-r.y())/r.height())
a=point(); start=c.zoom
for delta in [15]*8+[-15]*8:
 e=QWheelEvent(pos,pos,QPoint(),QPoint(0,delta),Qt.NoButton,Qt.NoModifier,Qt.NoScrollPhase,False)
 c.wheelEvent(e)
 assert max(abs(x-y) for x,y in zip(a,point()))<1e-12
assert abs(c.zoom-start)<1e-12
print('PASS: fractional wheel, cursor anchor, reversible zoom')
