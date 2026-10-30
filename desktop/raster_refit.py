"""Use the same Rust full-image raster objective as WASM, through its native ABI."""
import ctypes,json,sys,time
from pathlib import Path
import numpy as np
_runtime=None


def runtime():
    global _runtime
    if _runtime is None:
        path=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'vendor/quality/doctortracer_quality.dll'
        dll=ctypes.CDLL(str(path))
        dll.raster_refit.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_size_t];dll.raster_refit.restype=ctypes.c_void_p
        dll.result_len.restype=ctypes.c_size_t;dll.raster_refit_info.restype=ctypes.c_void_p
        _runtime=dll
    return _runtime


def optimize(svg,source):
    started=time.perf_counter();dll=runtime();a=np.ascontiguousarray(source,np.uint8);h,w=a.shape[:2];encoded=svg.encode('utf-8');buffer=ctypes.create_string_buffer(encoded)
    ptr=dll.raster_refit(buffer,len(encoded),a.ctypes.data,w,h)
    if not ptr:raise ValueError('Raster refit rejected input')
    result=ctypes.string_at(ptr,dll.result_len()).decode('utf-8')
    info=ctypes.string_at(dll.raster_refit_info(),dll.result_len()).decode('utf-8')
    return result,{**json.loads(info),'seconds':time.perf_counter()-started}
