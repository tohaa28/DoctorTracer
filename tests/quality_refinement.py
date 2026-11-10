"""Quality mechanisms, CPU/GPU equivalence, and actual Python/Rust end-to-end gates."""
import sys,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'desktop'),str(ROOT/'quality')]
import bench
from engine import trace,find_palette
from region_cleanup import clean
app=bench.app();out=ROOT/'build/quality-refinement';out.mkdir(parents=True,exist_ok=True)
labels=np.zeros((20,30),np.uint8);labels[3,3]=1;labels[8,3]=2;labels[12,3:10]=1;labels[14:19,20:25]=2;labels[16,22]=0
pal=[[100,100,100],[110,110,110],[0,0,0]]
filtered=clean(labels,pal,8)
assert filtered[3,3]==0 and filtered[8,3]==2
assert np.all(filtered[12,3:10]==1) and filtered[16,22]==0
canvas=Image.new('RGBA',(240,180),'white');d=ImageDraw.Draw(canvas);d.ellipse((24,21,185,159),fill='#d21e50');d.rectangle((150,90,228,153),fill='#14a0d2');d.ellipse((69,63,108,105),fill='white')
image=canvas.resize((80,60),Image.Resampling.LANCZOS);p=out/'aa.png';image.save(p)
inks=find_palette(np.array(image),9)
assert len(inks)==3,(len(inks),inks)
jobs=[];stats=[]
for alpha in [False,True]:
    a=np.array(image)
    if alpha:a[:10,:,3]=0
    name='alpha' if alpha else 'opaque';path=out/(name+'.png');Image.fromarray(a).save(path);(out/(name+'.rgba')).write_bytes(a.tobytes())
    for category in ['photo','aa']:
        for manual in [False,True]:
            key=name+'-'+category+'-'+str(manual);cfg={'category':category,'detail':1,'colors':9,'photo_regions':True,'photo_spatial':True,'compute':'cpu','speckle':2}
            if manual:cfg['palette']=['#ffffff','#d21e50','#14a0d2']
            cpu,cs=trace(path,cfg);gpu,gs=trace(path,{**cfg,'compute':'gpu'})
            assert cpu==gpu,('CPU/GPU',key)
            if category=='photo':assert cs['geometry_audit']['max_intersection_area_px2']<=.0001
            (out/(key+'-python.svg')).write_text(cpu,encoding='utf8')
            jobs.append({'id':key,'source':name+'.rgba','output':key+'-wasm.svg','w':80,'h':60,'config':cfg})
            stats.append({'case':key,'cpu_gpu_exact':True,'edge_fit_compute':gs.get('edge_fit_compute'),'edge_fit_vertices':gs.get('edge_fit_vertices',0),'curve_refit_vertices':gs.get('curve_refit_vertices',0)})
bench.write(out/'jobs.json',jobs)
subprocess.run(['node','quality/run_wasm.mjs',str(out/'jobs.json')],cwd=ROOT,check=True)
for job,row in zip(jobs,stats):
    key=job['id'];a=bench.render(out/(key+'-python.svg'),80,60);b=bench.render(out/(key+'-wasm.svg'),80,60)
    mae=float(np.abs(a.astype(float)-b.astype(float)).mean());limit=.02 if job['config']['category']=='photo' else .25
    assert mae<=limit,(key,mae,limit)
    row.update(rgba_mae=mae,limit=limit)
bench.write(out/'results.json',{'cases':stats,'small_regions':True,'adaptive_palette':True})
print(json.dumps({'ok':True,'cases':len(stats),'gpu_fits':sum(r['edge_fit_compute']=='OpenCL GPU FP64' for r in stats),'max_parity_mae':max(r['rgba_mae'] for r in stats)}))
