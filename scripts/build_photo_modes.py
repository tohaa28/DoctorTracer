"""Build the exact CPU mode filter with Zig 0.15.2 on PATH."""
import shutil,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
zig=shutil.which('zig')
if not zig:raise SystemExit('Put Zig 0.15.2 on PATH, then retry.')
target=root/'desktop/vendor/filters/photo_modes.dll';target.parent.mkdir(parents=True,exist_ok=True)
subprocess.run([zig,'cc','-shared','-O3','-g0','-s','-target','x86_64-windows-gnu',
               str(root/'core/photo_modes.c'),'-o',str(target)],check=True)
