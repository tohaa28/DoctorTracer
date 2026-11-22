"""Palette regression: transparency slot, exact candidate selection, RGB indices."""
import os,sys,tempfile
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from PySide6.QtWidgets import QApplication,QPushButton,QListWidget
from PIL import Image
import numpy as np
from engine import find_palette,trace
from refined import Window
app=QApplication.instance() or QApplication([])
a=np.zeros((48,96,4),dtype=np.uint8)
for i in range(12):a[4:44,i*8:(i+1)*8]=[(i*67)%256,(i*101)%256,(i*149)%256,255]
assert find_palette(a,1)==[np.median(a[a[:,:,3]>127,:3],axis=0).astype(int).tolist()]
with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'alpha.png';Image.fromarray(a).save(path)
    w=Window();w.load(str(path));w.color_mode='fixed';w.go('palette');app.processEvents()
    assert w.palette_has_transparency()
    assert len(w.palette_for(2))==1
    lst=w.findChild(QListWidget,'paletteCandidates');assert lst.currentRow()>=0
    assert w.manual_palette==w.palette_candidates[lst.currentRow()]
    assert w.palette_swatch_widget.findChild(type(__import__('palette_ui').transparent_swatch()),'transparentSwatch') is not None
    first=w.palette_swatches.itemAt(1).widget();assert isinstance(first,QPushButton) and first.property('paletteIndex')==0
    first.click();assert w.selected_color==0
    for n in (2,9,12,24):
        w.manual_palette=w.palette_for(n);w.draw_palette();app.processEvents()
        slots=[w.palette_swatches.itemAt(i).widget() for i in range(w.palette_swatches.count()) if w.palette_swatches.itemAt(i).widget()]
        assert len(slots)==len(w.manual_palette)+1
        assert sum(b.width() for b in slots)+2*(len(slots)-1)<=260
    w.manual_palette=['#abcdef']+w.manual_palette[1:];w.draw_palette();assert lst.currentRow()==-1
    w.choose_transparency('white');assert not w.palette_has_transparency()
    w.choose_transparency('preserve');assert w.palette_has_transparency() and w.analysis['transparent']
    w.color_mode='two';w.manual_palette=w.palette_for(2);assert len(w.config()['palette'])==1
    svg,stats=trace(path,{'category':'aa','colors':2,'palette':w.manual_palette,'compute':'cpu','speckle':0,'detail':2});assert svg.count('id="color-')==1
    w.close()
print('Palette desktop: transparent slot, 2/9/12/24 counts, selection, editing indices, flatten/preserve passed')
