"""Photo detail and shared fixed-palette ownership, no proprietary reference needed."""
import sys,tempfile,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'desktop'),str(ROOT/'quality')]
import bench
from engine import trace,segment
from vector_partition import audit_pieces
from color_objects import pdf_bytes
import xml.etree.ElementTree as ET
app=bench.app()
with tempfile.TemporaryDirectory() as folder:
    folder=Path(folder);a=np.full((64,96,4),255,np.uint8);a[30,8:88,:3]=[20,40,60]
    p=folder/'stroke.png';Image.fromarray(a).save(p)
    cfg={'category':'photo','detail':1,'photo_regions':True,'photo_spatial':True,'colors':2,'palette':['#ffffff','#14283c'],'speckle':2,'compute':'cpu','curve_tolerance':.24}
    _,labels,_,_=segment(p,cfg)
    assert np.count_nonzero(labels[30,8:88]==1)>=70,'Default cleanup erased a continuous thin stroke'
    svg,stats=trace(p,cfg);assert 'data-shared-boundaries="true"'in svg
    out=folder/'out.svg';out.write_text(svg,encoding='utf8');v=bench.render(out,96,64)
    assert np.count_nonzero(v[30,:,0]<180)>=60,'Shared curves erased thin stroke'
    assert np.min(v[4:-4,4:-4,3])==255,'Opaque partition has a transparent gap'
    audit={};doc=ET.fromstring(svg);audit_pieces([(q.get('fill'),q.get('d'))for q in doc.iter('{http://www.w3.org/2000/svg}path')],audit)
    assert audit['max_intersection_area_px2']<=.0001
    assert b'/Group' in pdf_bytes(svg)
    from fixtures import generate
    generate(folder/'fixtures');detail=np.array(Image.open(folder/'fixtures/thin-lines-02.png').convert('RGBA'));(folder/'detail.rgba').write_bytes(detail.tobytes())
    (folder/'input.rgba').write_bytes(a.tobytes());(folder/'test.json').write_text(json.dumps({'folder':str(folder),'config':cfg}))
    subprocess.run(['node',str(ROOT/'tests/photo_detail.mjs'),str(folder/'test.json')],cwd=ROOT,check=True)
print('Photo detail: CPU/WASM preserve thin strokes, no opaque gaps, fixed shared boundaries and PDF groups passed')
