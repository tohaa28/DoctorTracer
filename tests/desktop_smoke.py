"""Synthetic regression checks; no user images or reference program required."""
import sys,tempfile,json,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
import engine,numpy as np
from PIL import Image,ImageDraw
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import QByteArray,QRectF,Qt
from PySide6.QtSvg import QSvgRenderer
app=QApplication([])
def render(svg):
 im=QImage(96,80,QImage.Format_RGBA8888);im.fill(Qt.transparent);p=QPainter(im);QSvgRenderer(QByteArray(svg.encode())).render(p,QRectF(0,0,96,80));p.end();return np.frombuffer(im.bits(),np.uint8).reshape(80,96,4).copy()
with tempfile.TemporaryDirectory(prefix='doctor-tracer-') as directory:
 root=Path(directory);source=root/'цветной тест.png';image=Image.new('RGBA',(96,80));draw=ImageDraw.Draw(image);draw.rectangle((9,8,86,71),fill='#8044cc');draw.rectangle((30,26,65,54),fill='white');image.save(source)
 cfg={'category':'aa','detail':2,'speckle':0,'compute':'cpu'};svg,stats=engine.trace(source,cfg);gpu,_=engine.trace(source,{**cfg,'compute':'gpu'});assert svg==gpu
 a=render(svg);assert a[1,1,3]==0 and a[40,45,3]>250 and np.all(a[40,45,:3]>250);assert '<image' not in svg
 eps=engine.to_eps(svg);assert eps.startswith('%!PS-Adobe-3.0') and 'fill' in eps and 'image' not in eps
 assert engine.analyze_image(source)['category']=='aa'
 rng=np.random.default_rng(7);pixels=rng.integers(0,256,(80,96,4),dtype=np.uint8);pixels[:8,:,3]=0;photo=root/'photo.png';Image.fromarray(pixels).save(photo)
 for detail in range(3):
  output,st=engine.trace(photo,{'category':'photo','detail':detail,'speckle':2});assert st['compute']=='CPU' and st['alpha_threshold']==128;assert render(output)[0,48,3]==0
 flat,_=engine.trace(photo,{'category':'photo','detail':2,'flatten':True});assert render(flat)[0,48,3]>250
 job=root/'job.json';out=root/'result.svg';result=root/'result.json';job.write_text(json.dumps({'input':str(source),'output':str(out),'result':str(result),'config':cfg}),encoding='utf8')
 command=[sys.executable,str(Path(engine.__file__).parent/'app.py'),'--worker-server'];process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,encoding='utf8');stdout,_=process.communicate(json.dumps({'job':str(job)})+'\n'+json.dumps({'job':str(job)})+'\n',timeout=30);assert process.returncode==0 and len(stdout.splitlines())==2 and all(json.loads(line)['exit_code']==0 for line in stdout.splitlines());assert json.loads(result.read_text())['ok'];assert out.read_text()==svg
print(json.dumps({'ok':True,'checks':['transparent silhouette','enclosed white','CPU/GPU equality or fallback','vector EPS','three photo qualities','flattening','resident Unicode worker twice']}))
