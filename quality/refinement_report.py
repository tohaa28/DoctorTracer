"""Release comparison; preserve adverse results and distinguish quality from parity."""
import argparse,json,html
from pathlib import Path
import numpy as np
from PIL import Image
import bench

def main():
    p=argparse.ArgumentParser();p.add_argument('--corpus',type=Path,required=True);args=p.parse_args();root=args.corpus.resolve()
    reports={e:bench.read(root/f'reports/{e}-quality-release/report.json') for e in ['desktop','wasm']}
    old={e:bench.read(root/f'reports/{e}-public-v2/report.json') for e in reports}
    assert all(r['summary']['coverage_complete'] and len(r['cases'])==48 for r in reports.values())
    parity=[]
    for a,b in zip(reports['desktop']['cases'],reports['wasm']['cases']):
        assert (a['image'],a['profile'],a['source_sha256'])==(b['image'],b['profile'],b['source_sha256'])
        ac=dict(a['config']);bc=dict(b['config']);ac.pop('compute',None);bc.pop('compute',None);assert ac==bc
        key=a['image']+'--'+a['profile'];left=np.asarray(Image.open(root/f'runs/desktop-quality-final/{key}.png')).astype(float);right=np.asarray(Image.open(root/f'runs/wasm-quality-final/{key}.png')).astype(float)
        mae=float(np.abs(left-right).mean());limit=.25 if a['profile'].startswith('graphic') else .02
        parity.append({'case':key,'rgba_mae':mae,'limit':limit,'passed':mae<=limit,'recommended_domain':a['recommended_domain']})
    truth={e:float(np.mean([r['vector_truth_4x']['candidate']['rgb_mae_white'] for r in reports[e]['cases'] if r['profile']=='graphic-medium-9' and r.get('vector_truth_4x')])) for e in reports}
    performance=bench.read(bench.ROOT/'build/quality-refinement/performance.json')
    result={'versions':{'desktop':'0.13.0-preview','wasm':'0.15.0-wasm-preview'},'cases_per_engine':48,'reference':'Vector Magic Desktop 1.15','before':{e:r['summary'] for e,r in old.items()},'after':{e:r['summary'] for e,r in reports.items()},'parity':parity,'truth_graphic_4x_candidate_mae':truth,'performance':performance,'notice':'Preview: quality is not uniformly improved. The public corpus was used during development; no unseen-set claim. Local coverage optimization is not a global full-image raster optimizer.'}
    bench.write(bench.ROOT/'docs/QUALITY_015_RESULTS.json',result)
    out=root/'reports/quality-release';out.mkdir(exist_ok=False);bench.write(out/'summary.json',result)
    rows=''
    for key,now in reports['desktop']['summary']['by_profile_category'].items():
        profile,category=key.split('/')
        if (category=='photo')!=profile.startswith('photo'):continue
        before=old['desktop']['summary']['by_profile_category'][key];change=(before['mean_rgb_mae_white']-now['mean_rgb_mae_white'])/before['mean_rgb_mae_white']*100
        rows+=f'<tr><td>{html.escape(key)}</td><td>{before["mean_rgb_mae_white"]:.3f}</td><td>{now["mean_rgb_mae_white"]:.3f}</td><td>{change:+.1f}%</td><td>{now["mean_region_boundary_f1"]:.4f}</td></tr>'
    failures=[r for r in parity if not r['passed']]
    content='''<!doctype html><meta charset="utf-8"><title>DoctorTracer 0.13 / 0.15 — результаты</title><style>body{font:16px Segoe UI,system-ui;background:#f1f5fa;color:#192e48;margin:30px}section{padding:22px;background:white;border:1px solid #ccd6e2;border-radius:8px;margin:20px 0}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:12px;border-bottom:1px solid #ddd}a{color:#0759a4}p{line-height:1.6}pre{white-space:pre-wrap}.warning{color:#9a3f24}</style><h1>DoctorTracer Windows 0.13 / WASM 0.15</h1><p>12 входов · 48 реальных эталонов VM 1.15 · по 48 новых результатов обеих версий.</p><section><h2>Ошибка относительно Vector Magic, 0–255 ↓</h2><p>Показаны соответствующие типу входа профили. Изменение — снижение MAE, положительное значение лучше.</p><table><tr><th>Профиль / тип</th><th>До</th><th>После</th><th>Изменение</th><th>F1 после ↑</th></tr>'''+rows+'''</table><p class="warning">Нет равенства с Vector Magic. Chelsea с ограниченной палитрой ухудшилась; это preview с явными ограничениями. Подбор и проверка выполнялись на уже известном наборе.</p></section>'''
    content+='<section><h2>Что изменено</h2><p>Адаптивная палитра, взвешенное совместное уточнение кластеров и их цветов, субпиксельная коррекция общего графа, локальный подбор скругления Безье по покрытию, защита контрастных и тонких малых областей. Явные RGB сохраняются. В Windows локальная функция ошибки вычисляется OpenCL FP64; WebGPU ускоряет существующие фильтры, назначение областей и подходящие общие контуры. Глобальная оптимизация всего растра не заявляется.</p></section>'
    content+='<section><h2>Проверки версий и GPU</h2><p>Превышений допуска Windows/WASM: '+str(len(failures))+'/48.</p><pre>'+html.escape(json.dumps(failures,ensure_ascii=False,indent=2))+'</pre><p>Скорость CPU/GPU измерена на текущем алгоритме, после прогрева, три чередующихся замера; SVG совпадают побайтно.</p><pre>'+html.escape(json.dumps(performance,ensure_ascii=False,indent=2))+'</pre></section>'
    content+='<section><h2>Все сравнения</h2><p><a href="../desktop-quality-release/index.html">Windows: исходник / VM / до / после</a> · <a href="../wasm-quality-release/index.html">WASM: исходник / VM / до / после</a> · <a href="summary.json">Числа JSON</a></p></section>'
    (out/'index.html').write_text(content,encoding='utf-8');print(json.dumps({'parity_failures':failures,'truth':truth},indent=2))
if __name__=='__main__':main()
