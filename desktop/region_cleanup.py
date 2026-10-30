"""Remove low-contrast isolated regions without erasing thin high-contrast marks."""
import cv2
import numpy as np


def clean(labels,palette,min_area):
    if min_area<=1:return labels
    original=labels.copy();out=labels.copy();pal=np.asarray(palette,np.int32)
    for color in range(len(palette)):
        n,components,stats,_=cv2.connectedComponentsWithStats((original==color).astype(np.uint8),8)
        for k in range(1,n):
            x,y,w,h,area=stats[k]
            if area>=min_area or (min(w,h)<=2 and max(w,h)>=3):continue
            region=components[max(0,y-1):y+h+1,max(0,x-1):x+w+1]==k
            ring=cv2.dilate(region.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)&~region
            neighbors=original[max(0,y-1):y+h+1,max(0,x-1):x+w+1][ring]
            neighbors=neighbors[(neighbors!=255)&(neighbors!=color)]
            if not len(neighbors):continue
            target=int(np.bincount(neighbors,minlength=len(palette)).argmax())
            if int(np.sum((pal[color]-pal[target])**2))>35**2:continue
            patch=out[y:y+h,x:x+w];patch[components[y:y+h,x:x+w]==k]=target
    return out
