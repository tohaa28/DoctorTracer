import sys,json,time,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from post_smooth import smooth
from boundary_contract import segments
out=ROOT/'build/post-smooth';out.mkdir(exist_ok=True)
# All internal interface segments appear twice, in opposite directions.
a='M0 0 L20 0 L20 10 L21 11 L20 12 L21 13 L20 14 L20 40 L0 40 Z'
b='M20 0 L40 0 L40 40 L20 40 L20 14 L21 13 L20 12 L21 11 L20 10 Z'
fixture='<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40"><g id="result"><g fill="#ff0000"><path fill="#ff0000" d="'+a+'"/></g><g fill="#0000ff"><path fill="#0000ff" d="'+b+'"/></g></g></svg>'
square='<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><path fill="#ff0000" d="M10 10 L70 10 L70 70 L10 70 Z"/></svg>'
jobs=[]
for name,source in [('interface',fixture),('square',square)]:
 for strength in [0,35,100]:
  result,stats=smooth(source,strength,True)
  assert (result==source)==(strength==0 or name=='square'),(name,strength,stats)
  root=ET.fromstring(result);paths=list(root.iter('{http://www.w3.org/2000/svg}path'))
  assert [p.get('fill') for p in paths]==[p.get('fill') for p in ET.fromstring(source).iter('{http://www.w3.org/2000/svg}path')]
  if name=='interface':
   edges=[dict(segments(p.get('d'),True)) for p in paths]
   shared=set(edges[0])&set(edges[1]);assert len(shared)>=5
   assert all(edges[0][key]+edges[1][key]==0 for key in shared)
  key=f'{name}-{strength}';(out/(key+'-input.svg')).write_text(source,encoding='utf8');(out/(key+'-native.svg')).write_text(result,encoding='utf8');jobs.append({'name':key,'strength':strength,'stats':stats})
# A tiny hole and a T junction must not move.
hole='<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><path fill="#ff0000" d="M10 10 L70 10 L70 70 L10 70 Z M30 30 L30 33 L33 33 L33 30 Z"/></svg>'
assert smooth(hole,100,True)[0]==hole
junction='<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><path fill="#ff0000" d="M0 0 L20 0 L20 20 L0 20 Z"/><path fill="#0000ff" d="M0 20 L20 20 L20 40 L0 40 Z"/><path fill="#00ff00" d="M20 0 L40 0 L40 40 L20 40 L20 20 Z"/></svg>'
assert smooth(junction,100,False)[0]==junction
private=ROOT/'build/shared-boundary-fix/corrected.svg'
if private.exists():
 source=private.read_text(encoding='utf8');t=time.perf_counter();result,stats=smooth(source,35,True);assert result!=source,stats
 (out/'real-input.svg').write_text(source,encoding='utf8');(out/'real-native.svg').write_text(result,encoding='utf8');jobs.append({'name':'real','strength':35,'stats':stats,'seconds':time.perf_counter()-t})
(out/'jobs.json').write_text(json.dumps(jobs,indent=2),encoding='utf8')
print(json.dumps(jobs,indent=2))
