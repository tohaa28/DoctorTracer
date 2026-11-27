
"""Independent audit for two intensity-based postprocessing operations."""
import ctypes,json,xml.etree.ElementTree as ET
from raster_refit import runtime
from vector_partition import audit_pieces
from regularize import regularize

def intermediate(svg,strength):
    power=max(0,min(100,int(strength)))
    if not power:return svg,dict(removed_elements=0,protected_elements=0,applied_strength=0)
    dll=runtime();dll.result_intermediate.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint];dll.result_intermediate.restype=ctypes.c_void_p
    dll.stats_ptr.restype=ctypes.c_void_p;dll.stats_len.restype=ctypes.c_size_t
    data=svg.encode();buffer=ctypes.create_string_buffer(data)
    for amount in dict.fromkeys(max(1,round(power/2**i)) for i in range(5)):
        ptr=dll.result_intermediate(buffer,len(data),amount)
        if not ptr:continue
        candidate=ctypes.string_at(ptr,dll.result_len()).decode();stats=json.loads(ctypes.string_at(dll.stats_ptr(),dll.stats_len()));audit={}
        try:
            root=ET.fromstring(candidate);audit_pieces([(p.get('fill'),p.get('d')) for p in root.iter('{http://www.w3.org/2000/svg}path')],audit)
            return candidate,{**stats,'applied_strength':amount,'limited':amount!=power,'geometry':audit}
        except (ValueError,ET.ParseError):continue
    return svg,dict(removed_elements=0,protected_elements=0,applied_strength=0,limited=True,rejected=True)

def reduce_nodes(svg,strength):
    power=max(0,min(100,int(strength)))
    if not power:return svg,dict(nodes_before=0,nodes_after=0,reduction=0,applied_tolerance=0)
    candidate,stats=regularize(svg,power/50,True,True,True)
    before=stats['nodes_before'];after=stats['nodes_after']
    if not before>after:return svg,{**stats,'nodes_after':before,'reduction':0}
    return candidate,{**stats,'reduction':100*(before-after)/before}
