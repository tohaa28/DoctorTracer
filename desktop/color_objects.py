"""Merge partition boundaries and export editable PDF groups per color."""
import re,zlib
import xml.etree.ElementTree as ET
import pyclipper
from vector_partition import polygon_data,NS

def merge_colors(svg,preserve_curves=False):
    root=ET.fromstring(svg);out=ET.Element(root.tag,root.attrib);colors={}
    if preserve_curves:
        root.set('data-color-objects','merged')
        return ET.tostring(root,encoding='unicode'),len(list(root.iter('{'+NS+'}path')))
    for el in root.iter('{'+NS+'}path'):
        colors.setdefault(el.get('fill'),[]).extend(polygon_data(el.get('d','')))
    count=0
    def emit(node,group,color):
        nonlocal count
        for outer in node.Childs:
            if outer.IsHole:continue
            contours=[outer.Contour]+[h.Contour for h in outer.Childs if h.IsHole]
            data=' '.join('M'+' L'.join(f'{x/10000000:.7f} {y/10000000:.7f}' for x,y in path)+' Z' for path in contours)
            ET.SubElement(group,'{'+NS+'}path',{'d':data,'fill':color,'fill-rule':'nonzero'});count+=1
            for hole in outer.Childs:emit(hole,group,color)
    for color,polygons in colors.items():
        pc=pyclipper.Pyclipper()
        if not polygons:continue
        pc.AddPaths(polygons,pyclipper.PT_SUBJECT,True)
        tree=pc.Execute2(pyclipper.CT_UNION,pyclipper.PFT_NONZERO,pyclipper.PFT_NONZERO)
        group=ET.SubElement(out,'{'+NS+'}g',{'fill':color,'id':'color-'+color.lstrip('#'),'data-color':color})
        emit(tree,group,color)
    out.set('data-color-objects','merged')
    return ET.tostring(out,encoding='unicode'),count

def connected_paths(data):
    """Split disconnected outers, retaining original coordinate strings and holes."""
    chunks=re.findall(r'M[^M]*',data)
    if len(chunks)<2:return [data]
    from vector_partition import parse
    paths=[parse(chunk) for chunk in chunks]
    outer_winding=max(paths,key=lambda p:abs(p.area)).clockwise
    outers=[i for i,p in enumerate(paths) if p.clockwise==outer_winding]
    holes=[i for i,p in enumerate(paths) if p.clockwise!=outer_winding]
    grouped={i:[chunks[i]] for i in outers}
    for hole in holes:
        points=[pts[-1] for verb,pts in paths[hole].segments if pts]
        parents=[i for i in outers if abs(paths[i].area)>=abs(paths[hole].area) and all(paths[i].bounds[j]<=paths[hole].bounds[j]+1e-6 for j in (0,1)) and all(paths[i].bounds[j]>=paths[hole].bounds[j]-1e-6 for j in (2,3)) and any(paths[i].contains(point) for point in points)]
        if not parents:return [data]  # Preserve ambiguous touching contours intact.
        parent=min(parents,key=lambda i:abs(paths[i].area))
        grouped[parent].append(chunks[hole])
    return [' '.join(grouped[i]) for i in outers]


def pdf_bytes(svg):
    root=ET.fromstring(svg);w=float(root.get('width'));h=float(root.get('height'))
    x,y,vw,vh=map(float,root.get('viewBox',f'0 0 {w} {h}').split())
    groups={}
    def collect(el,fill='#000000'):
        fill=el.get('fill',fill).lower()
        if el.tag=='{'+NS+'}path' and fill!='none' and el.get('d'):
            groups.setdefault(fill,[]).extend(connected_paths(el.get('d')))
        for child in el:collect(child,fill)
    collect(root)
    objects=[b'',b''];resources=[];page=[]
    def stream(data,attributes=''):
        packed=zlib.compress(data.encode('ascii'))
        return (f'<< {attributes} /Length {len(packed)} /Filter /FlateDecode >>\nstream\n'.encode()+packed+b'\nendstream')
    for index,(color,paths) in enumerate(groups.items()):
        content=[' '.join(str(int(color[i:i+2],16)/255) for i in (1,3,5))+' rg']
        for data in paths:
            tokens=re.findall(r'[MLCZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',data);i=0;cmd=''
            while i<len(tokens):
                if tokens[i].isalpha():cmd=tokens[i];i+=1
                if cmd=='Z':content.append('h');cmd='';continue
                n,op={'M':(2,'m'),'L':(2,'l'),'C':(6,'c')}[cmd]
                content.append(' '.join(tokens[i:i+n])+' '+op);i+=n
                if cmd=='M':cmd='L'
            content.append('f')
        objects.append(stream('\n'.join(content),f'/Type /XObject /Subtype /Form /FormType 1 /Group << /S /Transparency /CS /DeviceRGB /I true /K false >> /BBox [{x} {y} {x+vw} {y+vh}] /Resources << >>'))
        obj=len(objects);resources.append(f'/Color{index} {obj} 0 R');page.append(f'/Color{index} Do')
    objects.append(stream(f'q\n{w/vw} 0 0 {-h/vh} {-x*w/vw} {h+y*h/vh} cm\n'+'\n'.join(page)+'\nQ'))
    contents=len(objects)
    objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w} {h}] /Resources << /XObject << {" ".join(resources)} >> >> /Contents {contents} 0 R >>'.encode())
    page_number=len(objects)
    objects[0]=b'<< /Type /Catalog /Pages 2 0 R >>'
    objects[1]=f'<< /Type /Pages /Kids [{page_number} 0 R] /Count 1 >>'.encode()
    result=bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n');offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(result));result.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
    start=len(result);result.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:result.extend(f'{offset:010d} 00000 n \n'.encode())
    result.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode())
    return bytes(result)
