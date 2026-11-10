"""Generate layout references from the actual desktop widgets and artwork."""
import os,sys,json
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'desktop'))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtCore import QByteArray
import wizard
from refined import Window
from vector_render import QSvgRenderer
app=QApplication([])
for font in ['tahoma.ttf','tahomabd.ttf']:
 path=Path('C:/Windows/Fonts')/font
 if path.is_file():QFontDatabase.addApplicationFont(str(path))
app.setStyle('windowsvista');app.setFont(QFont('Tahoma',9));app.setStyleSheet(wizard.STYLE)
w=Window();w.resize(1280,689);w.show();w.load(str(root/'web/demo.png'));w.svg_text=(root/'web/demo.svg').read_text(encoding='utf8');w.canvas.svg=QSvgRenderer(QByteArray(w.svg_text.encode()));w.export_button.setEnabled(True);app.processEvents();out=root/'build/ui-reference';out.mkdir(parents=True,exist_ok=True);reports=[]
for page in ['load','mode','type','quality','color','review','export']:
 w.page=page;w.render_page();app.processEvents();w.right.grab().save(str(out/(page+'.png')))
 cards=[{'title':c.title,'width':c.width(),'height':c.height()}for c in w.right.findChildren(wizard.Choice)]
 reports.append({'page':page,'sidebar_width':w.right.width(),'cards':cards,'nav_height':w.next_button.height(),'header_height':w.title.parentWidget().height()})
(out/'layout.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf8');r=next(row for row in reports if row['page']=='mode');(root/'web/desktop-layout.json').write_text(json.dumps({'source':'desktop/wizard.py + refined.py','sidebar_width':r['sidebar_width'],'card_width':r['cards'][0]['width'],'card_height':r['cards'][0]['height'],'header_height':r['header_height'],'nav_height':r['nav_height'],'icon_width':99,'icon_height':90},indent=2),encoding='utf8');w.close();print('Desktop sidebar references:',out)
