"""Offline raster preparation, vectorization and vector-only EPS export."""
import io
import re
import json
import sys
import time
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageOps, ImageFilter, ImageDraw
import numpy as np
import vtracer
import cv2
from geometry import absolute_path

NS='http://www.w3.org/2000/svg'


def load_source(path,cfg):
    with Image.open(path) as src:
        im=ImageOps.exif_transpose(src).convert('RGBA')
    original=im.size
    im.thumbnail((cfg.get('max_size',2400),)*2,Image.Resampling.LANCZOS)
    a=np.array(im)
    if cfg.get('flatten'):
        bg=np.array([int(cfg.get('flatten_color','#ffffff')[i:i+2],16) for i in (1,3,5)])
        alpha=a[:,:,3:4]/255.
        a[:,:,:3]=np.round(a[:,:,:3]*alpha+bg*(1-alpha)).astype('uint8');a[:,:,3]=255
    if cfg.get('remove_bg'):
        border=np.concatenate((a[0,:,:3],a[-1,:,:3],a[:,0,:3],a[:,-1,:3]))
        bins=(border//8).astype('int32');keys=bins[:,0]*1024+bins[:,1]*32+bins[:,2]
        values,counts=np.unique(keys,return_counts=True)
        bg=np.median(border[keys==values[counts.argmax()]],axis=0)
        near=(np.max(np.abs(a[:,:,:3].astype('float32')-bg),axis=2)<=cfg.get('tolerance',24)).astype('uint8')
        # Pad with a connected outer border and flood only candidate background.
        padded=np.pad(near,1,constant_values=1)
        cv2.floodFill(padded,None,(0,0),2)
        a[:,:,3][padded[1:-1,1:-1]==2]=0
    if cfg.get('denoise') or cfg.get('quality',2)==0:
        a[:,:,:3]=cv2.bilateralFilter(a[:,:,:3],5,25,3)
    return a,original


def find_palette(a, count=0, photo=False, merge_distance=24):
    rgb=a[:,:,:3];opaque=a[:,:,3]>127
    if not np.any(opaque):return [[255,255,255]]
    # Flat interior pixels are evidence for real ink colors; edge mixtures are not.
    maxc=cv2.dilate(rgb,np.ones((3,3),np.uint8)).astype('int16')
    minc=cv2.erode(rgb,np.ones((3,3),np.uint8)).astype('int16')
    flat=(np.max(maxc-minc,axis=2)<22)&opaque
    samples=rgb[flat] if flat.sum()>64 else rgb[opaque]
    samples=samples[::max(1,len(samples)//60000)]
    keys=(samples//8).astype('int32');keys=keys[:,0]*1024+keys[:,1]*32+keys[:,2]
    uniq,cnt=np.unique(keys,return_counts=True)
    order=np.argsort(-cnt)
    palette=[];weights=[]
    for j in order[:128]:
        if cnt[j]<max(4,len(samples)*.0015):break
        color=np.median(samples[keys==uniq[j]],axis=0)
        if all(np.linalg.norm(color-np.array(p))>merge_distance for p in palette):
            palette.append(color.astype(int).tolist());weights.append(int(cnt[j]))
        if len(palette)>=24:break
    if not palette:palette=[np.median(samples,axis=0).astype(int).tolist()]
    target=count or (min(24,max(8,len(palette))) if photo else len(palette))
    target=max(2,min(64,target))
    if not photo and not count and len(palette)<=24:return palette
    if len(palette)==target and not photo:return palette
    pixels=rgb[opaque][::max(1,int(opaque.sum())//60000)].astype('float32')
    cv2.setRNGSeed(27)
    target=min(target,len(np.unique(pixels,axis=0)))
    _,labels,centers=cv2.kmeans(pixels,target,None,(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,35,.2),3,cv2.KMEANS_PP_CENTERS)
    # Use medians of clusters to retain original flat colors despite JPEG ringing.
    return [np.median(pixels[labels[:,0]==i],axis=0).astype(int).tolist() for i in range(target) if np.any(labels[:,0]==i)]


def analyze_image(path,cfg=None):
    cfg=cfg or {}
    a,size=load_source(path,{**cfg,'max_size':900})
    palette=find_palette(a)
    rgb=a[:,:,:3]
    # A compact dominant palette indicates graphics rather than a photograph.
    # Invisible RGB bytes in transparent PNG margins are not image colors.
    visible=rgb[a[:,:,3]>127]
    sample=(visible[::max(1,len(visible)//30000)] if len(visible) else rgb.reshape(-1,3)[:1]).astype('float32')
    distance=np.min(np.sum((sample[:,None,:]-np.array(palette)[None,:,:])**2,axis=2),axis=1)
    coverage=float(np.mean(distance<35**2))
    category='photo' if coverage<.8 or len(palette)>18 else 'aa'
    return {'palette':['#%02x%02x%02x'%tuple(c) for c in palette], 'category':category,
            'size':list(size),'transparent':bool(np.any(a[:,:,3]<255)), 'coverage':coverage}


def segment(path,cfg):
    a,original=cfg.get('_source') or load_source(path,cfg)
    if cfg.get('preset')=='Чёрно-белое' or cfg.get('category')=='bw':
        gray=cv2.cvtColor(a[:,:,:3],cv2.COLOR_RGB2GRAY)
        a[:,:,:3]=np.where(gray[:,:,None]>=cfg.get('threshold',160),255,0).astype('uint8')
        palette=[[255,255,255],[0,0,0]]
    elif cfg.get('palette'):
        palette=[[int(c[i:i+2],16) for i in (1,3,5)] for c in cfg['palette']]
    else:
        palette=find_palette(a,cfg.get('colors',0),cfg.get('category')=='photo' or cfg.get('preset')=='Фотография')
    if cfg.get('supersample',1)>1:
        a=cv2.resize(a,None,fx=cfg['supersample'],fy=cfg['supersample'],interpolation=cv2.INTER_LINEAR)
    from accelerator import assign
    labels,compute=assign(a,palette,cfg.get('category','aa')=='aa' and cfg.get('palette_aa',True) and len(palette)<=24,3*cfg.get('supersample',1),cfg.get('compute','auto'))
    if '_metrics' in cfg:cfg['_metrics'].update(compute)
    min_area=cfg.get('speckle',2)
    if 'segmentation_complexity' in cfg:
        min_area=max(min_area,max(0,6-cfg['segmentation_complexity'])**2)
    if cfg.get('artifact_strength',0):
        median=cv2.medianBlur(labels,3)
        neighbors=cv2.boxFilter((labels!=median).astype('float32'),-1,(3,3),normalize=False)
        change=(labels!=255)&(median!=255)&(neighbors>= (6 if cfg['artifact_strength']==1 else 4))
        labels[change]=median[change]
    if min_area:
        # Reassign isolated specks from neighboring regions, preserving thin strokes.
        median=cv2.medianBlur(labels,3)
        for i in range(len(palette)):
            n,components,stats,_=cv2.connectedComponentsWithStats((labels==i).astype('uint8'),8)
            bad=np.where(stats[:,cv2.CC_STAT_AREA]<min_area)[0]
            bad=bad[bad!=0]
            if len(bad):
                small=np.isin(components,bad);labels[small]=median[small]
    return a,labels,palette,original


def native_trace(mask,cfg,scale=1.):
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
    exe=root/'vendor/potrace/potrace.exe'
    if not exe.exists():raise FileNotFoundError('Не найден встроенный движок Potrace')
    h,w=mask.shape
    data=f'P4\n{w} {h}\n'.encode()+np.packbits(mask.astype('uint8'),axis=1).tobytes()
    detail=cfg.get('detail',2)
    tolerance=cfg.get('curve_tolerance',[.5,.2,.12][detail])
    alpha=cfg.get('alphamax',1.) if cfg.get('mode','spline')=='spline' else 0
    args=[str(exe),'-s','-o','-','--flat','-t','0','-a',str(alpha),'-O',str(tolerance),'-u','100']
    proc=subprocess.run(args,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=90)
    if proc.returncode:raise RuntimeError(proc.stderr.decode('utf-8',errors='replace'))
    doc=ET.fromstring(proc.stdout)
    group=doc.find('{'+NS+'}g')
    # Potrace's emitted transform is translate(0,H) scale(1/unit,-1/unit).
    transform=group.get('transform')
    nums=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',transform)))
    tx,ty,sx,sy=nums
    return [absolute_path(p.get('d'),sx/scale,sy/scale,tx/scale,ty/scale) for p in group if p.tag.endswith('path')]


def trace_graphic(path,cfg):
    aa=cfg.get('category','aa')=='aa'
    metrics={};stage=time.perf_counter()
    source=load_source(path,cfg)
    # Transparent illustrations need a smooth silhouette independently of their
    # interior color regions. A solid underlayer also prevents pale seams.
    layered=aa and cfg.get('shape_strategy','auto')!='independent' and bool(np.any(source[0][:,:,3]<128)) and 'supersample' not in cfg
    supersample=1 if layered else cfg.get('supersample',2 if aa else 1)
    a,labels,palette,original=segment(path,{**cfg,'supersample':supersample,'_metrics':metrics,'_source':source})
    metrics['shape_strategy']='silhouette + interior layers' if layered else 'independent masks'
    metrics['segmentation_seconds']=time.perf_counter()-stage;stage=time.perf_counter()
    h,w=labels.shape
    root=ET.Element('{'+NS+'}svg',{'width':str(original[0]),'height':str(original[1]),'viewBox':f'0 0 {w} {h}','version':'1.1'})
    # Trace actual segmentation masks; smooth/optimize curves independently of palette discovery.
    counts=np.bincount(labels[labels!=255],minlength=len(palette))
    order=sorted((i for i in range(len(palette)) if counts[i]),key=lambda i:-counts[i])
    from concurrent.futures import ThreadPoolExecutor
    def trace_ink(i):
        if layered and i==order[0]:
            alpha=cv2.resize(a[:,:,3],None,fx=2,fy=2,interpolation=cv2.INTER_LINEAR)
            return i,native_trace(alpha>=128,cfg,scale=2.)
        mask=labels==i
        if cfg.get('contour_blur',0)>0:mask=cv2.GaussianBlur(mask.astype(np.float32),(0,0),cfg['contour_blur']*cfg.get('supersample',2 if aa else 1))>=.5
        return i,native_trace(mask,cfg)
    with ThreadPoolExecutor(max_workers=min(4,len(order) or 1)) as pool:
        for i,paths in pool.map(trace_ink,order):
            for data in paths:ET.SubElement(root,'{'+NS+'}path',{'d':data,'fill':'#%02x%02x%02x'%tuple(palette[i]),'fill-rule':'nonzero'})
    metrics['curves_seconds']=time.perf_counter()-stage
    ET.register_namespace('',NS)
    return ET.tostring(root,encoding='unicode',xml_declaration=True),{
        'paths':len(root),'colors':len(order),'width':original[0],'height':original[1],
        'working_size':[w,h],'palette':['#%02x%02x%02x'%tuple(c) for c in palette],**metrics}


def prepare(path, cfg):
    with Image.open(path) as src:
        im = ImageOps.exif_transpose(src).convert('RGBA')
    original = im.size
    limit = cfg.get('max_size', 2400)
    im.thumbnail((limit, limit), Image.Resampling.LANCZOS)
    if cfg.get('remove_bg'):
        a = np.array(im)
        corners = np.array([a[0, 0, :3], a[0, -1, :3], a[-1, 0, :3], a[-1, -1, :3]])
        bg = np.median(corners, axis=0)
        near = np.max(np.abs(a[:, :, :3].astype(float) - bg), axis=2) <= cfg.get('tolerance', 24)
        mask = Image.fromarray(np.where(near, 0, 255).astype('uint8')).copy()
        # Remove only areas connected to the border, retaining enclosed white detail.
        w, h = im.size
        for x in range(w):
            for y in (0, h - 1):
                if mask.getpixel((x, y)) == 0:
                    ImageDraw.floodfill(mask, (x, y), 128)
        for y in range(h):
            for x in (0, w - 1):
                if mask.getpixel((x, y)) == 0:
                    ImageDraw.floodfill(mask, (x, y), 128)
        a[:, :, 3][np.array(mask) == 128] = 0
        im = Image.fromarray(a)
    alpha = im.getchannel('A')
    rgb = Image.new('RGB', im.size, 'white')
    rgb.paste(im, mask=alpha)
    if cfg.get('denoise', 0):
        rgb = rgb.filter(ImageFilter.MedianFilter(3))
    if cfg.get('preset') == 'Чёрно-белое':
        rgb = ImageOps.grayscale(rgb).point(lambda x: 255 if x >= cfg.get('threshold', 160) else 0).convert('RGB')
    elif cfg.get('colors', 0):
        rgb = rgb.quantize(colors=cfg['colors'], method=Image.Quantize.MEDIANCUT,
                           dither=Image.Dither.NONE).convert('RGB')
    rgb.putalpha(alpha)
    return rgb, original


def trace(path, cfg):
    start = time.monotonic()
    category=cfg.get('category','aa')
    use_palette=bool(cfg.get('palette')) or bool(cfg.get('colors'))
    photo=category=='photo' or cfg.get('preset')=='Фотография'
    if cfg.get('backend','auto')!='vtracer' and (not photo or use_palette) and cfg.get('mode')!='none':
        svg,stats=trace_graphic(path,cfg)
        stats['seconds']=round(time.monotonic()-start,2)
        stats['backend']='segmentation + Potrace 1.16'
        return svg,stats
    if photo and not use_palette:
        # Keep straight RGB through segmentation. Compositing semitransparent
        # pixels against white before tracing creates pale fringes on dark views.
        a, original=load_source(path,{**cfg,'denoise':False,'quality':2})
        detail=cfg.get('detail',2)
        spatial,color=[(7,30),(5,20),(3,15)][detail]
        a[:,:,:3]=cv2.pyrMeanShiftFiltering(a[:,:,:3],spatial,color,maxLevel=1)
        a[:,:,3]=np.where(a[:,:,3]>=128,255,0)
        im=Image.fromarray(a)
    else:
        im, original = prepare(path, cfg)
    buf = io.BytesIO()
    im.save(buf, format='PNG')
    detail = cfg.get('detail', 2)
    svg = vtracer.convert_raw_image_to_svg(
        buf.getvalue(), img_format='png', colormode='color', hierarchical='stacked',
        mode=cfg.get('mode', 'spline'), filter_speckle=(cfg.get('photo_speckle',[12,6,4][detail])+max(0,cfg.get('speckle',2)-2) if photo and not use_palette else cfg.get('speckle',4)),
        color_precision=8 if cfg.get('colors') else [5, 6, 7][detail],
        layer_difference=8 if cfg.get('colors') else [32, 24, 16][detail],
        corner_threshold=cfg.get('corner', 60), length_threshold=[6., 4., 3.][detail],
        max_iterations=10, splice_threshold=45, path_precision=3)
    refit_seconds=0.
    if photo and not use_palette and cfg.get('mode','spline')=='spline' and cfg.get('photo_curve_refit',True):
        from photo_curves import refit_curves
        stage=time.perf_counter()
        svg,_=refit_curves(svg,cfg.get('photo_curve_tolerance',[.6,.4,.25][detail]),cfg.get('photo_curve_alpha',1.2))
        refit_seconds=time.perf_counter()-stage
    root = ET.fromstring(svg)
    # Preserve physical image dimensions even when processing resolution is limited.
    root.set('viewBox', f'0 0 {im.width} {im.height}')
    root.set('width', str(original[0]))
    root.set('height', str(original[1]))
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    svg = ET.tostring(root, encoding='unicode', xml_declaration=True)
    return svg, {'paths': len(list(root)), 'seconds': round(time.monotonic()-start, 2),
                 'width': original[0], 'height': original[1], 'working_size': list(im.size),
                 'colors': len(set(p.get('fill') for p in root)),
                 'backend':'spatial color regions + VTracer' if photo and not use_palette else 'VTracer',
                 'curve_backend':'Potrace Bezier refit' if refit_seconds else 'VTracer',
                 'curve_refit_seconds':round(refit_seconds,4),
                 'compute':'CPU', 'alpha_threshold':128 if photo and not use_palette else None}


def to_eps(svg):
    """Convert the restricted, trusted VTracer SVG path dialect to PostScript."""
    root = ET.fromstring(svg)
    width, height = float(root.get('width')), float(root.get('height'))
    view = [float(v) for v in root.get('viewBox', f'0 0 {width} {height}').split()]
    lines = ['%!PS-Adobe-3.0 EPSF-3.0', f'%%BoundingBox: 0 0 {int(width+.999)} {int(height+.999)}',
             '%%Creator: DoctorTracer', '%%EndComments', f'0 {height} translate',
             f'{width/view[2]} {-height/view[3]} scale']
    for el in root:
        if not el.tag.endswith('path'):
            raise ValueError('Unsupported SVG element')
        color = el.get('fill', '#000000').lstrip('#')
        if len(color) != 6:
            raise ValueError('Unsupported SVG color')
        lines += ['gsave', ' '.join(str(int(color[i:i+2],16)/255) for i in (0,2,4))+' setrgbcolor']
        transform = el.get('transform','')
        if transform:
            m = re.fullmatch(r'translate\(([-+\d.eE]+)[, ]+([-+\d.eE]+)\)', transform)
            if not m:
                raise ValueError('Unsupported transform')
            lines.append(f'{m[1]} {m[2]} translate')
        tokens = re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', el.get('d',''))
        i, cmd = 0, None
        lines.append('newpath')
        while i < len(tokens):
            if tokens[i].isalpha():
                cmd = tokens[i]; i += 1
            if cmd in ('Z','z'):
                lines.append('closepath'); cmd = None; continue
            n, op = {'M':(2,'moveto'),'L':(2,'lineto'),'C':(6,'curveto')}.get(cmd, (0,''))
            if not n or i+n > len(tokens):
                raise ValueError(f'Unsupported path command: {cmd}')
            lines.append(' '.join(tokens[i:i+n])+' '+op)
            i += n
            if cmd == 'M': cmd = 'L'
        lines += ['fill', 'grestore']
    return '\n'.join(lines + ['showpage','%%EOF',''])


def worker(job_path):
    job = json.loads(Path(job_path).read_text(encoding='utf-8'))
    try:
        svg, stats = trace(job['input'], job['config'])
        Path(job['output']).write_text(svg, encoding='utf-8')
        Path(job['result']).write_text(json.dumps({'ok': True, **stats}), encoding='utf-8')
        return 0
    except BaseException as exc:
        Path(job['result']).write_text(json.dumps({'ok': False, 'error': str(exc)}), encoding='utf-8')
        return 1

def worker_server():
    """One job at a time; preserve the OpenCL context between settings changes."""
    for line in sys.stdin.buffer:
        try:
            path=json.loads(line.decode('utf-8'))['job']
            code=worker(path)
        except Exception:code=1
        print(json.dumps({'exit_code':code}),flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(worker(sys.argv[1]))
