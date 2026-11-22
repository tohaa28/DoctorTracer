"""Conditional diagnostic using VM's observed RGB palette; not an independent score."""
import argparse,json,subprocess,time
from pathlib import Path
import numpy as np
from PIL import Image
import bench

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--corpus',type=Path,required=True)
    parser.add_argument('--name',default='palette-diagnostic');parser.add_argument('--profile',default='photo-medium-9');args=parser.parse_args()
    folder=args.corpus.resolve();data=bench.load(folder);out=folder/'diagnostics'/bench.safe(args.name)
    if out.exists():raise ValueError('Keep diagnostics immutable; choose a new name')
    out.mkdir(parents=True);app=bench.app();rows=[];jobs=[]
    from engine import trace
    from PySide6.QtGui import QColor
    for image in data['images']:
        if image['category']!='photo':continue
        name=image['id'];reference=folder/'references'/args.profile/(name+'.svg');receipt=bench.read(reference.with_suffix('.json'))
        if not receipt['verified'] or receipt['svg_sha256']!=bench.digest(reference):raise ValueError('Unverified reference')
        palette=[]
        for fill in bench.inventory(reference)['observed_fills']:
            color=QColor(fill)
            if not color.isValid():raise ValueError('Unknown VM palette format')
            palette.append(color.name())
        cfg=bench.case_config(args.profile,image,folder,data);cfg['palette']=list(dict.fromkeys(palette))
        with Image.open(folder/image['path']) as im:rgba=np.array(im.convert('RGBA'))
        raw=out/(name+'.rgba');raw.write_bytes(rgba.tobytes());jobs.append({'id':name,'source':raw.name,'output':name+'-wasm.svg','w':image['width'],'h':image['height'],'config':cfg})
        started=time.perf_counter();svg,stats=trace(folder/image['path'],cfg);p=out/(name+'-desktop.svg');p.write_text(svg,encoding='utf8')
        rows.append({'image':name,'source_sha256':image['sha256'],'reference_sha256':receipt['svg_sha256'],'palette_from_reference':True,'palette':cfg['palette'],'config':cfg,'desktop_seconds':time.perf_counter()-started})
    bench.write(out/'wasm-jobs.json',jobs)
    subprocess.run(['node',str(bench.ROOT/'quality/run_wasm.mjs'),str(out/'wasm-jobs.json')],cwd=bench.ROOT,check=True)
    for row in rows:
        image=next(i for i in data['images'] if i['id']==row['image']);reference=bench.render(folder/'references'/args.profile/(image['id']+'.svg'),image['width'],image['height'])
        for engine in ['desktop','wasm']:
            main=folder/'runs'/(engine+'-public-v2')/(image['id']+'--'+args.profile+'.svg')
            if not main.exists():raise ValueError('Run the independent public-v2 baseline first')
            before=bench.metrics(reference,bench.render(main,image['width'],image['height']))
            after=bench.metrics(reference,bench.render(out/(image['id']+'-'+engine+'.svg'),image['width'],image['height']))
            row[engine]={'independent_rgb_mae':before['rgb_mae_white'],'vm_palette_rgb_mae':after['rgb_mae_white'],'delta_mae':after['rgb_mae_white']-before['rgb_mae_white']}
    bench.write(out/'diagnostic.json',{'notice':'Oracle palette is taken from the VM export. Diagnostic only: exclude from independent quality aggregates. RGB only, not opacity matching.','rows':rows})
    print(json.dumps({'notice':'Conditional VM-palette diagnostic, not independent quality','rows':[{k:v for k,v in r.items() if k in ['image','desktop','wasm']} for r in rows]},indent=2))

if __name__=='__main__':main()
