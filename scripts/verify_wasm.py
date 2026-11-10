"""Run release quality gates against the desktop implementation.

python scripts/verify_wasm.py [--image input.png --image photo.jpg]
The images, golden vectors, stage dumps and complete reports stay in build/.
"""
import argparse,subprocess,sys,json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--image',action='append',default=[]);a=p.parse_args();images=sum((['--image',v] for v in a.image),[])
for command in [['node','tests/rust_wasm.mjs'],[sys.executable,'tests/desktop_parity.py',*images],[sys.executable,'tests/curves_parity.py',*images]]:subprocess.run(command,cwd=root,check=True)
reports={}
for name,folder in [('automatic','parity'),('limited','curves-parity')]:
 rows=json.loads((root/'build'/folder/'report.json').read_text(encoding='utf8'));reports[name]={'cases':len(rows),'max_rgba_mae':max(row['rgba_mae'] for row in rows),'threshold':.02 if name=='automatic' else .25}
reports['wasm_sha256']=hashlib.sha256((root/'web/doctortracer.wasm').read_bytes()).hexdigest();reports['desktop_sources']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'desktop').glob('*.py')};(root/'build/wasm-quality-gate.json').write_text(json.dumps(reports,indent=2),encoding='utf8');print('Release gates passed. Browser/WebGPU/layout gates: tests/browser.html')
