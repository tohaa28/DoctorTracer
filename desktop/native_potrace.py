"""MIT licensed binding; the linked Potrace 1.16 library is GPL-2.0-or-later."""
import ctypes as C
import sys
from pathlib import Path
from functools import lru_cache
import numpy as np

class Bitmap(C.Structure):
    _fields_=[('w',C.c_int),('h',C.c_int),('dy',C.c_int),('map',C.POINTER(C.c_uint32))]

@lru_cache(maxsize=1)
def runtime():
    path=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'vendor/potrace/potrace.dll'
    lib=C.CDLL(str(path))
    lib.doctor_version.restype=C.c_char_p
    if b'1.16' not in lib.doctor_version():raise RuntimeError('Unsupported Potrace library')
    lib.doctor_svg.argtypes=[C.POINTER(Bitmap),C.c_double,C.c_double]
    lib.doctor_svg.restype=C.c_void_p
    lib.doctor_free.argtypes=[C.c_void_p]
    lib.doctor_free.restype=None
    return lib

def trace(mask,cfg):
    if mask.ndim!=2 or not mask.size:return []
    h,w=mask.shape
    if w*h>20000000:raise ValueError('Tracing mask is too large')
    dy=(w+31)//32
    padded=np.pad(mask,((0,0),(0,dy*32-w)))
    words=np.packbits(padded,axis=1).view('>u4').astype(np.uint32).copy()
    bitmap=Bitmap(w,h,dy,words.ctypes.data_as(C.POINTER(C.c_uint32)))
    lib=runtime()
    pointer=lib.doctor_svg(C.byref(bitmap),float(cfg.get('curve_tolerance',.4)),float(cfg.get('alphamax',1.2)))
    if not pointer:raise RuntimeError('Potrace curve fitting failed')
    try:
        data=C.string_at(pointer).decode('ascii')
        return [data] if data else []
    finally:
        lib.doctor_free(pointer)
