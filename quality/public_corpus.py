"""Download a pinned, licensed external corpus. Images/VM exports stay under build/."""
import argparse,base64,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
import bench

def github_file(row):
    endpoint=f"repos/{row['repo']}/contents/{row['path']}?ref={row['revision']}"
    raw=subprocess.check_output(['gh','api',endpoint],encoding='utf8')
    entry=json.loads(raw)
    if entry.get('encoding')!='base64':raise ValueError('Unsupported GitHub content response')
    blob=base64.b64decode(entry['content']);sha=hashlib.sha256(blob).hexdigest()
    if row.get('sha256') and row['sha256']!=sha:raise ValueError('Pinned source digest mismatch: '+row['id'])
    git_sha=hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()
    if git_sha!=entry['sha']:raise ValueError('Git blob integrity mismatch')
    return blob,sha

def svg_raster(path,w,h):
    from PySide6.QtCore import QByteArray,QRectF,Qt
    from PySide6.QtGui import QImage,QPainter
    from vector_render import QSvgRenderer
    renderer=QSvgRenderer(QByteArray(Path(path).read_bytes()))
    if not renderer.isValid():raise ValueError('Invalid source SVG')
    image=QImage(w,h,QImage.Format_RGBA8888);image.fill(Qt.transparent);p=QPainter(image)
    try:renderer.render(p,QRectF(0,0,w,h))
    finally:p.end()
    return np.frombuffer(image.bits(),np.uint8).reshape(h,w,4).copy()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--corpus',type=Path,default=ROOT/'build/quality-public-v2')
    parser.add_argument('--manifest',type=Path,default=ROOT/'quality/public_sources.json');args=parser.parse_args()
    folder=args.corpus.resolve();manifest=bench.read(args.manifest)
    if (folder/'corpus.json').exists():raise ValueError('Keep the corpus immutable; choose another directory')
    for name in ['inputs','downloads','references']: (folder/name).mkdir(parents=True,exist_ok=True)
    app=bench.app();rows=[]
    for row in manifest['sources']:
        blob,sha=github_file(row);name=row['id'];ext=Path(row['path']).suffix
        source=folder/'downloads'/(name+ext);source.write_bytes(blob)
        if ext=='.svg':
            bench.validate_svg_source(source)
            image=Image.fromarray(svg_raster(source,768,768)).resize((256,256),Image.Resampling.LANCZOS)
        else:
            with Image.open(source) as im:image=im.convert('RGBA');image.thumbnail((640,640),Image.Resampling.LANCZOS)
        target=folder/'inputs'/(name+'.png');image.save(target);a=np.array(image)
        record={**row,'source_sha256':sha,'path':target.relative_to(folder).as_posix(),'sha256':bench.digest(target),'width':image.width,'height':image.height,
                'origin':'internet-pinned','split':'external-holdout','source_family':row['repo'],'transparent_slot':bool(np.any(a[:,:,3]<255)),
                'transform':'SVG rendered at 768 then Lanczos to 256 RGBA; raster EXIF-independent RGBA, max 640, no upscale',
                'download':source.relative_to(folder).as_posix()}
        if ext=='.svg':record['truth_svg']=record['download']
        rows.append(record);row['sha256']=sha;print(name,image.size,sha,flush=True)
    profiles=['photo-medium-auto','photo-high-auto','photo-medium-9','graphic-medium-9']
    bench.write(folder/'corpus.json',{'schema':2,'created':bench.now(),'generator':'external-public-v2','palette_policy':'ui-total-slots-v2','profiles':bench.PROFILES,'enabled_profiles':profiles,'images':rows})
    bench.write(folder/'source-manifest.json',manifest)
    args.manifest.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    bench.queue(args,folder)
    credits=['# External corpus credits','', 'Each URL and revision is pinned in source-manifest.json. Rasterized derivatives retain the stated source license. No VM exports are relicensed.','']
    credits += [f"- {r['id']}: {r['author']}; {r['license']}; {r['source_url']}; license: {r['license_url']}" for r in rows]
    (folder/'ATTRIBUTION.md').write_text('\n'.join(credits)+'\n',encoding='utf8')
    print('Created external holdout:',len(rows),'images,',len(rows)*len(profiles),'declared cases')

if __name__=='__main__':main()
