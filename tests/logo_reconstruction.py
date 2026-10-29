import sys,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'desktop'),str(ROOT/'quality')]
from logo_trace import trace
import bench
out=ROOT/'build/logo-reconstruction';out.mkdir(exist_ok=True);app=bench.app();jobs=[];ink=[34,83,147];palette=[[255,255,255],ink]
for name in ['rings','stars','combined','exact','transparent','no-model']:
 im=Image.new('RGBA',(192*8,144*8),'white');d=ImageDraw.Draw(im)
 if name in ['rings','combined']:
  d.ellipse((8*8,8*8,184*8,136*8),fill=tuple(ink));d.ellipse((15*8,14*8,177*8,130*8),fill='white');d.ellipse((21*8,19*8,171*8,125*8),outline=tuple(ink),width=6)
 if name in ['stars','combined']:
  for cx in [65,95,125]:
   p=[]
   for i in range(10):
    a=-math.pi/2+i*math.pi/5;r=8 if i%2==0 else 3.4;p.append(((cx+r*math.cos(a))*8,(42+r*math.sin(a))*8))
   d.polygon(p,fill=tuple(ink))
 if name=='no-model':d.rectangle((20*8,20*8,70*8,90*8),fill=tuple(ink))
 if name=='exact':d.rectangle((20*8,20*8,100*8,100*8),fill=tuple(ink))
 if name=='transparent':d.ellipse((8*8,8*8,184*8,136*8),fill=tuple(ink));im.putalpha(128)
 im=im.resize((192,144),Image.Resampling.NEAREST if name=='exact' else Image.Resampling.LANCZOS);a=np.array(im);candidate=trace(a,palette)
 if name in ['exact','transparent','no-model']:assert candidate is None,name;continue
 assert candidate is not None,name
 svg,stats=candidate;assert stats['geometry_verified'] and stats['geometry_audit']['max_intersection_area_px2']<=.0001
 if name in ['rings','combined']:assert stats['logo_reconstruction']['ellipse_rings']>=1,stats
 if name in ['stars','combined']:assert stats['logo_reconstruction']['stars']==3,stats
 (out/(name+'.svg')).write_text(svg,encoding='utf8');im.save(out/(name+'.png'));(out/(name+'.rgba')).write_bytes(a.tobytes());jobs.append({'name':name,'w':192,'h':144,'palette':palette,'stats':stats})
private=ROOT/'build/nf-quality/input.png'
if private.exists():
 a=np.array(Image.open(private).convert('RGBA'));result=trace(a,palette);assert result;svg,stats=result;assert stats['logo_reconstruction']['ellipse_rings']==2 and stats['logo_reconstruction']['stars']==4
 (out/'nf.svg').write_text(svg,encoding='utf8');(out/'nf.rgba').write_bytes(a.tobytes());jobs.append({'name':'nf','w':a.shape[1],'h':a.shape[0],'palette':palette,'stats':stats})
(out/'jobs.json').write_text(json.dumps(jobs,indent=2),encoding='utf8');print('PASS: primitive detection from pixels, protected exact/transparent/ordinary inputs, shared topology, overlap audit',len(jobs))
