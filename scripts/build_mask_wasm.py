"""Build shared desktop Potrace mask core with Emscripten 4.0.23."""
import argparse,os,shutil,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];parser=argparse.ArgumentParser();parser.add_argument('--emcc',default=shutil.which('emcc') or shutil.which('emcc.bat'));args=parser.parse_args()
if not args.emcc:raise SystemExit('Activate Emscripten 4.0.23 first')
src=root/'core/potrace-1.16/src'
subprocess.run([args.emcc,'-O3','-DVERSION="1.16"','-I'+str(src),*[str(src/(name+'.c')) for name in ['curve','trace','decompose','potracelib']],str(root/'core/wasm_mask.c'),'-sMODULARIZE=1','-sEXPORT_ES6=1','-sENVIRONMENT=web,worker,node','-sALLOW_MEMORY_GROWTH=1','-sMAXIMUM_MEMORY=1073741824','-sEXPORTED_FUNCTIONS=["_trace_mask","_malloc","_free"]','-sEXPORTED_RUNTIME_METHODS=["UTF8ToString","HEAPU8"]','-o',str(root/'web/vendor/mask.mjs')],check=True)
