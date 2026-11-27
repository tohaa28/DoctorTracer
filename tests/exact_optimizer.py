import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from exact_optimizer import optimize_path,optimize_svg
cases=json.loads(Path(__file__).with_name('exact_optimizer_cases.json').read_text(encoding='utf-8'))
for t in cases:
    r=optimize_path(t['d'])
    assert r['before']-r['after']==t['removed'],(t,r)
    assert r['d']==t.get('expected',t['d']),(t,r)
    assert r['skipped']==t.get('skipped',0),(t,r)
    assert optimize_path(r['d'])['d']==r['d'],t
base='<svg xmlns="http://www.w3.org/2000/svg" width="512" height="400"><g fill="#ff0000"><path fill="#ff0000" d="'+cases[0]['d']+'"/></g></svg>'
candidate,stats=optimize_svg(base)
assert stats['removed']==3
assert candidate==base.replace(cases[0]['d'],cases[0]['expected'])
try:optimize_svg('<svg stroke="red"><path d="M0 0 L1 0 Z"/></svg>')
except ValueError:pass
else:raise AssertionError('stroke not rejected')
print('PASS exact desktop geometry:',len(cases),'cases')
