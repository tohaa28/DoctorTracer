"""Palette-independent semantic boundaries and fixed-palette topology."""
import numpy as np
import cv2

def boundary(labels):
    out=np.zeros(labels.shape,bool);vertical=labels[1:]!=labels[:-1];horizontal=labels[:,1:]!=labels[:,:-1]
    out[1:]|=vertical;out[:-1]|=vertical;out[:,1:]|=horizontal;out[:,:-1]|=horizontal
    return out

def region_topology(labels):
    colors=np.unique(labels);colors=colors[colors>=0]
    if len(colors)>24:return {'measured':False,'reason':'more than 24 regions/colours; aggregate topology omitted','colors':len(colors)}
    total=significant=tiny=holes=0
    for color in colors:
        mask=(labels==color).astype(np.uint8);n,_,stats,_=cv2.connectedComponentsWithStats(mask,connectivity=4)
        areas=stats[1:,cv2.CC_STAT_AREA];total+=n-1;significant+=int(np.count_nonzero(areas>=4));tiny+=int(np.count_nonzero(areas<4))
        _,hierarchy=cv2.findContours(mask,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is not None:holes+=int(np.count_nonzero(hierarchy[0,:,3]>=0))
    return {'measured':True,'colors':len(colors),'components':total,'components_ge4px':significant,'tiny_components':tiny,'holes':holes}

def compare_labels(a,b):
    ea,eb=boundary(a),boundary(b);kernel=np.ones((3,3),np.uint8)
    def coverage(x,y):return float(np.mean(cv2.dilate(y.astype(np.uint8),kernel)[x]>0)) if x.any() else float(not y.any())
    precision,recall=coverage(eb,ea),coverage(ea,eb)
    values=[]
    for x,y in [(ea,eb),(eb,ea)]:
        if x.any() and y.any():values.append(cv2.distanceTransform((~y).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)[x])
    distance=np.concatenate(values) if len(values)==2 else np.zeros(1) if not ea.any() and not eb.any() else None
    return {'region_boundary_f1_1px':2*precision*recall/(precision+recall) if precision+recall else 0.,
            'boundary_mean_distance_px':float(np.mean(distance)) if distance is not None else None,
            'boundary_p95_distance_px':float(np.percentile(distance,95)) if distance is not None else None,
            'reference_color_topology':region_topology(a),'candidate_color_topology':region_topology(b)}

def palette_distance(reference,candidate):
    from PySide6.QtGui import QColor
    def lab(values):
        rgb=[]
        for value in values:
            c=QColor(value)
            if c.isValid():rgb.append([c.red(),c.green(),c.blue()])
        return cv2.cvtColor(np.asarray(rgb,np.float32).reshape(1,-1,3)/255,cv2.COLOR_RGB2LAB)[0] if rgb else np.empty((0,3))
    a,b=lab(reference),lab(candidate)
    def nearest(x,y):
        distances=[]
        for i in range(0,len(x),128):distances.extend(np.sqrt(((x[i:i+128,None]-y[None])**2).sum(2)).min(1).tolist())
        return float(np.mean(distances))
    return {'reference_rgb_colors':len(a),'candidate_rgb_colors':len(b),'symmetric_nearest_deltaE76':(nearest(a,b)+nearest(b,a))/2 if len(a) and len(b) else None,
            'policy':'unweighted nearest palette distance, not a one-to-one palette matching or full-image perceptual score'}
