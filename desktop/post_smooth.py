"""Optional finished-result module, backed by the same Rust code as WASM."""
import ctypes,json,math,xml.etree.ElementTree as ET
from pathlib import Path

def smooth(svg,strength=35,sharp=True):
    if not strength:return svg,{'nodes':0,'moved':0,'applied_strength':0}
    from vector_partition import audit_pieces
    dll=ctypes.CDLL(str(Path(__file__).with_name('vendor')/'quality/doctortracer_quality.dll'))
    dll.result_smooth.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint];dll.result_smooth.restype=ctypes.c_void_p
    for name in ['result_len','stats_len']:getattr(dll,name).restype=ctypes.c_size_t
    dll.stats_ptr.restype=ctypes.c_void_p
    source=svg.encode('utf8');buffer=ctypes.create_string_buffer(source)
    for attempt in range(5):
        amount=max(1,math.floor(strength/(2**attempt)+0.5))
        ptr=dll.result_smooth(buffer,len(source),amount,int(sharp))
        if not ptr:continue
        candidate=ctypes.string_at(ptr,dll.result_len()).decode('utf8')
        stats=json.loads(ctypes.string_at(dll.stats_ptr(),dll.stats_len()).decode('utf8'))
        try:
            root=ET.fromstring(candidate);audit={}
            audit_pieces([(p.get('fill'),p.get('d')) for p in root.iter('{http://www.w3.org/2000/svg}path')],audit)
            return candidate,{**stats,'applied_strength':amount,'limited':amount!=strength,'geometry':audit}
        except (ValueError,ET.ParseError):continue
    return svg,{'nodes':0,'moved':0,'applied_strength':0,'limited':True}
