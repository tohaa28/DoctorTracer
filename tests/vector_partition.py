"""Actual vector intersection tests, holes, grouping, visible color ownership."""
import sys,random,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
import pathops
from vector_partition import parse,partition,NS
from engine import to_eps

def check(paths,size=100):
    svg=f'<svg xmlns="{NS}" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'+''.join(f'<path fill="{c}" d="{d}"/>' for c,d in paths)+'</svg>'
    result,stats=partition(svg);root=ET.fromstring(result)
    assert len({g.get('fill') for g in root})==len(root)
    assert all(g.tag.endswith('g') and all(p.get('fill')==g.get('fill') for p in g) for g in root)
    visible=[(p.get('fill'),parse(p.get('d'))) for p in root.iter('{'+NS+'}path')]
    for i,(_,a) in enumerate(visible):
        for _,b in visible[:i]:
            intersection=pathops.op(a,b,pathops.PathOp.INTERSECTION)
            assert abs(intersection.area)<.0001,intersection.area
    before=pathops.OpBuilder();after=pathops.OpBuilder()
    for _,d in paths:before.add(parse(d),pathops.PathOp.UNION)
    for _,p in visible:after.add(p,pathops.PathOp.UNION)
    difference=pathops.op(before.resolve(),after.resolve(),pathops.PathOp.XOR)
    assert abs(difference.area)<.001,difference.area
    original=[(c,parse(d)) for c,d in paths]
    rng=random.Random(71)
    for _ in range(2000):
        point=(rng.uniform(0,size),rng.uniform(0,size))
        expected=next((c for c,p in reversed(original) if p.contains(point)),None)
        found=[c for c,p in visible if p.contains(point)]
        assert len(found)<=1 and (found[0] if found else None)==expected,(point,expected,found)
    eps=to_eps(result);assert eps.count('setrgbcolor')==len(visible)
    return stats

cases=[
 [('#ff0000','M0 0L100 0L100 100L0 100Z'),('#0000ff','M20 20L80 20L80 80L20 80Z'),('#ff0000','M30 30L70 30L70 70L30 70Z')],
 [('#333333','M10 10L90 10L90 90L10 90Z M20 20L20 80L80 80L80 20Z'),('#00ff00','M25 25L75 25L75 75L25 75Z')],
 [('#ff0000','M0 50C0 0 100 0 100 50C100 100 0 100 0 50Z'),('#0000ff','M40 0L60 0L60 100L40 100Z')],
 [('#ff0000','M0 0L50 0L50 100L0 100Z'),('#0000ff','M50 0L100 0L100 100L50 100Z')],
]
rng=random.Random(12)
rectangles=[]
for i in range(35):
    x=rng.uniform(0,80);y=rng.uniform(0,80);w=rng.uniform(2,20);h=rng.uniform(2,20)
    rectangles.append((['#ff0000','#0000ff','#00ff00'][i%3],f'M{x} {y}L{x+w} {y}L{x+w} {y+h}L{x} {y+h}Z'))
cases.append(rectangles)
for case in cases:check(case)
check([('#ff0000','M0 0L256 0L256 256L0 256Z'),('#0000ff','M128 20C250 20 250 230 128 230C5 230 5 20 128 20Z')],256)
# The robust integer fallback must also preserve holes/ownership and grouping.
import vector_partition as partition_module
original=partition_module.curve_tile
def fail(*args):raise pathops.PathOpsError('simulated degenerate cubic')
partition_module.curve_tile=fail
check(cases[0]);check(cases[1])
partition_module.curve_tile=original
cleaned=partition_module.clean_polygon_pieces([
    ('#ff0000','M0 0L60 0L60 60L0 60Z'),
    ('#0000ff','M40 40L90 40L90 90L40 90Z')])
assert partition_module.audit_pieces(cleaned)>0
print('PASS: vector intersections, union/holes, color groups, 16000 ownership samples, tile borders, integer fallback, cubic curves, grouped EPS')
