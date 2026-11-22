"""GPU shared contours must preserve exact SVG, holes and independent audit."""
import os,sys,json
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from PySide6.QtWidgets import QApplication
from shared_regions import trace
import gpu_contours
from accelerator import gpu_runtime
app=QApplication.instance() or QApplication([]);device=gpu_runtime()[-1];cases=0
pal=[[20,40,60],[200,100,30],[20,40,60],[230,230,230]]
for kind in range(4):
 a=np.zeros((27,39),np.int32)
 if kind==0:
  a[3:24,3:36]=1;a[7:20,8:30]=3;a[12,15]=-1;a[13,16]=0
 elif kind==1:
  yy,xx=np.indices(a.shape);a=((xx//3+yy//4)%4).astype(np.int32);a[::7,::5]=-1
 elif kind==2:a=np.random.default_rng(671).integers(-1,4,a.shape,dtype=np.int32)
 else:a[5:22,10:28]=1;a[8:19,14:24]=-1
 for passes in [1,2,4,5,8,10]:
  for tolerance in [.05,.15,.25,.375,.5,.75,1.2]:
   cfg=dict(smooth=True,passes=passes,curve_tolerance=tolerance)
   cpu,_=trace(a,pal,(39,27),compute='cpu',**cfg);gpu,stats=trace(a,pal,(39,27),compute='gpu',**cfg)
   assert cpu==gpu,(kind,passes,tolerance)
   assert stats.get('contour_compute')=='OpenCL GPU FP64',stats
   cases+=1
saved=gpu_contours.smooth
try:
 def unavailable(*args,**kwargs):raise RuntimeError('injected GPU unavailable')
 gpu_contours.smooth=unavailable
 fallback,stats=trace(a,pal,(39,27),compute='gpu',**cfg)
 assert fallback==cpu and 'injected' in stats['contour_gpu_fallback']
finally:gpu_contours.smooth=saved
print(json.dumps({'ok':True,'device':device,'exact_svg_cases':cases,'cpu_fallback':True}))
