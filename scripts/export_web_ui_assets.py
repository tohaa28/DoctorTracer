"""Render browser artwork from the actual desktop drawing code; no proprietary assets."""
import os,sys
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'desktop'))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QRect
from ui_icons import icon
from refined import arrow_icon
from wizard import ClassicCanvas
app=QApplication([])
for name in ['tahoma.ttf','tahomabd.ttf']:
 path=Path('C:/Windows/Fonts')/name
 if path.is_file():QFontDatabase.addApplicationFont(str(path))
folder=root/'web/desktop-icons';folder.mkdir(parents=True,exist_ok=True)
for kind in ['folder','clipboard','batch','gears','auto','basic','advanced','review','photo','flex','fixed','two','save','aa','hard','high','medium','low']:icon(kind).save(str(folder/(kind+'.png')))
for kind in ['next','back','home','reset','cancel']:arrow_icon(kind).pixmap(28,28).save(str(folder/('nav-'+kind+'.png')))
canvas=ClassicCanvas();canvas.resize(928,667);canvas.show();app.processEvents();canvas.grab().copy(QRect(236,155,456,351)).save(str(folder/'drop.png'));canvas.close();print('Rendered original desktop artwork to',folder)
