"""Run the built portable executable's real worker on a synthetic raster."""
import sys,tempfile,json,subprocess,os
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1]
exe=root/'rebuilt/DoctorTracer/DoctorTracer.exe'
assert exe.is_file()
with tempfile.TemporaryDirectory(prefix='doctortracer-release-') as tmp:
    tmp=Path(tmp);im=Image.new('RGBA',(96,80));d=ImageDraw.Draw(im);d.rectangle((8,8,87,71),fill='#8044cc');d.rectangle((28,24,65,55),fill='white')
    src=tmp/'sample.png';im.save(src)
    job=tmp/'job.json';out=tmp/'result.svg';result=tmp/'result.json'
    job.write_text(json.dumps(dict(input=str(src),output=str(out),result=str(result),config=dict(category='aa',detail=2,speckle=0,compute='cpu'))),encoding='utf8')
    p=subprocess.run([str(exe),'--worker',str(job)],cwd=exe.parent,env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},timeout=120)
    assert p.returncode==0,p.returncode
    assert json.loads(result.read_text(encoding='utf8'))['ok']
    assert '<svg' in out.read_text(encoding='utf8') and '<path' in out.read_text(encoding='utf8')
print('PASS portable DoctorTracer.exe real trace worker')
