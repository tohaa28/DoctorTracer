"""Windows must also dissolve computational tile seams, including holes."""
import sys,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from vector_partition import partition,NS,polygon_data
import pyclipper
for hole in [False,True]:
    d='M16 16 L496 16 L496 496 L16 496 Z'
    if hole:d+=' M96 96 L96 416 L416 416 L416 96 Z'
    svg=f'<svg xmlns="{NS}" width="512" height="512" viewBox="0 0 512 512"><path fill="#ff0000" d="{d}"/></svg>'
    out,stats=partition(svg);paths=list(ET.fromstring(out).iter('{'+NS+'}path'))
    assert len(paths)==1 and paths[0].get('d').count('M')==(2 if hole else 1)
    rings=polygon_data(paths[0].get('d'));area=abs(sum(pyclipper.Area(p) for p in rings))/1e14
    assert abs(area-(480*480-(320*320 if hole else 0)))<.0001
    assert all(x not in (1280000000,2560000000,3840000000) and y not in (1280000000,2560000000,3840000000) for p in rings for x,y in p)
print('PASS: Windows tile cuts dissolved, exact area, holes preserved')
