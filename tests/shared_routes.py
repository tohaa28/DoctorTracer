"""Old preset flags cannot restore independent mask tracing."""
import sys
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from engine import trace
out=ROOT/'build/shared-routes';out.mkdir(exist_ok=True)
im=Image.new('RGBA',(64,48),'white');d=ImageDraw.Draw(im);d.ellipse((8,6,50,42),fill='#dc2020');d.rectangle((30,20,57,38),fill='black');path=out/'source.png';im.save(path)
for category in ['photo','aa']:
 for mode in ['spline','none']:
  svg,stats=trace(path,{'category':category,'mode':mode,'colors':3,'compute':'cpu','backend':'vtracer','photo_regions':False})
  assert 'data-boundary-contract="paired"' in svg,(category,mode)
  assert stats['geometry_verified'],(category,mode)
print('PASS: four legacy/category/mode routes retain the shared boundary contract')
