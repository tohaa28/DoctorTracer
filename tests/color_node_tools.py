import sys,json,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'desktop'))
from color_node_tools import intermediate,reduce_nodes
from boundary_contract import segments
from color_objects import pdf_bytes
fixtures=json.loads((root/'tests/color_node_cases.json').read_text())
def svg(paths):
    return '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><g id="image">'+''.join('<g fill="'+c+'"><path fill="'+c+'" d="'+d+'"/></g>' for c,d in paths)+'</g></svg>'
def paths(svg):return list(ET.fromstring(svg).iter('{http://www.w3.org/2000/svg}path'))
source=svg(fixtures['strip'])
assert intermediate(source,0)[0]==source
assert intermediate(source,1)[0]==source
clean,s=intermediate(source,100)
assert s['removed_elements']==1,s
assert len(paths(clean))==2
assert intermediate(clean,100)[0]==clean
assert intermediate(source.replace('#800080','#00ff00'),100)[0]==source.replace('#800080','#00ff00')
island=svg(fixtures['island']);assert intermediate(island,100)[0]==island
circle=svg(fixtures['circle']);assert reduce_nodes(circle,0)[0]==circle
reduced,s=reduce_nodes(circle,100)
assert s['nodes_after']<s['nodes_before'],s
p=paths(reduced);assert len(p)==2 and 'C' in p[1].get('d')
a=dict(segments(p[0].get('d'),True));b=dict(segments(p[1].get('d'),True))
assert b and set(b)<=set(a) and all(a[k]+b[k]==0 for k in b)
assert b'/Subtype /Image' not in pdf_bytes(reduced)
assert reduce_nodes(circle,100)[0]==reduced
print('PASS native DLL intermediate colors and paired node reduction:',s)

fringes=json.loads((root/'tests/fringe_cases.json').read_text())
for key in ('annulus','crescent'):
    source=svg(fringes[key])
    assert intermediate(source,0)[0]==source
    assert intermediate(source,20)[0]==source
    cleaned,s=intermediate(source,100)
    assert s['removed_elements']==1,(key,s)
    assert len(paths(cleaned))==2,key
    gold_before=next(p for p in paths(source) if p.get('fill')=='#d39f50')
    gold_after=next(p for p in paths(cleaned) if p.get('fill')=='#d39f50')
    assert sorted(segments(gold_before.get('d'),True))==sorted(segments(gold_after.get('d'),True)),key
    assert intermediate(cleaned,100)[0]==cleaned
for key in ('wide','unrelated','alpha'):
    source=svg(fringes[key]);assert intermediate(source,100)[0]==source,key
print('PASS native curved and ring gray fringe, preserve authentic colors and transparency')
