"""Finished-vector island cleanup and bounded shared-curve simplification."""
import ctypes,json,xml.etree.ElementTree as ET
from pathlib import Path

def clean(svg,min_area=4,tolerance=.25,protect=True):
    from vector_partition import audit_pieces
    dll=ctypes.CDLL(str(Path(__file__).with_name('vendor')/'quality/doctortracer_quality.dll'))
    dll.result_clean.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_double,ctypes.c_double,ctypes.c_uint];dll.result_clean.restype=ctypes.c_void_p
    for name in ['result_len','stats_len']:getattr(dll,name).restype=ctypes.c_size_t
    dll.stats_ptr.restype=ctypes.c_void_p
    data=svg.encode('utf8');buffer=ctypes.create_string_buffer(data)
    for amount in [tolerance/(2**i) for i in range(5)]+[0]:
        ptr=dll.result_clean(buffer,len(data),float(min_area),float(amount),int(protect))
        if not ptr:raise ValueError('Неподдерживаемая геометрия готового вектора')
        candidate=ctypes.string_at(ptr,dll.result_len()).decode('utf8');stats=json.loads(ctypes.string_at(dll.stats_ptr(),dll.stats_len()).decode('utf8'))
        try:
            audit={};root=ET.fromstring(candidate)
            audit_pieces([(p.get('fill'),p.get('d')) for p in root.iter('{http://www.w3.org/2000/svg}path')],audit)
            return candidate,{**stats,'applied_tolerance':amount,'limited':amount!=tolerance,'geometry':audit}
        except (ValueError,ET.ParseError):continue
    return svg,{'nodes_before':0,'nodes_after':0,'removed_elements':0,'protected_elements':0,'limited':True,'rejected':True}
