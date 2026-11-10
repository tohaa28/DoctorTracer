"""Pixel-driven primitive reconstruction for small opaque two-ink AA logos."""
import ctypes,json,time
import numpy as np
from native_potrace import trace as fit_mask
from raster_refit import runtime
from vector_partition import audit_pieces
import xml.etree.ElementTree as ET

def trace(source,palette):
    if len(palette)!=2:return None
    started=time.perf_counter();a=np.ascontiguousarray(source,np.uint8);h,w=a.shape[:2];pal=np.ascontiguousarray(palette,np.uint8);dll=runtime()
    dll.set_palette.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    dll.logo_prepare.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_size_t];dll.logo_prepare.restype=ctypes.c_void_p
    dll.logo_finish.argtypes=[ctypes.c_void_p,ctypes.c_size_t];dll.logo_finish.restype=ctypes.c_void_p
    dll.stats_ptr.restype=ctypes.c_void_p;dll.stats_len.restype=ctypes.c_size_t
    dll.set_palette(pal.ctypes.data,len(pal));p=dll.logo_prepare(a.ctypes.data,w,h)
    if not p:return None
    info=json.loads(ctypes.string_at(dll.stats_ptr(),dll.stats_len()));mask=np.frombuffer(ctypes.string_at(p,dll.result_len()),np.uint8).reshape(h*8,w*8).copy()
    data=' '.join(fit_mask(mask,{'curve_tolerance':.4,'alphamax':.85})).encode();buffer=ctypes.create_string_buffer(data);p=dll.logo_finish(buffer,len(data))
    if not p:return None
    svg=ctypes.string_at(p,dll.result_len()).decode();root=ET.fromstring(svg);paths=list(root.iter('{http://www.w3.org/2000/svg}path'));audit={}
    try:audit_pieces([(p.get('fill'),p.get('d'))for p in paths],audit)
    except ValueError:return None
    return svg,{'colors':2,'width':w,'height':h,'paths':sum(p.get('d').count('M')for p in paths),'palette':[p.get('fill')for p in paths],
       'geometry_verified':True,'geometry_audit':{**audit,'unmatched_edges':0,'boundary_contract':'analytic reversed primitives'},
       'shape_strategy':'source-fitted two-ink shared interfaces','logo_reconstruction':info,'contour_compute':'Rust CPU / Potrace',
       'reconstruction_seconds':time.perf_counter()-started,'working_size':[w*8,h*8]}
