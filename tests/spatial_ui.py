"""Opt-in state, presets, stale exports, and real worker integration."""
import sys,time,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from PySide6.QtWidgets import QApplication
from PIL import Image,ImageDraw
from refined import Window

app=QApplication([])
w=Window();w.show();app.processEvents()
with tempfile.TemporaryDirectory() as directory:
    source=Path(directory)/'тест.png'
    im=Image.new('RGBA',(127,95),'white');draw=ImageDraw.Draw(im)
    draw.ellipse((10,10,100,85),fill='#185890');im.save(source)
    w.load(str(source))
    assert w.config()['photo_spatial'] and w.config()['compute']=='gpu'
    w.apply_settings({'category':'photo','detail':1,'palette':['#ffffff','#185890'],'compute':'gpu','photo_spatial':True})
    assert w.config()['photo_spatial'] and w.config()['compute']=='gpu'
    w.wizard_mode='advanced'
    assert w.config()['category']=='photo'
    w.wizard_mode='basic'
    w.begin_trace()
    deadline=time.monotonic()+30
    while w.process and time.monotonic()<deadline:
        app.processEvents();time.sleep(.02)
    assert not w.process and w.svg_text and w.export_button.isEnabled()
    import json
    stats=json.loads(w.result_file.read_text())
    assert stats['segmentation']=='spatial-experimental'
    w.set_photo_spatial(False)
    assert not w.export_button.isEnabled()
    w.restore_defaults()
    assert w.config()['photo_spatial'] and w.config()['compute']=='gpu'
w.close()
print('PASS: opt-in defaults, preset state, actual worker, stale export, advanced photo type')
