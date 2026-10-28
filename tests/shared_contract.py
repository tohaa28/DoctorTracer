"""Common curves must pair exactly; transparency is an audited exterior face."""
import sys,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'desktop'),str(ROOT/'quality')]
import bench
from shared_regions import trace
from boundary_contract import verify
out=ROOT/'build/shared-contract';out.mkdir(exist_ok=True);bench.app();jobs=[]
for alpha in [False,True]:
 for smooth in [False,True]:
  a=np.zeros((64,80),np.uint8);a[7:55,8:70]=1;a[20:48,18:54]=2;a[30:32,20:70]=3;a[10:24,46:49]=3
  if alpha:a[:5]=255;a[35:38,30:33]=255
  pal=[[255,30,0],[20,0,0],[250,210,0],[250,250,230]]
  svg,stats=trace(a,pal,(80,64),smooth=smooth,curve_tolerance=.25,passes=2,polygon=not smooth)
  gpu,gs=trace(a,pal,(80,64),smooth=smooth,curve_tolerance=.25,passes=2,polygon=not smooth,compute='gpu')
  assert svg==gpu;assert 'data-boundary-contract="paired"' in svg
  assert stats['geometry_audit']['unmatched_edges']==0
  name=f'{alpha}-{smooth}';(out/(name+'.svg')).write_text(svg,encoding='utf8');(out/(name+'.i32')).write_bytes(np.where(a==255,-1,a.astype(np.int32)).astype(np.int32).tobytes());jobs.append({'name':name,'w':80,'h':64,'palette':pal,'smooth':smooth})
# Reject even a single serialized coordinate disagreement, without area tolerance.
left='M0 0 L10 0 L10 10 L0 10 Z';right='M0 0 L0 10 L10 10 L10 0 Z'
verify([(0,left),(1,right)])
try:verify([(0,left),(1,left)])
except ValueError:pass
else:raise AssertionError('Equal edge orientations were accepted')
try:verify([(0,left),(1,right.replace('L10 10','L10.0001 10'))])
except ValueError:pass
else:raise AssertionError('Boundary mismatch was accepted')
(out/'jobs.json').write_text(json.dumps(jobs),encoding='utf8');subprocess.run(['node','tests/shared_contract.mjs'],cwd=ROOT,check=True)
for j in jobs:
 a=bench.render(out/(j['name']+'.svg'),80,64);b=bench.render(out/(j['name']+'-wasm.svg'),80,64);mae=float(np.abs(a.astype(float)-b.astype(float)).mean());assert mae<=.02,mae
print('PASS: exact paired geometry, fault rejection, transparent holes, CPU/GPU/Rust parity')
