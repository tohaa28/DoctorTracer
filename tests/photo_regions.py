"""Exercise the actual photo pipeline and its CPU/GPU/export contracts."""
import sys,tempfile,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication
from engine import trace
from color_objects import pdf_bytes
app=QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory() as folder:
    y,x=np.indices((60,80));a=np.zeros((60,80,4),np.uint8)
    a[:,:,:3]=np.stack([x*3,y*4,(x+y)*255//138],2);a[:,:,3]=255
    a[20:35,25:45,3]=0
    path=Path(folder)/'input.png';Image.fromarray(a).save(path)
    cfg={'category':'photo','detail':1,'photo_regions':True,'photo_spatial':True,'speckle':2}
    cpu,cs=trace(path,{**cfg,'compute':'cpu'});gpu,gs=trace(path,{**cfg,'compute':'gpu'})
    assert cpu==gpu
    assert cs['backend']=='shared photographic regions' and cs['geometry_verified']
    assert cs['geometry_audit']['max_intersection_area_px2']<=.0001
    root=ET.fromstring(cpu);colors=[g.get('fill') for g in root]
    assert len(colors)==len(set(colors))
    assert all(len(g)==1 for g in root)
    pdf=pdf_bytes(cpu)
    assert b'/Subtype /Image' not in pdf and pdf.count(b'/Subtype /Form')==len(colors)
    again,stats=trace(path,{**cfg,'compute':'gpu'})
    assert again==gpu and stats['palette_cache_hit']
    changed,_=trace(path,{**cfg,'compute':'gpu','curve_tolerance':.06})
    assert changed!=gpu
    Image.new('RGBA',(17,13),(90,80,70,0)).save(path)
    empty,stats=trace(path,{**cfg,'compute':'gpu'})
    assert stats['colors']==0 and stats['geometry_verified']
    assert len(ET.fromstring(empty))==0
print('Photo pipeline: CPU/GPU identical, disjoint groups, vector PDF, cache identity and smoothing control passed')
