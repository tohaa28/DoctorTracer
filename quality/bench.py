"""Offline quality corpus, immutable reference receipts, runs and visual reports.

All images and reports default to ignored build/quality. See quality/README.md.
"""
import argparse, datetime, hashlib, html, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'desktop'))
sys.path.insert(0,str(Path(__file__).parent))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from fixtures import generate

PROFILES={
 'photo-medium-auto':{'category':'photo','detail':1,'colors':0},
 'photo-high-auto':{'category':'photo','detail':2,'colors':0},
 'photo-medium-9':{'category':'photo','detail':1,'colors':9},
 'graphic-medium-9':{'category':'aa','detail':1,'colors':9},
 'hard-medium-2':{'category':'hard','detail':1,'colors':2},
}

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def safe(value):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',value):raise ValueError('Use ASCII letters, digits, _ or - for identifiers')
    return value
def load(folder):
    data=read(folder/'corpus.json')
    if data['profiles']!=PROFILES:raise ValueError('Profile definitions changed; create a versioned corpus')
    for row in data['images']:
        if digest(folder/row['path'])!=row['sha256']:raise ValueError('Input changed: '+row['id'])
    return data
def select(rows,ids):
    wanted=set(ids.split(',')) if ids else None
    result=[r for r in rows if wanted is None or r['id'] in wanted]
    if wanted and wanted-{r['id'] for r in result}:raise ValueError('Unknown image IDs')
    return result
def config(profile):
    return {**PROFILES[profile],'compute':'cpu','mode':'spline','photo_regions':True,'photo_spatial':True,
      'speckle':2,'artifact_strength':0,'segmentation_complexity':5,'spatial_iterations':2,
      'curve_tolerance':.12*[4,2,1][PROFILES[profile]['detail']],
      'spatial_strength':200 if PROFILES[profile]['category']=='photo' and not PROFILES[profile]['colors'] else 700,'flatten':False,'alphamax':1.,'max_size':2400}
def svg_size(path):
    doc=ET.parse(path).getroot()
    if doc.get('viewBox'):return tuple(map(float,doc.get('viewBox').replace(',',' ').split()))[2:]
    def unit(s):
        m=re.fullmatch(r'\s*([\d.eE+-]+)(px|pt|mm|cm|in)?\s*',s or '')
        if not m:raise ValueError('SVG requires a numeric viewBox or dimensions')
        return float(m[1])*{'px':1,'pt':96/72,'mm':96/25.4,'cm':96/2.54,'in':96,None:1}[m[2]]
    return unit(doc.get('width')),unit(doc.get('height'))
def validate_svg(path,width,height):
    doc=ET.parse(path).getroot()
    for el in doc.iter():
        if el.tag.split('}')[-1] in ['image','script','foreignObject']:raise ValueError('Reference must be vector-only SVG')
        for key,val in el.attrib.items():
            if key.split('}')[-1]=='href' and not val.startswith('#'):raise ValueError('External SVG resource is forbidden')
    w,h=svg_size(path)
    if min(w,h)<=0 or abs(w/h-width/height)>.001:raise ValueError('SVG aspect ratio differs from source')

def init(args,folder):
    if (folder/'corpus.json').exists():raise ValueError('Corpus exists; use a new directory or add-image')
    images=generate(folder/'inputs')
    for row in images:row['sha256']=digest(folder/row['path'])
    write(folder/'corpus.json',{'schema':1,'created':now(),'generator':'fixtures-v1','profiles':PROFILES,'images':images})
    (folder/'references').mkdir(exist_ok=True)
    queue(args,folder)
    print('Created',len(images),'original synthetic cases; no Vector Magic references fabricated.')

def add_image(args,folder):
    data=load(folder);name=safe(args.id)
    if any(r['id']==name for r in data['images']):raise ValueError('Image ID already exists')
    source=Path(args.input);target=folder/'inputs'/(name+source.suffix.lower());shutil.copy2(source,target)
    with Image.open(target) as im:w,h=im.size
    data['images'].append({'id':name,'path':target.relative_to(folder).as_posix(),'sha256':digest(target),'width':w,'height':h,'category':args.category,'origin':'private-local','split':args.split})
    write(folder/'corpus.json',data);queue(args,folder)

