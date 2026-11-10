"""Spatial audit agrees with the full independent audit, including holes/slivers."""
import sys,json,subprocess,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'desktop'),str(ROOT/'quality')]
import bench
from vector_partition import audit_global,polygon_data
from audit_tiles import audit
out=ROOT/'build/audit-tiles';out.mkdir(exist_ok=True);cases=[]
def rect(x,y,w,h,reverse=False):
    points=[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
    if reverse:points.reverse()
    return 'M'+' L'.join(f'{x:.7f} {y:.7f}' for x,y in points)+' Z '
def outcome(pieces,tiled):
    report={}
    try:
        (audit([polygon_data(d) for c,d in pieces],report) if tiled else audit_global(pieces,report))
        return True,report
    except ValueError:return False,{}
for count in [1,16,100,101]:
    holes=[rect((124 if count==101 else 4)+(i%10)*48,(124 if count==101 else 4)+(i//10)*48,12,12,True) for i in range(count)]
    islands=[rect((124 if count==101 else 4)+(i%10)*48,(124 if count==101 else 4)+(i//10)*48,12,12) for i in range(count)]
    for offset in [0,.000005,.00002,.01]:
        pieces=[('#ffffff',rect(0,0,512,512)+''.join(holes)),('#000000',''.join(islands)+rect((124 if count==101 else 4)-offset,(124 if count==101 else 4),offset,12) if offset else ''.join(islands))]
        a,ar=outcome(pieces,False);b,br=outcome(pieces,True);assert a==b,(count,offset,a,b)
        svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'+''.join(f'<g fill="{c}"><path fill="{c}" d="{d}"/></g>' for c,d in pieces)+'</svg>'
        name=f'case-{len(cases)}';(out/(name+'.svg')).write_text(svg,encoding='utf-8');cases.append({'file':name+'.svg','accepted':a})
bench.write(out/'cases.json',cases)
subprocess.run(['node','tests/audit_tiles.mjs',str(out/'cases.json')],cwd=ROOT,check=True)
print(json.dumps({'ok':True,'cases':len(cases),'full_vs_tiled':True}))
