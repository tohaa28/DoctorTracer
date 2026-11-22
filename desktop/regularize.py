"""Global shared-chain straightening and Bezier regularization."""
import ctypes,json,xml.etree.ElementTree as ET
from raster_refit import runtime
from vector_partition import audit_pieces

def regularize(svg,tolerance=.15,straight=True,curved=True,protect=True):
    dll=runtime();dll.result_regularize.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_double,ctypes.c_uint];dll.result_regularize.restype=ctypes.c_void_p
    dll.stats_ptr.restype=ctypes.c_void_p;dll.stats_len.restype=ctypes.c_size_t
    data=svg.encode();buffer=ctypes.create_string_buffer(data);flags=int(straight)|int(curved)<<1|int(protect)<<2
    valid=False
    for amount in [tolerance/(2**i) for i in range(5)]+[0]:
        ptr=dll.result_regularize(buffer,len(data),amount,flags)
        if not ptr:continue
        valid=True
        candidate=ctypes.string_at(ptr,dll.result_len()).decode();stats=json.loads(ctypes.string_at(dll.stats_ptr(),dll.stats_len()));audit={}
        try:
            root=ET.fromstring(candidate);audit_pieces([(p.get('fill'),p.get('d'))for p in root.iter('{http://www.w3.org/2000/svg}path')],audit)
            return candidate,{**stats,'applied_tolerance':amount,'limited':amount!=tolerance,'geometry':audit}
        except (ValueError,ET.ParseError):continue
    if not valid:raise ValueError('Неподдерживаемая геометрия результата')
    return svg,{'nodes_before':0,'nodes_after':0,'straightened':0,'curves_fitted':0,'rejected':True,'limited':True}
