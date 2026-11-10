import sys,time,os
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from PySide6.QtWidgets import QApplication,QWidget
from PySide6.QtCore import QByteArray
from vector_render import QSvgRenderer
from post_smooth_dialog import SmoothDialog,_jobs
app=QApplication.instance() or QApplication([])
class Canvas:
 def update(self):pass
class Owner(QWidget):
 def __init__(self,svg):super().__init__();self.svg_text=svg;self.canvas=Canvas();self.canvas.svg=QSvgRenderer(QByteArray(svg.encode()))
 def set_contours(self):pass
source=(ROOT/'build/post-smooth/interface-35-input.svg').read_text(encoding='utf8')
owner=Owner(source)
def preview(d):
 deadline=time.monotonic()+10
 while time.monotonic()<deadline:
  app.processEvents();time.sleep(.01)
  if d.apply.isEnabled():return
 raise AssertionError(d.info.text())
d=SmoothDialog(owner);preview(d);assert owner.svg_text!=source;d.reject();assert owner.svg_text==source
# Closing during computation must not destroy a live QThread.
d=SmoothDialog(owner);d.calculate();d.reject();assert owner.svg_text==source
while _jobs:app.processEvents();time.sleep(.01)
d=SmoothDialog(owner);preview(d);d.accept();assert owner.svg_text!=source and owner.post_smooth_undo==[source]
changed=owner.svg_text;d=SmoothDialog(owner);d.slider.setValue(0)
for _ in range(30):app.processEvents();time.sleep(.01)
assert owner.svg_text==changed and not d.apply.isEnabled();d.reject()
while _jobs:app.processEvents();time.sleep(.01)
print('PASS: preview, cancel, apply, undo snapshot, zero strength, close while worker is active')
