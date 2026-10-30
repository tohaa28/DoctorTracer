"""A native boolean worker crash must recover audited, disjoint geometry."""
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from vector_partition import parse, parallel_tiles, audit_global

class FailedWorker:
    returncode=1
    def communicate(self,timeout=None):return b'',b'Injected native worker failure'
    def poll(self):return 1

items=[('#ff0000',parse('M0 0 L200 0 L200 80 L0 80 Z')),
       ('#0000ff',parse('M40 20 L180 20 L180 60 L40 60 Z'))]
jobs=[([0,1],(0,0,128,128)),([0,1],(128,0,256,128))]
with patch('vector_partition.subprocess.Popen',side_effect=lambda *a,**k:FailedWorker()):
    result=parallel_tiles(items,jobs,2)
assert all(fallback for pieces,fallback in result)
pieces=[p for group,_ in result for p in group]
report={};audit_global(pieces,report)
assert report['max_intersection_area_px2']==0,report
assert {color for color,data in pieces}=={'#ff0000','#0000ff'}
print('PASS: native worker crash recovery, colors retained, no intersections')
