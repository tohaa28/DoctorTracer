import sys,tempfile,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'desktop'))
from PySide6.QtWidgets import QApplication,QPushButton,QLineEdit
from PySide6.QtGui import QFont
from refined import Window
from PIL import Image
app=QApplication([]);app.setStyle('windowsvista');w=Window();w.show()
w.file='C:/very-long-folder-name/another-folder/a-long-image-name.png';w.canvas.image_size.setWidth(568);w.canvas.image_size.setHeight(960)
for size in [(820,640),(960,720),(1200,850)]:
 for pt in [9,11]:
  app.setFont(QFont('Tahoma',pt));w.resize(*size);w.page='export';w.render_page();app.processEvents()
  for button in w.scroll.widget().findChildren(QPushButton):
   if button.isCheckable() and button.text().startswith('▶'):button.click()
  app.processEvents()
  assert w.scroll.horizontalScrollBar().maximum()==0,(size,pt,w.scroll.horizontalScrollBar().maximum())
  for field in w.scroll.widget().findChildren(QLineEdit):assert field.width()>40,(size,pt,field.width())
  w.scroll.verticalScrollBar().setValue(w.scroll.verticalScrollBar().maximum());app.processEvents()
  print('expanded export layout',size,pt,'PASS')
w.close()
with tempfile.TemporaryDirectory() as d:
 d=Path(d);im=d/'input.png';Image.new('RGB',(80,60),(50,150,100)).save(im)
 job=d/'job.json';job.write_text(json.dumps({'input':str(im),'output':str(d/'out.svg'),'result':str(d/'result.json'),'config':{'category':'photo','detail':1,'compute':'gpu','photo_regions':True}}))
 r=subprocess.run([sys.executable,str(root/'desktop/app.py'),'--worker-server'],input=json.dumps({'job':str(job),'progress':True})+'\n',text=True,capture_output=True,timeout=60)
 msgs=[json.loads(line) for line in r.stdout.splitlines()];progress=[m['progress'] for m in msgs if 'progress' in m]
 assert msgs[-1]=={'exit_code':0},(r.stdout,r.stderr)
 assert progress[0]==0 and progress[-1]==100 and progress==sorted(set(progress)),progress
 assert len(progress)>8,progress
 print('worker progress',progress,'PASS')
