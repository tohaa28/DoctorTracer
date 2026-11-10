"""Build the shared Windows integer geometry backend with Zig 0.15.2."""
import argparse,subprocess,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--zig',default=shutil.which('zig'));a=p.parse_args()
if not a.zig:raise SystemExit('Provide official Zig 0.15.2 with --zig')
subprocess.run([a.zig,'c++','-shared','-O3','-g0','-s','-target','x86_64-windows-gnu',str(root/'core/clipper.cpp'),str(root/'core/wasm_audit.cpp'),'-Wl,--export-all-symbols','-o',str(root/'desktop/vendor/quality/doctortracer_clipper.dll')],check=True,cwd=root)
