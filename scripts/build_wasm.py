"""Build the Rust WASM core, then assemble a static GitHub Pages artifact.

rustup target add wasm32-unknown-unknown
python scripts/build_wasm.py
"""
import argparse,os,shutil,subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--cargo',default=shutil.which('cargo'));parser.add_argument('--toolchain');args=parser.parse_args()
if not args.cargo:raise SystemExit('Install Rust from https://rustup.rs and add wasm32-unknown-unknown.')
command=[args.cargo]+(['+'+args.toolchain] if args.toolchain else [])
env=os.environ.copy();env['RUSTFLAGS']=env.get('RUSTFLAGS','')+' -C link-arg=--max-memory=1073741824'
subprocess.run(command+['build','--manifest-path',str(root/'rust/Cargo.toml'),'--target','wasm32-unknown-unknown','--release','--locked'],check=True,cwd=root,env=env)
shutil.copy2(root/'rust/target/wasm32-unknown-unknown/release/doctortracer_wasm.wasm',root/'web/doctortracer.wasm')
metadata=json.loads(subprocess.check_output(command+['metadata','--manifest-path',str(root/'rust/Cargo.toml'),'--format-version','1','--locked'],cwd=root,text=True,encoding='utf8'))
licenses=['DoctorTracer Rust WASM 0.11\n\nRust core: MIT. Combined browser distribution: GPL-3.0-or-later.\nSource: https://github.com/tohaa28/DoctorTracer/tree/spatial-photo-preview\n\n', (root/'desktop/LICENSE').read_text(encoding='utf8'),(root/'licenses/GPL-3.0.txt').read_text(encoding='utf8')]
for package in sorted(metadata['packages'],key=lambda p:p['name']):
 if package['name']=='doctortracer-wasm':continue
 folder=Path(package['manifest_path']).parent
 licenses.append('\n\n=== '+package['name']+' '+package['version']+' ('+str(package['license'])+') ===\n')
 files=[p for p in folder.iterdir() if p.is_file() and (p.name.lower().startswith(('license','licence','copying','copyright')))]
 if not files and package['license']=='Apache-2.0':
  licenses.append('Attribution: '+', '.join(package.get('authors',[]))+'\n')
  files=[root/'licenses/APACHE-2.0.txt']
 if not files:raise SystemExit('Missing dependency license: '+package['name'])
 for p in sorted(files):licenses.append(p.read_text(encoding='utf8',errors='replace'))
(root/'web/LICENSE.txt').write_text('\n'.join(licenses),encoding='utf8')
site=root/'build/site';site.mkdir(parents=True,exist_ok=True)
files=['index.html','style.css','app.js','worker.js','rust-tracer.mjs','doctortracer.wasm','gpu.js','exports.mjs','icons.js','demo.png','LICENSE.txt']
for name in files:shutil.copy2(root/'web'/name,site/name)
(site/'.nojekyll').write_text('')
print('Built Rust WASM and build/site static artifact')
