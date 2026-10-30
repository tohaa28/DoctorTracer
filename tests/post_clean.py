import sys,json,time,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from post_clean import clean
from boundary_contract import segments
from color_objects import pdf_bytes
out=ROOT/'build/post-clean';out.mkdir(exist_ok=True)
def svg(paths):return '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><g id="result">'+''.join('<g fill="'+color+'"><path fill="'+color+'" d="'+d+'"/></g>' for color,d in paths)+'</g></svg>'
outer='M0 0 L100 0 L100 100 L0 100 Z';hole='M20 20 L20 22 L22 22 L22 20 Z';island='M20 20 L22 20 L22 22 L20 22 Z'
islands=svg([('#ff0000',outer+' '+hole),('#0000ff',island)])
a='M0 0 L50 0 '+' '.join(f'L50 {i}'for i in range(2,101,2))+' L0 100 Z'
b='M50 0 L100 0 L100 100 L50 100 '+' '.join(f'L50 {i}'for i in range(98,-1,-2))+' Z'
lines=svg([('#ff0000',a),('#0000ff',b)])
thin=svg([('#000000','M20 20 L40 20 L40 21 L20 21 Z')])
junction=svg([('#ff0000','M0 0 L10 0 L10 1 L9 2 L0 2 Z'),('#0000ff','M10 0 L100 0 L100 100 L10 100 L10 1 Z'),('#00ff00','M0 2 L9 2 L10 1 L10 100 L0 100 Z')])
# Eight cubic arcs approximate a circle: verify simplification against analytic geometry.
k=0.5522847498307936;r=30.;c=50.
quarters=[[(80,50),(80,50+k*r),(50+k*r,80),(50,80)],[(50,80),(50-k*r,80),(20,50+k*r),(20,50)],[(20,50),(20,50-k*r),(50-k*r,20),(50,20)],[(50,20),(50+k*r,20),(80,50-k*r),(80,50)]]
curved='M80 50 '
for q in quarters:
 a,b,c1=[tuple((q[i][j]+q[i+1][j])/2 for j in range(2)) for i in range(3)]
 d,e=[tuple((u[j]+v[j])/2 for j in range(2)) for u,v in [(a,b),(b,c1)]];m=tuple((d[j]+e[j])/2 for j in range(2))
 for controls in [[a,d,m],[e,c1,q[3]]]:curved+='C'+' '.join(str(v)for xy in controls for v in xy)+' '
curved+='Z';circle=svg([('#ff0000',curved)])
# Reverse every cubic to represent the same interface as the surrounding hole.
circle_edges=list(segments(curved,True));reverse=''
# Read the authored cubic list, preserving exact original controls.
import re
coords=[float(x)for x in re.findall(r'[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?',curved)]
cur=(coords[0],coords[1]);arcs=[]
for i in range(2,len(coords),6):
 v=coords[i:i+6];arcs.append((cur,v));cur=tuple(v[4:6])
reverse='M80 50 '
for start,v in reversed(arcs):reverse+='C'+' '.join(str(x)for x in [*v[2:4],*v[0:2],*start])+' '
reverse+='Z'
shared_circle=svg([('#ff0000',outer+' '+reverse),('#0000ff',curved)])
scaled=islands.replace('width="100" height="100"','width="50" height="50"')
cases=[('shared-circle',shared_circle,0,.25,True),('scaled-islands',scaled,1,0,True),('circle',circle,0,.25,True),('islands',islands,4,0,True),('disabled',islands,0,0,True),('lines',lines,0,.25,True),('thin-protected',thin,30,0,True),('thin-delete',thin,30,0,False),('junction',junction,100,0,True)]
private=ROOT/'build/shared-boundary-fix/corrected.svg'
if private.exists():cases.append(('real',private.read_text(encoding='utf8'),4,.25,True))
jobs=[]
for name,source,area,tol,protect in cases:
 t=time.perf_counter();result,stats=clean(source,area,tol,protect);elapsed=time.perf_counter()-t
 assert stats['nodes_after']<=stats['nodes_before'],(name,stats)
 if name=='shared-circle':
  paths=list(ET.fromstring(result).iter('{http://www.w3.org/2000/svg}path'));left=dict(segments(paths[0].get('d'),True));right=dict(segments(paths[1].get('d'),True));shared=set(left)&set(right);assert len(shared)==4 and all(left[k]+right[k]==0 for k in shared),stats
 if name in ['islands','scaled-islands']:
  assert stats['removed_elements']==1 and stats['nodes_after']==4,stats
 if name=='circle':
  assert stats['nodes_after']<stats['nodes_before'] and 'C' in result,stats
  path=next(ET.fromstring(result).iter('{http://www.w3.org/2000/svg}path'))
  for segment in segments(path.get('d')):
   if segment[0]!=1:continue
   coords=[(segment[i]/10000,segment[i+1]/10000)for i in range(1,len(segment),2)]
   for i in range(201):
    t=i/200;u=1-t;pt=[u**3*coords[0][j]+3*u*u*t*coords[1][j]+3*u*t*t*coords[2][j]+t**3*coords[3][j]for j in range(2)]
    assert abs(((pt[0]-50)**2+(pt[1]-50)**2)**.5-30)<.25
 if name=='islands':
  assert stats['removed_elements']==1 and stats['nodes_after']==4,stats
  assert len(list(ET.fromstring(result).iter('{http://www.w3.org/2000/svg}path')))==1
 if name in ['disabled','thin-protected','junction']:assert result==source,(name,stats)
 if name=='lines':
  assert stats['nodes_after']==8,stats
  paths=list(ET.fromstring(result).iter('{http://www.w3.org/2000/svg}path'));left=dict(segments(paths[0].get('d'),True));right=dict(segments(paths[1].get('d'),True));shared=set(left)&set(right);assert len(shared)==1 and all(left[k]+right[k]==0 for k in shared)
 if name=='thin-delete':assert stats['removed_elements']==1
 pdf=pdf_bytes(result);assert b'/Subtype /Image' not in pdf
 if name=='real':assert pdf.count(b'/Subtype /Form')==4
 (out/(name+'-input.svg')).write_text(source,encoding='utf8');(out/(name+'-native.svg')).write_text(result,encoding='utf8')
 jobs.append({'name':name,'area':area,'tolerance':tol,'protect':protect,'stats':stats,'seconds':elapsed})
(out/'jobs.json').write_text(json.dumps(jobs,indent=2),encoding='utf8');print(json.dumps(jobs,indent=2))
