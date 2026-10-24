"""Build the Windows x64 Potrace DLL with official Zig 0.15.2 on PATH."""
import shutil,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];src=root/'core/potrace-1.16/src'
build=root/'build/native';build.mkdir(parents=True,exist_ok=True)
zig=shutil.which('zig')
if not zig:raise SystemExit('Put Zig 0.15.2 on PATH, then retry.')
subprocess.run([zig,'cc','-shared','-O2','-g0','-s','-target','x86_64-windows-gnu','-DVERSION="1.16"','-DHAVE_INTTYPES_H','-I'+str(src),*[str(src/(name+'.c')) for name in ['curve','trace','decompose','potracelib']],str(root/'core/native_svg.c'),'-Wl,--export-all-symbols','-o',str(build/'potrace.dll')],check=True)
shutil.copy2(build/'potrace.dll',root/'desktop/vendor/potrace/potrace.dll')
