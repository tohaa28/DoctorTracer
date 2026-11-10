import sys,time,os
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen';ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
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
source=(ROOT/'build/post-clean/islands-input.svg').read_text(encoding='utf8');owner=Owner(source)
def wait(d):
 deadline=time.monotonic()+10
 while time.monotonic()<deadline:
  app.processEvents();time.sleep(.01)
  if d.apply.isEnabled():return
 raise AssertionError(d.info.text())
d=SmoothDialog(owner,cleanup=True);wait(d);assert owner.svg_text!=source and '12 → 4' in d.info.text();d.reject();assert owner.svg_text==source
while _jobs:app.processEvents();time.sleep(.01)
d=SmoothDialog(owner,cleanup=True);wait(d);d.accept();assert owner.svg_text!=source and owner.post_smooth_undo==[source]
d=SmoothDialog(owner,cleanup=True);d.reset_values()
for _ in range(40):app.processEvents();time.sleep(.01)
assert not d.apply.isEnabled();d.reject()
while _jobs:app.processEvents();time.sleep(.01)
print('PASS: cleanup preview, live counters, cancel, apply/undo snapshot, reset, worker lifetime')
