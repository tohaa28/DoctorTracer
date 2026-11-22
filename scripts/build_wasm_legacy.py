"""Build with an activated Emscripten 4.0.23 SDK: python scripts/build_wasm.py."""
import os,shutil,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
emcc=shutil.which('emcc') or shutil.which('emcc.bat')
emxx=shutil.which('em++') or shutil.which('em++.bat')
if not emcc or not emxx:raise SystemExit('Activate Emscripten SDK first (emsdk_env).')
src=root/'core/potrace-1.16/src';build=root/'build/wasm';build.mkdir(parents=True,exist_ok=True)
objects=[]
for name in ['curve','trace','decompose','potracelib']:
 obj=build/(name+'.o');subprocess.run([emcc,'-O3','-DVERSION="1.16"','-I'+str(src),'-c',str(src/(name+'.c')),'-o',str(obj)],check=True);objects.append(str(obj))
subprocess.run([emxx,'-O3','-std=c++17','-fexceptions','-I'+str(src),str(root/'core/tracer.cpp'),*objects,'-sMODULARIZE=1','-sEXPORT_ES6=1','-sEXPORT_NAME=createTracer','-sENVIRONMENT=web,worker,node','-sALLOW_MEMORY_GROWTH=1','-sMAXIMUM_MEMORY=1073741824','-sEXPORTED_FUNCTIONS=["_trace_rgba","_trace_paths","_malloc","_free"]','-sEXPORTED_RUNTIME_METHODS=["UTF8ToString","HEAPU8"]','-o',str(root/'web/tracer.mjs')],check=True)
print('Built web/tracer.mjs + web/tracer.wasm')
