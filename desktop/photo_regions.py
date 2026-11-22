"""Photographic segmentation with a shared, disjoint colour boundary graph."""
import time
import hashlib
from collections import OrderedDict
import numpy as np
import cv2
import gpu_meanshift
import shared_regions
from trace_progress import report

_palettes=OrderedDict()

def automatic_palette(a,count):
    """Cache by pixel contents, never by a filename or a stale timestamp."""
    from engine import find_palette
    key=(a.shape,count,hashlib.blake2b(a.tobytes(),digest_size=16).digest())
    if key in _palettes:
        _palettes.move_to_end(key)
        return _palettes[key],True
    palette=find_palette(a,count,True)
    value=tuple(tuple(rgb) for rgb in palette);_palettes[key]=value
    if len(_palettes)>8:_palettes.popitem(last=False)
    return value,False

def trace(path,cfg):
    # Imported here to avoid a circular dependency at module initialization.
    from engine import load_source,segment
    started=time.perf_counter();metrics={};unlimited=not(cfg.get('palette') or cfg.get('colors'))
    options={**cfg,'quality':2,'photo_spatial':True,'_metrics':metrics,'_unlimited':unlimited}
    if unlimited:options['colors']=64
    report(cfg,8,'Фильтрация изображения')
    source,original=load_source(path,options)
    if unlimited:
        detail=cfg.get('detail',1)
        source,filtered=gpu_meanshift.apply(source,cfg.get('compute','gpu'),
            radius=[7,5,3][detail],color_range=[30,20,15][detail],iterations=5)
        metrics.update(filtered)
        options.setdefault('spatial_strength',200);options.setdefault('spatial_iterations',2)
        report(cfg,18,'Определение палитры')
        palette,hit=automatic_palette(source,options['colors'])
        options['palette']=['#%02x%02x%02x'%rgb for rgb in palette]
        metrics['palette_cache_hit']=hit
    report(cfg,28,'Сегментация изображения')
    a,labels,palette,original=segment(path,{**options,'_source':(source,original)})
    if not unlimited and (not cfg.get('palette') or cfg.get('palette_generated',False)) and cfg.get('joint_refine',True):
        from joint_palette import refine
        labels,palette,history=refine(a,labels,palette,cfg.get('compute','gpu'),options.get('spatial_strength',700),options.get('spatial_iterations',2))
        metrics['joint_palette_steps']=history
    if unlimited:
        # A region retains its own mean colour. A global ink table alone would
        # erase gradual shading in photos even when the shape remains intact.
        regions=np.full(labels.shape,-1,np.int32);inks=[]
        for color in range(len(palette)):
            report(cfg,35+int(20*color/max(1,len(palette))),'Выделение цветовых областей')
            count,components=cv2.connectedComponents((labels==color).astype(np.uint8),connectivity=4)
            counts=np.bincount(components.ravel(),minlength=count)
            sums=np.stack([np.bincount(components.ravel(),weights=a[:,:,j].ravel(),minlength=count) for j in range(3)],axis=1)
            colors=np.rint(sums[1:]/counts[1:,None]).astype(int)
            visible=components>0;regions[visible]=components[visible]-1+len(inks);inks.extend(colors.tolist())
        from region_merge import merge
        boundary_count=int(np.count_nonzero(labels[1:]!=labels[:-1])+np.count_nonzero(labels[:,1:]!=labels[:,:-1]))
        hsv=cv2.cvtColor(source[:,:,:3],cv2.COLOR_RGB2HSV)
        colorful=(source[:,:,3]>=128)&(hsv[:,:,1]>=32)&(hsv[:,:,2]>=32)
        histogram=np.bincount((hsv[:,:,0].astype(np.int32)*12//180)[colorful],minlength=12)
        probabilities=histogram[histogram>0]/max(1,histogram.sum())
        hue_entropy=float(-np.sum(probabilities*np.log2(probabilities)))
        diversity=float(np.clip(hue_entropy/3.2,.6,1.05))
        # A busy watercolour needs more regions than a simple photograph of
        # the same size. Boundary density measures that spatial complexity.
        target=max(128,round(diversity*boundary_count**2/labels.size/[40,16,6][cfg.get('detail',1)]))
        if cfg.get('photo_region_area'):target=max(16,round(labels.size/cfg['photo_region_area']))
        metrics.update(initial_regions=len(inks),region_target=target,boundary_count=boundary_count,hue_entropy=hue_entropy)
        report(cfg,60,'Объединение областей')
        labels,palette=merge(regions,inks,target)
    metrics['segmentation_seconds']=time.perf_counter()-started
    detail=cfg.get('detail',1)
    normal_tolerance=.12*[4,2,1][detail]
    tolerance=min(1.2,max(.05,[.75,.5,.3][detail]*cfg.get('curve_tolerance',normal_tolerance)/normal_tolerance))
    # Fixed inks need tighter boundaries: broad diffusion rounds away thin details.
    if not unlimited:tolerance*=.5
    report(cfg,70,'Построение общих границ')
    svg,geometry=shared_regions.trace(labels,palette,original,smooth=cfg.get('shared_smoothing',True),
        curve_tolerance=tolerance,rounding=1.5*cfg.get('alphamax',1.),passes=([10,8,5] if unlimited else [4,2,1])[detail],progress=cfg.get('_progress'),compute=cfg.get('compute','gpu'),source=a if cfg.get('edge_fit',True) else None,polygon=cfg.get('mode','spline')!='spline')
    if cfg.get('raster_refit',True) and cfg.get('shared_smoothing',True):
        from raster_refit import optimize
        from vector_partition import audit_pieces
        import xml.etree.ElementTree as ET
        candidate,refit=optimize(svg,a)
        if candidate!=svg:
            document=ET.fromstring(candidate);audit={}
            try:
                audit_pieces([(p.get('fill'),p.get('d')) for p in document.iter('{http://www.w3.org/2000/svg}path')],audit)
                svg=candidate;geometry['geometry_audit']=audit
            except ValueError as exc:refit.update(rejected=str(exc));refit['after']=refit['before']
        metrics['raster_refit']=refit
    return svg,{**geometry,**metrics,'width':original[0],'height':original[1],
        'working_size':[labels.shape[1],labels.shape[0]],'colors':geometry['color_groups'],
        'seconds':time.perf_counter()-started,'backend':'shared photographic regions',
        'palette_mode':'regional means' if unlimited else 'fixed',
        'palette':['#%02x%02x%02x'%tuple(c) for c in palette] if not unlimited else []}
