"""Interleaved warm before/after timings; assert byte-identical SVG, never publish inputs.

python scripts/bench_gpu_contours.py --image sample.png --repeats 3
Baseline geometry is loaded from the last palette release, not approximated.
"""
import argparse,importlib.util,json,os,statistics,subprocess,sys
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication
import shared_regions,boundary_smoothing,photo_regions
from engine import trace,find_palette

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',action='append',required=True)
    parser.add_argument('--browser-cases',action='store_true');parser.add_argument('--repeats',type=int,default=3);parser.add_argument('--baseline',default='02373c0')
    args=parser.parse_args();app=QApplication.instance() or QApplication([])
    folder=ROOT/'build/gpu-contours';folder.mkdir(parents=True,exist_ok=True)
    def baseline(name):
        data=subprocess.check_output(['git','show',args.baseline+':desktop/'+name+'.py'],cwd=ROOT)
        path=folder/('baseline-'+name+'.py');path.write_bytes(data)
        spec=importlib.util.spec_from_file_location('baseline_'+name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    old_shared=baseline('shared_regions');old_smoothing=baseline('boundary_smoothing');original=old_shared.trace
    def compatible(*a,**k):k.pop('compute',None);return original(*a,**k)
    old_shared.trace=compatible
    rows=[];browser_cases=[]
    try:
        for image_id,path in enumerate(args.image):
            with Image.open(path) as im:
                im=im.convert('RGBA');im.thumbnail((2400,2400));a=np.array(im);width,height=im.size
            if args.browser_cases:(folder/f'input-{image_id}.rgba').write_bytes(a.tobytes())
            for mode in ['fixed','unlimited']:
                config={'category':'photo','detail':1,'colors':0,'photo_regions':True,'photo_spatial':True,'compute':'gpu','speckle':2,'curve_tolerance':.24}
                if mode=='fixed':
                    config['colors']=9;config['palette']=['#%02x%02x%02x'%tuple(c) for c in find_palette(a,9-int(np.any(a[:,:,3]<128)))]
                if args.browser_cases:
                    browser_cases.append({'id':len(browser_cases),'width':width,'height':height,'rgba':f'input-{image_id}.rgba','config':config});(folder/'browser-cases.json').write_text(json.dumps(browser_cases),encoding='utf8')
                samples={k:[] for k in ['before','after']};boundary={k:[] for k in samples};chains=[];reference=None
                # Warm both implementations, device compilation and palette cache before timing.
                order=['before','after']+[k for i in range(args.repeats) for k in (['before','after'] if i%2==0 else ['after','before'])]
                for iteration,kind in enumerate(order):
                    photo_regions.shared_regions=old_shared if kind=='before' else shared_regions
                    sys.modules['boundary_smoothing']=old_smoothing if kind=='before' else boundary_smoothing
                    svg,stats=trace(path,config)
                    if reference is None:reference=svg
                    assert svg==reference,(image_id,mode,kind,'SVG changed')
                    if iteration>=2:samples[kind].append(stats['seconds']);boundary[kind].append(stats['shared_boundary_seconds'])
                    if kind=='after':
                        assert stats.get('contour_compute')=='OpenCL GPU FP64',stats
                        after=stats
                medians={k:statistics.median(v) for k,v in samples.items()}
                row={'image_id':image_id,'mode':mode,'samples_seconds':samples,'median_seconds':medians,'speedup':medians['before']/medians['after'],'boundary_samples':boundary,'svg_byte_identical':True,'audit':after['geometry_audit'],'device':after.get('device'),'contour_compute':after['contour_compute'],'curve_compute':after.get('curve_compute')}
                rows.append(row);(folder/'warm-benchmark.json').write_text(json.dumps(rows,indent=2),encoding='utf8');print(json.dumps(row),flush=True)
    finally:photo_regions.shared_regions=shared_regions;sys.modules['boundary_smoothing']=boundary_smoothing

if __name__=='__main__':main()
