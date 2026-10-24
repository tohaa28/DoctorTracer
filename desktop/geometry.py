"""Normalize the line/cubic SVG dialect emitted by native Potrace."""
import re


def absolute_path(data, sx=1., sy=1., tx=0., ty=0.):
    tokens=re.findall(r'[a-zA-Z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',data)
    result=[];i=0;cmd=None;x=y=mx=my=0.
    def fmt(n):
        s=f'{n:.3f}'.rstrip('0').rstrip('.')
        return s if s and s!='-0' else '0'
    def point(a,b):return fmt(a*sx+tx)+' '+fmt(b*sy+ty)
    while i<len(tokens):
        if tokens[i].isalpha():cmd=tokens[i];i+=1
        upper=cmd.upper();relative=cmd.islower()
        if upper=='Z':result.append('Z');x,y=mx,my;cmd=None;continue
        count={'M':2,'L':2,'C':6,'H':1,'V':1}.get(upper)
        if count is None:raise ValueError(f'Unsupported path command {cmd}')
        vals=list(map(float,tokens[i:i+count]));i+=count
        if upper in ('M','L'):
            a,b=vals
            if relative:a+=x;b+=y
            result.append(upper+point(a,b));x,y=a,b
            if upper=='M':mx,my=x,y;cmd='l' if relative else 'L'
        elif upper=='C':
            pairs=[]
            for j in (0,2,4):
                a,b=vals[j:j+2]
                if relative:a+=x;b+=y
                pairs.append(point(a,b))
            x=vals[4]+(x if relative else 0);y=vals[5]+(y if relative else 0)
            result.append('C'+' '.join(pairs))
        elif upper=='H':
            x=vals[0]+(x if relative else 0);result.append('L'+point(x,y))
        elif upper=='V':
            y=vals[0]+(y if relative else 0);result.append('L'+point(x,y))
    return ' '.join(result)
