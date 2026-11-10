"""Original deterministic stress fixtures; no downloaded or proprietary images."""
from pathlib import Path
import io
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def generate(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);rows=[]
    kinds=['logo','text','thin-lines','holes','alpha','gradient','texture','watercolor']
    for kind in kinds:
        for variant in range(5):
            seed=81031+kinds.index(kind)*100+variant;rng=np.random.default_rng(seed)
            w,h=256+variant*16,192+variant*8;scale=3
            bg=(255,255,255,0 if kind in ['alpha','holes'] else 255)
            im=Image.new('RGBA',(w*scale,h*scale),bg);d=ImageDraw.Draw(im)
            def box(x,y,a,b):return tuple(int(v*scale) for v in (x,y,a,b))
            ink=(24+variant*7,50,85,255);accent=(225,60+variant*15,42,255)
            if kind=='logo':
                d.rounded_rectangle(box(15,20,w-15,h-20),radius=15*scale,fill=ink)
                d.ellipse(box(35,35,135,135),fill=accent)
                d.polygon([(int(x*scale),int(y*scale))for x,y in [(100,h-30),(w-35,h-30),(w-75,40)]],fill=(70,190,155,255))
                d.rectangle(box(145,70,w-35,82),fill='white')
            elif kind=='text':
                font_path=Path('C:/Windows/Fonts/arial.ttf')
                if not font_path.exists():font_path=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
                for j,size in enumerate([10,16,25,37]):
                    font=ImageFont.truetype(str(font_path),size*scale) if font_path.exists() else ImageFont.load_default(size=size*scale)
                    d.text((12*scale,(8+j*43)*scale),'Ab8 O0 e @ 123',font=font,fill=ink)
            elif kind=='thin-lines':
                for j in range(1,12):
                    width=max(1,round((.35+j*.22)*scale))
                    d.line([(12*scale,j*14*scale),((w-12)*scale,(j*14+8+variant)*scale)],fill=ink,width=width)
                d.ellipse(box(w/2,12,w-15,h-12),outline=accent,width=scale)
            elif kind=='holes':
                for j in range(4):
                    x=12+j*(w-24)/4;d.rectangle(box(x,20,x+45,h-20),fill=ink)
                    d.ellipse(box(x+7,30,x+38,80),fill=(0,0,0,0))
                    d.rectangle(box(x+20,100,x+21+j,h-35),fill=(0,0,0,0))
                # Exactly one native pixel and a narrow bridge are deliberate invariants.
                d.rectangle(box(20,105,21,106),fill=(0,0,0,0))
            elif kind=='alpha':
                for j in range(7):d.ellipse(box(10+j*25,20+j*12,100+j*25,110+j*12),fill=(30+j*25,180,220-j*20,40+j*30))
                d.line([(10*scale,(h-15)*scale),((w-10)*scale,15*scale)],fill=(240,30,80,200),width=2*scale)
            elif kind in ['gradient','texture']:
                y,x=np.mgrid[:h,:w];a=np.zeros((h,w,4),np.uint8)
                a[:,:,0]=np.clip(20+210*x/(w-1),0,255);a[:,:,1]=np.clip(220-170*y/(h-1),0,255);a[:,:,2]=np.clip(40+100*np.sin(x/35)**2,0,255);a[:,:,3]=255
                if kind=='texture':a[:,:,:3]=np.clip(a[:,:,:3].astype(float)+rng.normal(0,12+variant*3,(h,w,1)),0,255)
                im=Image.fromarray(a).resize((w*scale,h*scale));d=ImageDraw.Draw(im)
                d.ellipse(box(50,25,w-40,h-25),outline=ink,width=3*scale)
            else:
                for _ in range(65):
                    x,y=rng.integers(0,w),rng.integers(0,h);radius=int(rng.integers(5,30));layer=Image.new('RGBA',im.size);ld=ImageDraw.Draw(layer)
                    ld.ellipse(box(x-radius,y-radius,x+radius,y+radius),fill=tuple(map(int,rng.integers(20,240,3)))+(int(rng.integers(30,100)),))
                    im=Image.alpha_composite(im,layer.filter(ImageFilter.GaussianBlur((variant+1)*scale)))
            im=im.resize((w,h),Image.Resampling.LANCZOS)
            if kind=='text' and variant==4:
                b=io.BytesIO();im.convert('RGB').save(b,'JPEG',quality=45);im=Image.open(io.BytesIO(b.getvalue())).convert('RGBA')
            name=f'{kind}-{variant+1:02d}';im.save(folder/(name+'.png'))
            rows.append({'id':name,'path':'inputs/'+name+'.png','category':kind,'origin':'generated','seed':seed,'split':'holdout' if variant>=3 else 'development','width':w,'height':h})
    return rows
