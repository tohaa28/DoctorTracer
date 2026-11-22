"""Joint-energy monotonicity, manual RGB ownership and full-raster refit."""
import sys,json,subprocess
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'desktop'),str(ROOT/'quality')]
import bench
from engine import trace
from joint_palette import refine
from raster_refit import optimize
app=bench.app();out=ROOT/'build/joint-raster';out.mkdir(exist_ok=True)
yy,xx=np.indices((64,80));a=np.empty((64,80,4),np.uint8);a[:,:,:3]=np.stack([40+xx*2,20+yy*3,30+(xx+yy)],2);a[:,:,3]=255;a[19:28,22:37,3]=0
path=out/'joint.png';Image.fromarray(a).save(path);(out/'joint.rgba').write_bytes(a.tobytes());inks=['#3c2832','#b4a096','#78644b','#b47850']
cfg={'category':'photo','detail':1,'photo_regions':True,'photo_spatial':True,'colors':4,'palette':inks,'palette_generated':True,'compute':'cpu','speckle':2}
cpu,cs=trace(path,cfg);gpu,gs=trace(path,{**cfg,'compute':'gpu'})
assert cpu==gpu
assert cs['joint_palette_steps'] and all(r['after_energy']<=r['before_energy'] for r in cs['joint_palette_steps'])
assert cs['raster_refit']['after']<=cs['raster_refit']['before']
_,manual=trace(path,{**cfg,'palette_generated':False});assert manual['palette']==inks and 'joint_palette_steps' not in manual
with patch('gpu_edge_fit.evaluator',return_value=lambda _:(_ for _ in ()).throw(RuntimeError('injected device loss'))):
    fallback,fs=trace(path,{**cfg,'compute':'gpu'})
    assert fallback==cpu and 'injected device loss' in fs['edge_fit_gpu_fallback']
(out/'python.svg').write_text(cpu,encoding='utf-8');bench.write(out/'jobs.json',[{'id':'joint','source':'joint.rgba','output':'wasm.svg','w':80,'h':64,'config':cfg}])
subprocess.run(['node','quality/run_wasm.mjs',str(out/'jobs.json')],cwd=ROOT,check=True)
left=bench.render(out/'python.svg',80,64);right=bench.render(out/'wasm.svg',80,64);mae=float(np.abs(left.astype(float)-right.astype(float)).mean());assert mae<=.02,mae
# The target circle is independently rasterized from a high-resolution bitmap.
im=Image.new('RGBA',(512,512),'white');ImageDraw.Draw(im).ellipse((64,64,448,448),fill='black');source=np.array(im.resize((64,64),Image.Resampling.LANCZOS))
svg='<svg><path fill="#ffffff" d="M0 0 L64 0 L64 64 L0 64 Z"/><path fill="#000000" d="M32 8 C39 8 56 25 56 32 C56 39 39 56 32 56 C25 56 8 39 8 32 C8 25 25 8 32 8 Z"/></svg>'
_,fit=optimize(svg,source);assert fit['after']<fit['before'],fit
bench.write(out/'results.json',{'joint_steps':cs['joint_palette_steps'],'cpu_gpu_exact':True,'manual_palette_preserved':True,'gpu_device_loss_fallback':True,'python_wasm_rgba_mae':mae,'full_raster_improvement':fit})
print(json.dumps({'ok':True,'joint_steps':len(cs['joint_palette_steps']),'parity_mae':mae,'raster':fit}))
