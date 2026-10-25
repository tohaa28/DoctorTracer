"""PDF colour groups retain disconnected curves and holes without rasterization."""
import sys,re,zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from color_objects import connected_paths,pdf_bytes
from vector_partition import parse
import pathops
for data in [
 'M0 0L100 0L100 100L0 100Z M20 20L20 80L80 80L80 20Z M120 0L140 0L140 20L120 20Z',
 'M0 0L0 100L100 100L100 0Z M20 20L80 20L80 80L20 80Z M120 0L120 20L140 20L140 0Z']:
 parts=connected_paths(data)
 assert len(parts)==2 and sorted(p.count('M') for p in parts)==[1,2]
 assembled=pathops.Path()
 for part in parts:assembled.addPath(parse(part))
 assert abs(pathops.op(assembled,parse(data),pathops.PathOp.XOR).area)<1e-9
 assert assembled.contains((10,10)) and not assembled.contains((50,50)) and assembled.contains((130,10))
svg='<svg xmlns="http://www.w3.org/2000/svg" width="200" height="160"><path fill="#ff0000" d="M10 10L70 10L70 70L10 70Z M90 10L150 10L150 70L90 70Z"/><path fill="#0000ff" d="M20 90L120 90L120 140L20 140Z"/></svg>'
pdf=pdf_bytes(svg)
assert pdf.count(b'/Subtype /Form')==2
assert pdf.count(b'/Group << /S /Transparency /CS /DeviceRGB /I true /K false >>')==2
assert b'/Subtype /Image' not in pdf
streams=[zlib.decompress(s) for s in re.findall(rb'stream\n(.*?)\nendstream',pdf,re.S)]
assert [s.splitlines().count(b'f') for s in streams[:-1]]==[2,1]
assert streams[-1].count(b' Do')==2
print('PDF colour groups: explicit group for singleton, separate curves, preserved holes/winding, pure vector passed')

case='<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><g fill="#FF0000"><path d="M0 0L10 0L10 10Z"/><path fill="#ff0000" d="M20 20L30 20L30 30Z"/></g></svg>'
assert pdf_bytes(case).count(b'/Subtype /Form')==1
print('Equivalent RGB spelling and inherited fill stay in one colour group')
