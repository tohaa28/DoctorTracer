"""Build the Rust WASM core, then assemble a static GitHub Pages artifact.

rustup target add wasm32-unknown-unknown
python scripts/build_wasm.py
"""
import argparse,os,shutil,subprocess,json,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--cargo',default=shutil.which('cargo'));parser.add_argument('--toolchain');args=parser.parse_args()
if not args.cargo:raise SystemExit('Install Rust from https://rustup.rs and add wasm32-unknown-unknown.')
command=[args.cargo]+(['+'+args.toolchain] if args.toolchain else [])
env=os.environ.copy();env['RUSTFLAGS']=env.get('RUSTFLAGS','')+' -C link-arg=--max-memory=1073741824'
subprocess.run(command+['build','--manifest-path',str(root/'rust/Cargo.toml'),'--target','wasm32-unknown-unknown','--release','--locked'],check=True,cwd=root,env=env)
shutil.copy2(root/'rust/target/wasm32-unknown-unknown/release/doctortracer_wasm.wasm',root/'web/doctortracer.wasm')
metadata=json.loads(subprocess.check_output(command+['metadata','--manifest-path',str(root/'rust/Cargo.toml'),'--format-version','1','--locked'],cwd=root,text=True,encoding='utf8'))
licenses=['DoctorTracer Desktop WASM 0.16\n\nRust desktop algorithm port: MIT; OpenCV palette adaptation: Apache-2.0. Potrace 1.16: GPL-2.0-or-later. Skia PathKit: BSD. Clipper 6.4.2: Boost-1.0. Combined browser distribution: GPL-3.0-or-later.\nSource: https://github.com/tohaa28/DoctorTracer/tree/spatial-photo-preview\n\n', (root/'desktop/LICENSE').read_text(encoding='utf8'),(root/'licenses/GPL-3.0.txt').read_text(encoding='utf8')]
for notice in ['APACHE-2.0.txt','BOOST-1.0.txt','SKIA-PATHKIT.txt']:
 licenses.append((root/'licenses'/notice).read_text(encoding='utf8'))
licenses.append('Clipper JavaScript translation: Timo, 2017. JSBN: Copyright (c) 2005 Tom Wu. See preserved notices in web/vendor/clipper.mjs.\n')
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
files=['gpu-contours.mjs','palette-ui.mjs','index.html','style.css','app.js','worker.js','rust-tracer.mjs','doctortracer.wasm','gpu.js','exports.mjs','icons.js','geometry.mjs','paths.mjs','desktop-curves.mjs','preview.mjs','zip.mjs','diagnostics.html','desktop-layout.json','demo.png','LICENSE.txt']
for name in files:shutil.copy2(root/'web'/name,site/name)
for folder in ['vendor','desktop-icons']:shutil.copytree(root/'web'/folder,site/folder,dirs_exist_ok=True)
# Version the deployed resource URLs, so an older browser cache cannot mix ABIs.
for path in site.rglob('*'):
 if '.git' in path.parts or path.suffix not in ('.js','.mjs','.html'):continue
 text=path.read_text(encoding='utf8')
 text=re.sub(r"(['\"])(\./[^'\"]+\.(?:m?js|wasm|css))\1",lambda m:m[1]+m[2]+'?v=0.16.3'+m[1],text)
 text=re.sub(r'(src|href)="([^"?]+\.(?:m?js|css))"',lambda m:m[1]+'="'+m[2]+'?v=0.16.3"',text)
 text=text.replace("frame.src='./'","frame.src='./?v=0.16.3'")
 path.write_text(text,encoding='utf8')
(site/'.nojekyll').write_text('')
print('Built Rust WASM and build/site static artifact')