def queue(args,folder):
    data=load(folder);items=[]
    for row in data['images']:
        for profile in PROFILES:
            p=folder/'references'/profile/(row['id']+'.json')
            receipt=read(p) if p.exists() else {}
            items.append({'image':row['id'],'profile':profile,'source_sha256':row['sha256'],
              'settings':PROFILES[profile],'transparency':'preserve','wizard':receipt.get('wizard','basic'),
              'palette_policy':'per-program automatic selection; same count is not identical RGB',
              'status':'ready' if receipt.get('verified') else 'missing-or-unverified'})
    write(folder/'reference-queue.json',items)

def register(args,folder):
    data=load(folder);row=select(data['images'],args.id)[0];profile=args.profile
    target=folder/'references'/profile/(row['id']+'.svg');receipt=target.with_suffix('.json')
    if target.exists() or receipt.exists():raise ValueError('Reference exists; keep it immutable and use a new corpus for replacement')
    source=Path(args.svg);validate_svg(source,row['width'],row['height'])
    evidence=Path(args.evidence)
    if not evidence.is_file():raise ValueError('Capture evidence file is required')
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    proof=target.with_name(row['id']+'-evidence'+evidence.suffix);shutil.copy2(evidence,proof)
    write(receipt,{'schema':1,'image':row['id'],'profile':profile,'source_sha256':row['sha256'],
      'svg_sha256':digest(target),'program':'Vector Magic Desktop','version':args.version,'captured':now(),
      'verified':args.verified,'settings':PROFILES[profile],'wizard':args.wizard,'transparency':'preserve',
      'palette_policy':'per-program automatic selection','evidence':proof.name,'evidence_sha256':digest(proof),
      'notes':args.notes})
    queue(args,folder);print('Reference registered:',row['id'],profile,'verified=',args.verified)

def import_batch(args,folder):
    images=select(load(folder)['images'],args.ids)
    # Preflight the entire selection before committing immutable receipts.
    for row in images:
        source=Path(args.directory)/(row['id']+'.svg')
        validate_svg(source,row['width'],row['height'])
        if (folder/'references'/args.profile/(row['id']+'.svg')).exists():raise ValueError('Reference already exists: '+row['id'])
    for row in images:
        single=argparse.Namespace(**vars(args));single.id=row['id'];single.svg=str(Path(args.directory)/(row['id']+'.svg'))
        register(single,folder)

def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])

