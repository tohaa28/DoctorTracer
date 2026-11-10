"""Checks for the measurement harness, using synthetic test-only references."""
import sys,tempfile,json,unittest,argparse
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'quality'))
import bench

class QualityBench(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=bench.app()
    def test_basic_photo_profile_matches_desktop_defaults(self):
        from refined import Window
        w=Window();w.category='photo';w.wizard_mode='basic';w.preset.setCurrentIndex(1);w.detail.setCurrentIndex(1)
        for count,name,strength in [(0,'photo-medium-auto',200),(9,'photo-medium-9',700)]:
            w.colors.setValue(count);actual=w.config();profile=bench.config(name)
            self.assertEqual(profile['artifact_strength'],actual.get('artifact_strength',0))
            self.assertEqual(profile['curve_tolerance'],actual['curve_tolerance'])
            self.assertEqual(profile['spatial_strength'],actual.get('spatial_strength',strength))
            self.assertEqual(profile['detail'],actual['detail']);self.assertEqual(profile['colors'],actual['colors'])
        w.close()
    def test_identity_and_shift(self):
        a=np.zeros((32,32,4),np.uint8);a[8:24,8:24]=[190,25,60,255]
        same=bench.metrics(a,a);self.assertEqual(same['rgb_mae_white'],0);self.assertEqual(same['boundary_f1_1px'],1);self.assertEqual(same['alpha_iou'],1)
        b=np.roll(a,4,axis=1);m=bench.metrics(a,b);self.assertLess(m['alpha_iou'],1);self.assertGreater(m['rgb_mae_white'],0);self.assertLess(m['boundary_f1_1px'],1)
    def test_hole_and_inherited_transform(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'shape.svg';p.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><g fill="#ff0000" transform="translate(4,4)"><path fill-rule="evenodd" d="M0 0L24 0L24 24L0 24Z M8 8L16 8L16 16L8 16Z"/></g></svg>')
            a=bench.render(p,32,32);self.assertEqual(a[6,6].tolist(),[255,0,0,255]);self.assertEqual(int(a[16,16,3]),0);self.assertEqual(bench.topology(a[:,:,3]),{'components':1,'holes':1})
    def test_wrong_aspect_and_raster_reference(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.svg';p.write_text('<svg viewBox="0 0 20 10"/>')
            with self.assertRaises(ValueError):bench.validate_svg(p,10,10)
            p.write_text('<svg viewBox="0 0 10 10"><image href="picture.png"/></svg>')
            with self.assertRaises(ValueError):bench.validate_svg(p,10,10)
    def test_input_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'input.png').write_bytes(b'original');bench.write(p/'corpus.json',{'profiles':bench.PROFILES,'images':[{'id':'test','path':'input.png','sha256':bench.digest(p/'input.png')}]});bench.load(p)
            (p/'input.png').write_bytes(b'changed')
            with self.assertRaises(ValueError):bench.load(p)
    def test_empty_reference_coverage_fails_strict_gate(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);Image.new('RGBA',(8,8),'red').save(p/'source.png');svg=p/'runs/check/a.svg';svg.parent.mkdir(parents=True);svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><path fill="#ff0000" d="M0 0L8 0L8 8L0 8Z"/></svg>')
            bench.write(p/'corpus.json',{'profiles':bench.PROFILES,'images':[{'id':'sample','path':'source.png','sha256':bench.digest(p/'source.png'),'width':8,'height':8,'category':'logo','split':'holdout'}]})
            bench.write(svg.parent/'run.json',{'rows':[{'image':'sample','profile':'photo-medium-auto','status':'ok','file':'a.svg','svg_sha256':bench.digest(svg)}]})
            args=argparse.Namespace(run='check',baseline=None,name='missing',require_complete=True,regression_mae=.1,regression_iou=.001,regression_boundary=.01)
            with self.assertRaises(SystemExit) as error:bench.compare(args,p)
            self.assertEqual(error.exception.code,2);report=bench.read(p/'reports/missing/report.json');self.assertEqual(report['summary']['verified_reference_cases'],0);self.assertNotIn('mean_rgb_mae_white',report['summary'])
    def test_regression_gate_detects_wrong_colour(self):
        # Synthetic in-memory test oracle, never imported as a real VM reference.
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);Image.new('RGBA',(8,8),'red').save(p/'source.png');sha=bench.digest(p/'source.png')
            bench.write(p/'corpus.json',{'profiles':bench.PROFILES,'images':[{'id':'sample','path':'source.png','sha256':sha,'width':8,'height':8,'category':'logo','split':'holdout'}]})
            cfg=bench.config('photo-medium-auto')
            for name,colour in [('base','#ff0000'),('bad','#0000ff')]:
                svg=p/'runs'/name/'a.svg';svg.parent.mkdir(parents=True);svg.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><path fill="{colour}" d="M0 0L8 0L8 8L0 8Z"/></svg>')
                bench.write(svg.parent/'run.json',{'rows':[{'image':'sample','profile':'photo-medium-auto','source_sha256':sha,'config':cfg,'status':'ok','file':'a.svg','svg_sha256':bench.digest(svg)}]})
            refs=p/'references/photo-medium-auto';refs.mkdir(parents=True);bench.shutil.copy2(p/'runs/base/a.svg',refs/'sample.svg');(refs/'proof.txt').write_text('SYNTHETIC UNIT TEST ONLY')
            bench.write(refs/'sample.json',{'verified':True,'source_sha256':sha,'svg_sha256':bench.digest(refs/'sample.svg'),'evidence':'proof.txt','evidence_sha256':bench.digest(refs/'proof.txt')})
            args=argparse.Namespace(run='bad',baseline='base',name='regression',require_complete=True,regression_mae=.1,regression_iou=.001,regression_boundary=.01)
            with self.assertRaises(SystemExit) as error:bench.compare(args,p)
            self.assertEqual(error.exception.code,2);self.assertEqual(bench.read(p/'reports/regression/report.json')['summary']['regressions'],['sample--photo-medium-auto'])

if __name__=='__main__':unittest.main()
