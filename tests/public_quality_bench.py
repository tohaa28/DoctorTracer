"""External corpus integrity, palette semantics and colour-independent geometry."""
import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'quality'),str(ROOT/'desktop')]
import bench
from geometry_metrics import compare_labels,palette_distance,region_topology
app=bench.app()
class PublicQuality(unittest.TestCase):
 def test_palette_total_transparency(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);Image.new('RGBA',(12,12),(20,40,60,255)).save(folder/'a.png');image={'path':'a.png','transparent_slot':True}
   with patch('engine.find_palette',return_value=[[20,40,60]]) as find:
    cfg=bench.case_config('photo-medium-9',image,folder,{'palette_policy':'ui-total-slots-v2'});self.assertEqual(find.call_args.args[1],8);self.assertEqual(cfg['palette'],['#14283c'])
   self.assertNotIn('palette',bench.case_config('photo-medium-9',image,folder,{'schema':1}))
 def test_recolour_does_not_move_geometry(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'a.svg';b=Path(d)/'b.svg';svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><path fill="COLOR" d="M4 4L28 4L28 28L4 28Z"/></svg>'
   a.write_text(svg.replace('COLOR','#ff0000'));b.write_text(svg.replace('COLOR','#00ff00'))
   m=compare_labels(bench.render(a,32,32,labels=True),bench.render(b,32,32,labels=True));self.assertEqual(m['region_boundary_f1_1px'],1);self.assertEqual(m['boundary_p95_distance_px'],0)
   self.assertGreater(palette_distance(['#ff0000'],['#00ff00'])['symmetric_nearest_deltaE76'],1)
 def test_internal_hole_visible_in_colour_topology(self):
  a=np.zeros((24,24),np.int32);a[3:21,3:21]=1;a[8:16,8:16]=0
  self.assertEqual(bench.topology(np.full((24,24),255,np.uint8))['holes'],0)
  self.assertEqual(region_topology(a)['holes'],2) # one enclosed hole in each colour's mask
  b=a.copy();b[8:16,8:16]=1;self.assertLess(compare_labels(a,b)['region_boundary_f1_1px'],1)
 def test_pinned_download_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'a.png').write_bytes(b'input');(p/'a.svg').write_bytes(b'source');bench.write(p/'corpus.json',{'profiles':bench.PROFILES,'images':[{'id':'a','path':'a.png','sha256':bench.digest(p/'a.png'),'download':'a.svg','source_sha256':bench.digest(p/'a.svg')}]});bench.load(p)
   (p/'a.svg').write_bytes(b'changed')
   with self.assertRaises(ValueError):bench.load(p)
 def test_external_svg_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bad.svg';p.write_text('<svg><use href="https://example.invalid/a.svg"/></svg>')
   with self.assertRaises(ValueError):bench.validate_svg_source(p)
if __name__=='__main__':unittest.main()