def render(path,w,h):
    # Same independent painter for both programs: bypass Qt SVG parser path-size limits.
    # Supported measured export dialect: M/L/C/Z, inherited fills/opacities and transforms.
    from photo_curves import qpath
    from PySide6.QtGui import QImage,QPainter,QColor,QTransform
    from PySide6.QtCore import Qt
    doc=ET.parse(path).getroot();vw,vh=svg_size(path)
    vb=list(map(float,doc.get('viewBox',f'0 0 {vw} {vh}').replace(',',' ').split()))
    samples=3;image=QImage(w*samples,h*samples,QImage.Format_RGBA8888);image.fill(Qt.transparent);p=QPainter(image)
    p.scale(w*samples/vb[2],h*samples/vb[3]);p.translate(-vb[0],-vb[1]);p.setPen(Qt.NoPen)
    def paint(el,inherited):
        tag=el.tag.split('}')[-1]
        if tag in ['defs','metadata','title','desc']:return
        attrs=dict(inherited);attrs.update(el.attrib)
        for decl in el.get('style','').split(';'):
            if ':' in decl:
                k,v=decl.split(':',1);attrs[k.strip()]=v.strip()
        if any(k in attrs for k in ['clip-path','mask','filter']):raise ValueError('Unsupported SVG effect in measurement')
        p.save()
        for name,values in re.findall(r'([A-Za-z]+)\s*\(([^)]*)\)',el.get('transform','')):
            v=list(map(float,re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?',values)))
            if name=='translate':p.translate(v[0],v[1] if len(v)>1 else 0)
            elif name=='scale':p.scale(v[0],v[1] if len(v)>1 else v[0])
            elif name=='matrix' and len(v)==6:p.setWorldTransform(QTransform(*v),True)
            else:raise ValueError('Unsupported SVG transform: '+name)
        p.setOpacity(p.opacity()*float(el.get('opacity',1)))
        if tag=='path':
            d=el.get('d','');commands=set(re.findall('[A-Za-z]',re.sub(r'[eE][-+]?\d+','',d)))
            if commands-set('MLCZz'):raise ValueError('Unsupported SVG commands: '+str(commands))
            shape=qpath(d);shape.setFillRule(Qt.OddEvenFill if attrs.get('fill-rule')=='evenodd' else Qt.WindingFill)
            colour=QColor(attrs.get('fill','#000'))
            if attrs.get('fill')!='none' and not colour.isValid():raise ValueError('Unsupported SVG fill')
            colour.setAlphaF(colour.alphaF()*float(attrs.get('fill-opacity',1)))
            if attrs.get('fill')!='none':p.setBrush(colour);p.drawPath(shape)
        elif tag not in ['svg','g']:raise ValueError('Unsupported vector element: '+tag)
        child_attrs={k:v for k,v in attrs.items() if k not in ['opacity','transform']}
        for child in el:paint(child,child_attrs)
        p.restore()
    try:paint(doc,{})
    finally:p.end()
    image=image.scaled(w,h,Qt.IgnoreAspectRatio,Qt.SmoothTransformation)
    return np.frombuffer(image.bits(),np.uint8).reshape(h,w,4).copy()

def topology(alpha):
    import cv2
    mask=(alpha>=128).astype(np.uint8)
    n,_=cv2.connectedComponents(mask,connectivity=8)
    contours,hierarchy=cv2.findContours(mask,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    return {'components':n-1,'holes':0 if hierarchy is None else int(sum(row[3]>=0 for row in hierarchy[0]))}

def metrics(a,b):
    import cv2
    af=a.astype(float);bf=b.astype(float);result={}
    for name,bg in [('white',255),('dark',40)]:
        ac=af[:,:,:3]*af[:,:,3:4]/255+bg*(1-af[:,:,3:4]/255)
        bc=bf[:,:,:3]*bf[:,:,3:4]/255+bg*(1-bf[:,:,3:4]/255)
        result['rgb_mae_'+name]=float(np.abs(ac-bc).mean())
    result['alpha_mae']=float(np.abs(af[:,:,3]-bf[:,:,3]).mean())
    am=a[:,:,3]>=128;bm=b[:,:,3]>=128;union=np.count_nonzero(am|bm)
    result['alpha_iou']=float(np.count_nonzero(am&bm)/union) if union else 1.
    # Canny on white composite sees colour-region boundaries as well as silhouette.
    def edges(x):
        c=x[:,:,:3].astype(float)*x[:,:,3:4]/255+255*(1-x[:,:,3:4]/255)
        return cv2.Canny(cv2.cvtColor(np.round(c).astype(np.uint8),cv2.COLOR_RGB2GRAY),40,100)>0
    ae,be=edges(a),edges(b);kernel=np.ones((3,3),np.uint8)
    def score(x,y):
        return float(np.count_nonzero(x&(cv2.dilate(y.astype(np.uint8),kernel)>0))/np.count_nonzero(x)) if x.any() else float(not y.any())
    precision,recall=score(be,ae),score(ae,be)
    result['boundary_f1_1px']=2*precision*recall/(precision+recall) if precision+recall else 0.
    result['reference_topology']=topology(a[:,:,3]);result['candidate_topology']=topology(b[:,:,3])
    return result

def inventory(path):
    doc=ET.parse(path).getroot();paths=list(doc.iter('{http://www.w3.org/2000/svg}path'))
    return {'paths':len(paths),'commands':sum(len(re.findall('[MmLlCcQqAaHhVvSsTtZz]',p.get('d','')))for p in paths),
      'observed_fills':sorted({el.get('fill')for el in doc.iter() if el.get('fill') not in [None,'none']})}

def run(args,folder):
    from engine import trace
    data=load(folder);run_dir=folder/'runs'/safe(args.name)
    if run_dir.exists():raise ValueError('Run exists; choose a new immutable name')
    run_dir.mkdir(parents=True);qapp=app();rows=[];prepared=[]
    source_paths=[*(ROOT/'desktop').glob('*.py'),*(ROOT/'rust/src').glob('*.rs'),*(ROOT/'web').glob('*.mjs'),*(ROOT/'web').glob('*.js'),*(ROOT/'web/vendor').glob('*.wasm'),*(ROOT/'quality').glob('*.py'),ROOT/'web/doctortracer.wasm']
    hashes={p.relative_to(ROOT).as_posix():digest(p) for p in source_paths}
    started=now();corpus_hash=digest(folder/'corpus.json')
    profiles=args.profiles.split(',')
    if any(p not in PROFILES for p in profiles):raise ValueError('Unknown profile')
    for row in select(data['images'],args.ids):
        with Image.open(folder/row['path']) as im:rgba=np.array(im.convert('RGBA'))
        for profile in profiles:
            name=row['id']+'--'+profile;cfg=config(profile);start=time.perf_counter()
            entry={'image':row['id'],'profile':profile,'source_sha256':row['sha256'],'config':cfg,'file':name+'.svg'}
            try:
                if args.engine=='desktop':
                    svg,stats=trace(folder/row['path'],cfg);(run_dir/entry['file']).write_text(svg,encoding='utf8');entry['stats']=stats
                else:
                    raw=run_dir/(name+'.rgba');raw.write_bytes(rgba.tobytes());prepared.append({'id':name,'source':raw.name,'output':entry['file'],'w':row['width'],'h':row['height'],'config':cfg})
                entry['seconds']=time.perf_counter()-start;entry['status']='ok'
            except Exception as e:entry.update(status='error',error=str(e))
            rows.append(entry);print(args.name,name,entry['status'],flush=True)
    if prepared:
        write(run_dir/'wasm-jobs.json',prepared)
        subprocess.run(['node',str(ROOT/'quality/run_wasm.mjs'),str(run_dir/'wasm-jobs.json')],cwd=ROOT,check=True)
        results=read(run_dir/'wasm-results.json')
        for row in rows:
            if row['status']=='ok':row.update(results[row['file']])
    for row in rows:
        if row['status']=='ok':
            image=next(i for i in data['images'] if i['id']==row['image'])
            try:
                Image.fromarray(render(run_dir/row['file'],image['width'],image['height'])).save((run_dir/row['file']).with_suffix('.png'))
                row['svg_sha256']=digest(run_dir/row['file'])
            except Exception as e:row.update(status='error',error='Render: '+str(e))
    write(run_dir/'run.json',{'schema':1,'created':started,'completed':now(),'engine':args.engine,'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      'corpus_sha256':corpus_hash,'renderer':'uniform-path-painter-3x-v1','source_hashes':hashes,'rows':rows})

def compare(args,folder):
    qapp=app();data=load(folder);run_dir=folder/'runs'/args.run;run=read(run_dir/'run.json')
    baseline_dir=folder/'runs'/args.baseline if args.baseline else None
    baseline=read(baseline_dir/'run.json') if baseline_dir else None
    out=folder/'reports'/safe(args.name)
    if out.exists():raise ValueError('Report exists; choose another name')
    (out/'assets').mkdir(parents=True);results=[];cards=[];regressions=[]
    for c in run['rows']:
        image=next(i for i in data['images'] if i['id']==c['image']);key=c['image']+'--'+c['profile'];row={**c,'category':image['category'],'split':image['split']}
        refs=folder/'references'/c['profile'];rp=refs/(c['image']+'.json');ref=read(rp) if rp.exists() else None
        row['reference_status']='missing' if not ref else 'verified' if ref['verified'] else 'unverified'
        if ref and (ref['source_sha256']!=image['sha256'] or ref['svg_sha256']!=digest(refs/(c['image']+'.svg')) or ref['evidence_sha256']!=digest(refs/ref['evidence'])):raise ValueError('Reference integrity failed: '+key)
        source=out/'assets'/(key+'-input.png')
        with Image.open(folder/image['path']) as im:im.convert('RGBA').save(source)
        if c['status']=='ok':
            if digest(run_dir/c['file'])!=c['svg_sha256']:raise ValueError('Candidate changed: '+key)
            candidate=render(run_dir/c['file'],image['width'],image['height']);Image.fromarray(candidate).save(out/'assets'/(key+'-candidate.png'))
            svg=ET.parse(run_dir/c['file']).getroot();paths=list(svg.iter('{http://www.w3.org/2000/svg}path'))
            row['path_count']=len(paths);row['commands']=sum(len(re.findall('[MmLlCcQqAaHhVvSsTtZz]',p.get('d','')))for p in paths)
            row['candidate_vector']=inventory(run_dir/c['file'])
            if ref and ref['verified']:
                row['reference_vector']=inventory(refs/(c['image']+'.svg'))
                reference=render(refs/(c['image']+'.svg'),image['width'],image['height']);row['metrics']=metrics(reference,candidate)
                Image.fromarray(reference).save(out/'assets'/(key+'-reference.png'))
                diff=np.abs(reference.astype(int)-candidate.astype(int));delta=np.maximum(diff[:,:,:3],diff[:,:,3:4]);Image.fromarray(np.minimum(delta*4,255).astype(np.uint8)).save(out/'assets'/(key+'-diff.png'))
                if baseline:
                    prev=next((p for p in baseline['rows'] if p['image']==c['image'] and p['profile']==c['profile'] and p['status']=='ok'),None)
                    if prev:
                        if prev['source_sha256']!=c['source_sha256'] or prev['config']!=c['config']:raise ValueError('Baseline settings differ: '+key)
                        if digest(baseline_dir/prev['file'])!=prev['svg_sha256']:raise ValueError('Baseline changed: '+key)
                        old_image=render(baseline_dir/prev['file'],image['width'],image['height']);old=metrics(reference,old_image)
                        Image.fromarray(old_image).save(out/'assets'/(key+'-baseline.png'))
                        row['baseline_metrics']=old;row['delta_white_mae']=row['metrics']['rgb_mae_white']-old['rgb_mae_white']
                        if row['delta_white_mae']>args.regression_mae or row['metrics']['alpha_iou']<old['alpha_iou']-args.regression_iou or row['metrics']['boundary_f1_1px']<old['boundary_f1_1px']-args.regression_boundary:regressions.append(key)
        results.append(row)
    verified=[r for r in results if 'metrics'in r]
    errors=[r['image']+'--'+r['profile']for r in results if r['status']!='ok']
    baseline_missing=[r['image']+'--'+r['profile']for r in results if 'baseline_metrics'not in r] if baseline else []
    summary={'cases':len(results),'verified_reference_cases':len(verified),'missing_or_unverified':len(results)-len(verified),'regressions':regressions,'errors':errors,
      'baseline_missing':baseline_missing,
      'coverage_complete':bool(results) and len(verified)==len(results),'baseline':args.baseline,'run':args.run,'generated':now(),
      'regression_thresholds':{'white_mae_increase':args.regression_mae,'alpha_iou_decrease':args.regression_iou,'boundary_f1_decrease':args.regression_boundary},
      'notice':'Missing/unverified references are excluded from quality aggregates. Metrics do not prove Vector Magic equivalence.'}
    if verified:summary['mean_rgb_mae_white']=float(np.mean([r['metrics']['rgb_mae_white']for r in verified]))
    summary['by_profile']={p:{'cases':len(v),'mean_rgb_mae_white':float(np.mean([r['metrics']['rgb_mae_white']for r in v]))} for p in sorted({r['profile']for r in verified}) if (v:=[r for r in verified if r['profile']==p])}
    summary['by_split']={p:{'cases':len(v),'mean_rgb_mae_white':float(np.mean([r['metrics']['rgb_mae_white']for r in v]))} for p in sorted({r['split']for r in verified}) if (v:=[r for r in verified if r['split']==p])}
    summary['by_category']={p:{'cases':len(v),'mean_rgb_mae_white':float(np.mean([r['metrics']['rgb_mae_white']for r in v]))} for p in sorted({r['category']for r in verified}) if (v:=[r for r in verified if r['category']==p])}
    write(out/'report.json',{'summary':summary,'cases':results})
    for r in sorted(results,key=lambda r:r.get('metrics',{}).get('rgb_mae_white',-1),reverse=True):
        key=r['image']+'--'+r['profile'];esc=html.escape
        def img(suffix,label):
            p='assets/'+key+'-'+suffix+'.png'
            return '<figure><a href="'+p+'"><img loading="lazy" src="'+p+'"></a><figcaption>'+label+'</figcaption></figure>' if (out/p).exists() else '<figure><p>Эталон не получен</p></figure>'
        metric=r.get('metrics');text='Нет подтверждённого эталона' if not metric else 'MAE белый %.4f · тёмный %.4f · IoU %.5f · границы F1 %.4f'%(metric['rgb_mae_white'],metric['rgb_mae_dark'],metric['alpha_iou'],metric['boundary_f1_1px'])
        previous=img('baseline','Baseline DoctorTracer') if baseline else ''
        slider=''
        if metric:
            slider='<details><summary>Шторка: слева DoctorTracer, справа Vector Magic</summary><div class="wipe"><img src="assets/'+key+'-reference.png"><img class="over" src="assets/'+key+'-candidate.png"></div><input class="slider" aria-label="Шторка сравнения" type="range" min="0" max="100" value="50"></details>'
        counts=''
        if metric:counts='<p>SVG paths / команды: VM '+str(r['reference_vector']['paths'])+' / '+str(r['reference_vector']['commands'])+'; DoctorTracer '+str(r['candidate_vector']['paths'])+' / '+str(r['candidate_vector']['commands'])+'. Топология силуэта: VM '+esc(str(metric['reference_topology']))+'; DoctorTracer '+esc(str(metric['candidate_topology']))+'.</p>'
        delta=''
        if 'baseline_metrics'in r:delta='<p>'+('УХУДШЕНИЕ: превышен допуск. ' if key in regressions else '')+'Δ MAE белый к baseline: '+format(r['delta_white_mae'],'+.5f')+'</p>'
        cards.append('<article data-regression="'+str(key in regressions).lower()+'" data-category="'+esc(r['category'])+'"><h2>'+esc(key)+'</h2><p>'+esc(r['split']+' · '+r['reference_status']+' · '+text)+'</p>'+delta+'<div class="grid">'+img('input','Исходник')+img('reference','Vector Magic')+previous+img('candidate','DoctorTracer')+img('diff','Разница ×4, включая альфа')+'</div>'+counts+slider+'</article>')
    template=(ROOT/'quality/report.html').read_text(encoding='utf8')
    (out/'index.html').write_text(template.replace('<!--SUMMARY-->',html.escape(json.dumps(summary,ensure_ascii=False,indent=2))).replace('<!--CASES-->','\n'.join(cards)),encoding='utf8')
    print(json.dumps(summary,ensure_ascii=True,indent=2));print('Report:',out/'index.html')
    if (args.require_complete and not summary['coverage_complete']) or regressions or errors or baseline_missing:raise SystemExit(2)

def main():
    p=argparse.ArgumentParser();p.add_argument('--corpus',type=Path,default=ROOT/'build/quality');sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init');sub.add_parser('queue')
    a=sub.add_parser('add-image');a.add_argument('--id',required=True);a.add_argument('--input',required=True);a.add_argument('--category',required=True);a.add_argument('--split',choices=['development','holdout'],default='holdout')
    a=sub.add_parser('reference');a.add_argument('--id',required=True);a.add_argument('--profile',choices=PROFILES,required=True);a.add_argument('--svg',required=True);a.add_argument('--evidence',required=True);a.add_argument('--version',required=True);a.add_argument('--wizard',choices=['basic','batch'],default='basic');a.add_argument('--verified',action='store_true');a.add_argument('--notes',default='')
    a=sub.add_parser('import-batch');a.add_argument('--directory',required=True);a.add_argument('--ids');a.add_argument('--profile',choices=PROFILES,required=True);a.add_argument('--evidence',required=True);a.add_argument('--version',required=True);a.add_argument('--wizard',choices=['basic','batch'],default='batch');a.add_argument('--verified',action='store_true');a.add_argument('--notes',default='')
    a=sub.add_parser('run');a.add_argument('--name',required=True);a.add_argument('--engine',choices=['desktop','wasm'],default='desktop');a.add_argument('--profiles',default='photo-medium-auto');a.add_argument('--ids')
    a=sub.add_parser('compare');a.add_argument('--run',required=True);a.add_argument('--baseline');a.add_argument('--name',required=True);a.add_argument('--regression-mae',type=float,default=.1);a.add_argument('--regression-iou',type=float,default=.001);a.add_argument('--regression-boundary',type=float,default=.01);a.add_argument('--require-complete',action='store_true')
    args=p.parse_args();folder=args.corpus.resolve();folder.mkdir(parents=True,exist_ok=True)
    {'init':init,'add-image':add_image,'queue':queue,'reference':register,'import-batch':import_batch,'run':run,'compare':compare}[args.command](args,folder)

if __name__=='__main__':main()
