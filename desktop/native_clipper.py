"""Shared C++ integer geometry backend, also compiled to WebAssembly."""
import ctypes
from pathlib import Path

def partition(items,width,height):
    from vector_partition import polygon_paths,polygon_data
    dll=ctypes.CDLL(str(Path(__file__).with_name('vendor')/'quality/doctortracer_clipper.dll'))
    dll.partition_start.argtypes=[ctypes.c_double,ctypes.c_double]
    dll.partition_add.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.c_int]
    dll.partition_add.restype=ctypes.c_char_p
    dll.partition_set_group.argtypes=[ctypes.c_int]
    dll.partition_verify.restype=ctypes.c_double
    def encode(paths):
        data=[]
        for p in paths:
            data.append(len(p));data.extend(v for point in p for v in point)
        return (ctypes.c_double*len(data))(*data)
    dll.partition_start(width,height);pieces=[];colors={}
    for color,p in reversed(items):
        dll.partition_set_group(colors.setdefault(color,len(colors)))
        data=encode(polygon_paths(p))
        value=dll.partition_add(data,len(data))
        if value is None:raise RuntimeError('Native integer partition failed')
        if value:pieces.append((color,value.decode('ascii')))
    area=dll.partition_verify()
    if area<0 or area>.0001:raise ValueError('Native recovered geometry failed intersection audit')
    return pieces
