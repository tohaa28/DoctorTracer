"""Build the identical Rust raster objective as a Windows DLL (GNU toolchain)."""
import argparse,subprocess,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--cargo',default=shutil.which('cargo'));p.add_argument('--toolchain',default='1.99.1-x86_64-pc-windows-gnu');a=p.parse_args()
root=Path(__file__).resolve().parents[1]
subprocess.run([a.cargo,'+'+a.toolchain,'build','--manifest-path',str(root/'rust/Cargo.toml'),'--locked','--release','--target','x86_64-pc-windows-gnu'],cwd=root,check=True)
target=root/'desktop/vendor/quality/doctortracer_quality.dll';target.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(root/'rust/target/x86_64-pc-windows-gnu/release/doctortracer_wasm.dll',target)
print('Built',target)
