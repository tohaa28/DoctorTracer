"""Merged tile boundaries, one PDF group per color, large preview paths."""
import sys,re,zlib,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from color_objects import merge_colors,pdf_bytes
from vector_render import QSvgRenderer
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QByteArray,Qt,QRectF
from PySide6.QtGui import QImage,QPainter
import numpy as np
app=QApplication([])
svg='''<svg xmlns="http://www.w3.org/2000/svg" width="256" height="128" viewBox="0 0 256 128"><g fill="#ff0000"><path fill="#ff0000" d="M0 0L128 0L128 128L0 128Z"/><path fill="#ff0000" d="M128 0L256 0L256 128L128 128Z"/></g></svg>'''
merged,count=merge_colors(svg);assert count==1
root=ET.fromstring(merged);data=next(root.iter('{http://www.w3.org/2000/svg}path')).get('d');assert data.count('L')==3
pdf=pdf_bytes(merged);assert pdf.count(b'/Subtype /Form')==1 and b'/Subtype /Image' not in pdf
streams=[zlib.decompress(x) for x in re.findall(rb'stream\n(.*?)\nendstream',pdf,re.S)]
assert sum(s.splitlines().count(b'f') for s in streams)==1
im=QImage(256,128,QImage.Format_RGBA8888);im.fill(Qt.transparent);p=QPainter(im)
QSvgRenderer(QByteArray(merged.encode())).render(p,QRectF(0,0,256,128));p.end()
a=np.frombuffer(im.bits(),np.uint8).reshape(128,256,4)
assert np.all(a[:,:,3]==255) and np.all(a[:,:,0]==255)
# Many subpaths in a single color object must not hit the native SVG parser cap.
paths=' '.join(f'M{x} {y}L{x+1} {y}L{x+1} {y+1}L{x} {y+1}Z' for y in range(0,128,2) for x in range(0,256,2))
large=f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="128" viewBox="0 0 256 128" data-color-objects="merged"><path fill="#ff0000" d="{paths}"/></svg>'
im.fill(Qt.transparent);p=QPainter(im);QSvgRenderer(QByteArray(large.encode())).render(p,QRectF(0,0,256,128));p.end()
assert np.count_nonzero(np.frombuffer(im.bits(),np.uint8).reshape(128,256,4)[:,:,3])==8192
print('PASS: tile cuts merged, one PDF color group, pure vector PDF, large color preview')
