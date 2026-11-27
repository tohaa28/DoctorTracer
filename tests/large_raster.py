import sys,tempfile,subprocess
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'desktop'))
from input_raster import open_raster,validate_input_file,MAX_INPUT_BYTES
from engine import load_source,trace
import xml.etree.ElementTree as ET
with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp)
    sparse=tmp/'size.bin'
    with sparse.open('wb') as handle:handle.truncate(MAX_INPUT_BYTES)
    assert validate_input_file(sparse)==150_000_000
    with sparse.open('ab') as handle:handle.write(b'x')
    try:validate_input_file(sparse)
    except ValueError:pass
    else:raise AssertionError('oversized file accepted')
    path=tmp/'native.tif'
    subprocess.run([sys.executable,str(root/'tests/large_raster_fixture.py'),str(path)],check=True)
    im=open_raster(path);assert im.size==(5130,1685);assert im.info['dpi']==(300,300)
    assert im.getpixel((50,50))==(255,0,0,255) and im.getpixel((300,300))[3]==0
    a,size=load_source(path,{'max_size':2400,'category':'hard'})
    assert size==(5130,1685) and a.shape==(1685,5130,4)
    svg,stats=trace(path,{'category':'hard','mode':'polygon','colors':4,'palette':['#ff0000','#00ff00','#0000ff','#000000'],'detail':2,'compute':'cpu','speckle':0})
    assert stats['working_size']==[5130,1685],stats
    doc=ET.fromstring(svg);assert doc.get('width')=='5130' and doc.get('height')=='1685'
    assert stats['colors']==4,stats
    print('PASS full-size CMYKA TIFF Windows trace, 4 colors, 5130x1685, 150MB boundary',stats['working_size'])
