"""Compile the desktop Clipper 6.4.2 audit for WebAssembly."""
import argparse,subprocess,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--emxx',default=shutil.which('em++') or shutil.which('em++.bat'));a=p.parse_args()
if not a.emxx:raise SystemExit('Activate Emscripten 4.0.23')
subprocess.run([a.emxx,'-O3','-fexceptions','-std=c++17',str(root/'core/clipper.cpp'),str(root/'core/wasm_audit.cpp'),'-sMODULARIZE=1','-sEXPORT_ES6=1','-sENVIRONMENT=web,worker,node','-sALLOW_MEMORY_GROWTH=1','-sEXPORTED_FUNCTIONS=["_audit_start","_audit_add","_audit_pairs","_partition_start","_partition_add","_malloc","_free"]','-sEXPORTED_RUNTIME_METHODS=["HEAPF64","UTF8ToString"]','-o',str(root/'web/vendor/audit.mjs')],check=True)
