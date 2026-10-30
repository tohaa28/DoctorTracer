import sys,json,math,time,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'desktop'),str(ROOT/'quality')]
from regularize import regularize
from boundary_contract import segments
from color_objects import pdf_bytes
out=ROOT/'build/regularize';out.mkdir(exist_ok=True)
def svg(ds):return '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'+''.join(f'<g fill="{color}"><path fill="{color}" d="{d}"/></g>'for color,d in ds)+'</svg>'
p=[(50+.08*math.sin(i*1.7),i*2.5)for i in range(41)];p[0]=(50,0);p[-1]=(50,100)
coords=lambda ps:' '.join(f'L{x:.6f} {y:.6f}'for x,y in ps)
a='M0 0 L50 0 '+coords(p[1:])+' L0 100 Z';b='M50 0 L100 0 L100 100 '+coords(list(reversed(p)))+' Z';wave=svg([('#ff0000',a),('#0000ff',b)])
# Noisy parabola: one globally fitted cubic replaces many local segments.
ps=[(10+i*2,10+.018*(i*2)**2+.06*math.sin(i*2.3))for i in range(31)];ps[0]=(10,10);ps[-1]=(70,74.8)
arc=svg([('#ff0000','M10 10 '+coords(ps[1:])+' L70 90 L10 90 Z')])
star=svg([('#ff0000','M50 10 L59 38 L88 38 L65 56 L74 85 L50 67 L26 85 L35 56 L12 38 L41 38 Z')])
tiny=svg([('#ff0000','M20 20 L23 20 L23 23 L20 23 Z')]);cases=[('wave',wave,.15,True,True,True),('wave-zero',wave,0,True,True,True),('disabled',wave,.15,False,False,True),('curve',arc,.2,False,True,True),('star',star,.3,True,True,True),('tiny',tiny,.3,True,True,True)]
bow=svg([('#ff0000','M10 10 C20 10.1 30 9.9 40 10 L40 50 L10 50 Z')]);cases.extend([('bow',bow,.15,True,False,True),('bow-keep',bow,.15,False,True,True)])
p=[(50+.08*math.sin(i*1.7),i*.1)for i in range(1001)];p[0]=(50,0);p[-1]=(50,100)
a='M0 0 L50 0 '+coords(p[1:])+' L0 100 Z';b='M50 0 L100 0 L100 100 '+coords(list(reversed(p)))+' Z';cases.append(('long-wave',svg([('#ff0000',a),('#0000ff',b)]),.15,True,True,True))
top=[(5+i*2.25,50+.1*math.sin(math.pi*i/40))for i in range(41)];bottom=[(x,100-y)for x,y in reversed(top)]
lens=svg([('#ff0000','M5 50 '+coords(top[1:])+' '+coords(bottom[1:])+' Z')]);cases.append(('thin-guard',lens,.3,True,True,True))
junction_points=[(50+.06*math.sin(i),i*2)for i in range(26)];junction_points[0]=(50,0);junction_points[-1]=(50,50)
a='M0 0 L50 0 '+coords(junction_points[1:])+' L0 50 Z';b='M0 50 L50 50 L50 100 L0 100 Z';c='M50 0 L100 0 L100 100 L50 100 L50 50 '+coords(list(reversed(junction_points[:-1])))+' Z'
cases.append(('junction',svg([('#ff0000',a),('#00ff00',b),('#0000ff',c)]),.15,True,True,True))
private=ROOT/'build/nf-quality/corrected.svg'
if private.exists():cases.append(('nf',private.read_text(encoding='utf8'),.15,True,True,True))
jobs=[]
for name,source,tol,straight,curved,protect in cases:
 start=time.perf_counter();result,stats=regularize(source,tol,straight,curved,protect);elapsed=time.perf_counter()-start
 assert stats['nodes_after']<=stats['nodes_before'],(name,stats)
 if name in ['wave-zero','disabled','star','tiny','bow-keep']:assert result==source,(name,stats)
 if name=='bow':assert stats['straightened']==1 and stats['curves_fitted']==0 and 'C'not in result,stats
 if name in ['wave','long-wave']:
  assert stats['straightened']>=1 and stats['nodes_after']==8,stats
  paths=list(ET.fromstring(result).iter('{http://www.w3.org/2000/svg}path'));left=dict(segments(paths[0].get('d'),True));right=dict(segments(paths[1].get('d'),True));shared=set(left)&set(right);assert len(shared)==1 and all(left[k]+right[k]==0 for k in shared)
 if name=='curve':assert stats['curves_fitted']>0 and stats['nodes_after']<stats['nodes_before']/2,stats
 if name=='curve':
  path=next(ET.fromstring(result).iter('{http://www.w3.org/2000/svg}path'));cs=[v for v in segments(path.get('d'))if v[0]==1]
  for c in cs:
   ps=[(c[i]/10000,c[i+1]/10000)for i in range(1,len(c),2)]
   for i in range(201):
    t=i/200;u=1-t;xy=[u**3*ps[0][j]+3*u*u*t*ps[1][j]+3*u*t*t*ps[2][j]+t**3*ps[3][j]for j in range(2)]
    assert abs(xy[1]-(10+.018*(xy[0]-10)**2))<.25
 if name=='thin-guard':
  from vector_partition import parse
  before=next(ET.fromstring(source).iter('{http://www.w3.org/2000/svg}path')).get('d');after=next(ET.fromstring(result).iter('{http://www.w3.org/2000/svg}path')).get('d')
  assert abs(parse(after).area)>=abs(parse(before).area)*.8
  assert stats['limited'] and stats['applied_tolerance']<tol,stats
 if name=='junction':
  from boundary_contract import verify
  paths=list(ET.fromstring(result).iter('{http://www.w3.org/2000/svg}path'))
  verify([(i,p.get('d'))for i,p in enumerate(paths)]+[(-1,'M0 0 L0 50 L0 100 L50 100 L100 100 L100 0 L50 0 Z')])
  assert stats['nodes_after']==13,stats
 if name=='nf':
  src_paths=list(ET.fromstring(source).iter('{http://www.w3.org/2000/svg}path'));dst_paths=list(ET.fromstring(result).iter('{http://www.w3.org/2000/svg}path'))
  # Four oval contours and four stars remain geometrically identical.
  original=[v for v in src_paths[-1].get('d').split('M')if v.strip()][-8:];changed=[v for v in dst_paths[-1].get('d').split('M')if v.strip()][-8:]
  assert len(original)==len(changed)==8
  for a,b in zip(original,changed):assert list(segments('M'+a))==list(segments('M'+b))
 assert b'/Subtype /Image' not in pdf_bytes(result)
 (out/(name+'-input.svg')).write_text(source,encoding='utf8');(out/(name+'-native.svg')).write_text(result,encoding='utf8');jobs.append({'name':name,'tolerance':tol,'straight':straight,'curved':curved,'protect':protect,'stats':stats,'seconds':elapsed})
(out/'jobs.json').write_text(json.dumps(jobs,indent=2),encoding='utf8');print(json.dumps(jobs,indent=2))
