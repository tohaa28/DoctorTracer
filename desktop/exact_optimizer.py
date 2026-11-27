"""Exact geometry-only node optimization. See Relief Forge MIT attribution."""
import re
from decimal import Decimal, InvalidOperation, localcontext

LIMIT=100000000000000
SCALE=10**7
TOKEN=re.compile(r'[MLCZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?')
def integer(s):
    if len(s)>50:raise ValueError('coordinate length')
    with localcontext() as ctx:
        ctx.prec=100
        try:
            d=Decimal(s)
            if not d.is_finite() or abs(d.adjusted())>40:raise ValueError('coordinate range')
            n=d*SCALE
            if n!=n.to_integral_value() or abs(n)>LIMIT:raise ValueError('coordinate grid')
            return int(n)
        except InvalidOperation as exc:raise ValueError('coordinate') from exc
def decimal(n):
    sign='-' if n<0 else '';s=str(abs(n)).zfill(8);f=s[-7:].rstrip('0')
    return sign+s[:-7]+('.'+f if f else '')
def parse(d):
    ts=[];end=0
    for m in TOKEN.finditer(d):
        if not re.fullmatch(r'[\s,]*',d[end:m.start()]):raise ValueError('path syntax')
        ts.append(m.group());end=m.end()
    if not re.fullmatch(r'[\s,]*',d[end:]) or not ts:raise ValueError('empty path')
    rings=[];ring=None;i=0
    while i<len(ts):
        op=ts[i];i+=1;n={'M':2,'L':2,'C':6,'Z':0}.get(op)
        if n is None or i+n>len(ts):raise ValueError('explicit command required')
        coords=tuple(integer(t) for t in ts[i:i+n]);i+=n
        if op=='M':
            if ring is not None:raise ValueError('open path')
            ring=[(op,coords)]
        elif op=='Z':
            if ring is None or len(ring)<2:raise ValueError('empty path')
            rings.append(ring);ring=None
        else:
            if ring is None:raise ValueError('missing M')
            ring.append((op,coords))
    if ring is not None or not rings:raise ValueError('closed paths required')
    return rings
def endpoint(s):return s[1][-2:]
def forward(a,b,c):
    x,y=b[0]-a[0],b[1]-a[1];u,v=c[0]-b[0],c[1]-b[1]
    return x*v-y*u==0 and x*u+y*v>0
def half_merge(p,a,b):
    if a[0]!='C' or b[0]!='C':return None
    q,r,m=a[1][:2],a[1][2:4],a[1][4:];s,t,z=b[1][:2],b[1][2:4],b[1][4:]
    p1=tuple(2*q[i]-p[i] for i in range(2));p2=tuple(2*t[i]-z[i] for i in range(2))
    for i in range(2):
        if 4*r[i]!=p[i]+2*p1[i]+p2[i] or 4*s[i]!=p1[i]+2*p2[i]+z[i] or 8*m[i]!=p[i]+3*p1[i]+3*p2[i]+z[i]:return None
    if any(abs(v)>LIMIT for v in p1+p2):return None
    return 'C',p1+p2+z
def optimize_path(d):
    try:rings=parse(d)
    except (ValueError,ArithmeticError):return dict(d=d,before=0,after=0,zero=0,straight=0,cubic=0,skipped=1)
    before=after=zero=straight=cubic=0;output=[]
    for ring in rings:
        before+=len(ring)-1;stack=[ring[0]];z=l=c=0
        for seg in ring[1:]:
            p=endpoint(stack[-1])
            if all(v==p[i%2] for i,v in enumerate(seg[1])):z+=1;continue
            stack.append(seg)
            while len(stack)>=3:
                a,b=stack[-2:];start=endpoint(stack[-3])
                if a[0]==b[0]=='L' and forward(start,endpoint(a),endpoint(b)):
                    stack[-2:]=[b];l+=1;continue
                merged=half_merge(start,a,b)
                if merged is not None:stack[-2:]=[merged];c+=1;continue
                break
        kept=ring if len(stack)==1 else stack
        if len(stack)>1:zero+=z;straight+=l;cubic+=c
        after+=len(kept)-1;output.append(' '.join(op+' '.join(map(decimal,coords)) for op,coords in kept)+' Z')
    return dict(d=d if before==after else ' '.join(output),before=before,after=after,zero=zero,straight=straight,cubic=cubic,skipped=0)
def optimize_svg(svg):
    if re.search(r'\s(?:stroke(?:-[\w-]+)?|style|class|marker(?:-[\w-]+)?|clip-path|mask|filter|pathLength)\s*=|<(?:style|script|use|image|text|clipPath|mask|filter)\b',svg,re.I):
        raise ValueError('Точная оптимизация поддерживает только обычные залитые контуры')
    stats=dict(before=0,after=0,zero=0,straight=0,cubic=0,skipped=0)
    def tag(m):
        def data(n):
            result=optimize_path(n[2])
            for k in stats:stats[k]+=result[k]
            return n[1]+result['d']+n[3]
        return re.sub(r'(\s+d=")([^"]*)(")',data,m[0])
    result=re.sub(r'<path\b[^>]*>',tag,svg)
    return result,{**stats,'removed':stats['before']-stats['after']}
def checked_optimize(svg):
    from vector_partition import audit_pieces
    import xml.etree.ElementTree as ET
    candidate,stats=optimize_svg(svg)
    if candidate!=svg:
        root=ET.fromstring(candidate);report={}
        audit_pieces([(p.get('fill'),p.get('d')) for p in root.iter('{http://www.w3.org/2000/svg}path')],report)
        stats['geometry']=report
    return candidate,stats
