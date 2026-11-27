"""Package 0.21.8 with the newly rebuilt Rust WASM and pinned prior decoder assets."""
import sys,shutil,re,json,hashlib,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
base=root/'published-site';site=root/'build/site'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((base/'version.json').read_text(encoding='utf8'))
assert old['version']=='0.21.7-wasm-preview'
assert old['sourceCommit']=='42efc25c733db8fe379ad02ebb9773861438807c'
assert old['wasmSha256']==sha(base/'doctortracer.wasm')
assert sha(root/'web/doctortracer.wasm')!=old['wasmSha256'], 'Expected newly rebuilt native WASM'
assert old['auditWasmSha256']==sha(base/'vendor/audit.wasm')==sha(root/'web/vendor/audit.wasm')
if site.exists():shutil.rmtree(site)
shutil.copytree(base,site,ignore=shutil.ignore_patterns('.git'))
for n in ['app.js','worker.js','index.html','exact-optimizer.mjs','LICENSE.txt','doctortracer.wasm','input-image.mjs','rust-tracer.mjs','gpu.js','gpu-contours.mjs','pixel-grid-trace.mjs','color-node-tools.mjs']:
    shutil.copy2(root/'web'/n,site/n)
for p in site.rglob('*'):
    if p.suffix not in ('.js','.mjs','.html') or 'pdfjs' in p.parts or p.name=='tiff.mjs':continue
    text=p.read_text(encoding='utf8').replace('?v=0.21.7','?v=0.21.8')
    text=re.sub(r"(['\"])(\./[^'\"]+\.(?:m?js|wasm|css))\1",lambda m:m[1]+m[2]+'?v=0.21.8'+m[1],text)
    text=re.sub(r'(src|href)="([^"?]+\.(?:m?js|css))"',lambda m:m[1]+'="'+m[2]+'?v=0.21.8"',text)
    text=text.replace("frame.src='./'","frame.src='./?v=0.21.8'")
    p.write_text(text,encoding='utf8')
old.update(version='0.21.8-wasm-preview',wasmSha256=sha(site/'doctortracer.wasm'),sourceCommit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip())
(site/'version.json').write_text(json.dumps(old,indent=2)+'\n',encoding='utf8')
assert sha(site/'doctortracer.wasm')==old['wasmSha256']
assert sha(site/'vendor/audit.wasm')==old['auditWasmSha256']
assert 'Точная оптимизация узлов' in (site/'app.js').read_text(encoding='utf8')
assert './exact-optimizer.mjs?v=0.21.8' in (site/'worker.js').read_text(encoding='utf8')
(site/'.nojekyll').touch()
print(json.dumps(old,ensure_ascii=False))
