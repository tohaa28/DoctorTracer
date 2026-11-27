"""Generate synthetic 5-channel TIFF, not customer artwork."""
import numpy as np,tifffile,sys
from pathlib import Path
p=Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True)
w,h=5130,1685
a=np.zeros((h,w,5),dtype=np.uint8)
a[16:1660,16:1280]=[0,255,255,0,255]
a[16:1660,1280:2560]=[255,0,255,0,255]
a[16:1660,2560:3840]=[255,255,0,0,255]
a[16:1660,3840:5110]=[0,0,0,255,255]
a[200:400,200:400,4]=0
tifffile.imwrite(p,a,photometric='separated',extrasamples=['UNASSALPHA'],resolution=(300,300),resolutionunit='INCH',compression=None)
print('fixture',p,p.stat().st_size)
