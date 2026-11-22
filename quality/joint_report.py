"""Release 016 report; keep development, blind validation and stress cases separate."""
import json, html
from pathlib import Path
import numpy as np
from PIL import Image
import bench

def main():
    result={'versions':{'desktop':'0.14.0-preview','wasm':'0.16.0-wasm-preview'},
            'reference':'Vector Magic Desktop 1.15', 'algorithm_freeze':'88d2263',
            'notice':'Six new inputs selected before tuning; quality parameters frozen before their evaluation. Performance/robustness fixes followed evaluation. No full old-WASM holdout aggregate: that run was interrupted. Full-image refit searches three shared tensions against the filtered working raster, not every control point. Metrics do not establish equivalence to Vector Magic.', 'sets':{}}
    parity=[]; sections=[]
    for name,folder,native in [('development','quality-public-v2','desktop-joint-release-016'),('unseen','quality-holdout-016','desktop-joint-release-016')]:
        root=bench.ROOT/'build'/folder
        reports={e:bench.read(root/f'reports/{run}/report.json') for e,run in [('desktop',native),('wasm','wasm-joint-release-016')]}
        for r in reports.values():assert r['summary']['coverage_complete'] and not r['summary']['errors']
        result['sets'][name]={e:r['summary'] for e,r in reports.items()}
        rows=''
        for c in reports['desktop']['cases']:
            key=c['image']+'--'+c['profile']; a=np.asarray(Image.open(root/f'runs/{native}/{key}.png')).astype(float);b=np.asarray(Image.open(root/f'runs/wasm-joint-release-016/{key}.png')).astype(float)
            error=float(np.abs(a-b).mean());limit=.25 if c['profile'].startswith('graphic') else .02
            parity.append({'set':name,'case':key,'rgba_mae':error,'limit':limit,'passed':error<=limit})
        for key,now in reports['desktop']['summary']['by_profile_category'].items():
            profile,category=key.split('/')
            if (category=='photo')!=profile.startswith('photo'):continue
            selected=[c for c in reports['desktop']['cases'] if c['profile']==profile and c['category']==category]
            before=float(np.mean([c['baseline_metrics']['rgb_mae_white'] for c in selected]))
            rows+=f'<tr><td>{html.escape(key)}</td><td>{before:.3f}</td><td>{now["mean_rgb_mae_white"]:.3f}</td><td>{now["mean_region_boundary_f1"]:.4f}</td></tr>'
        sections.append(f'<section><h2>{"Разработка: 12 входов / 48 режимов" if name=="development" else "Новые 6 входов / 24 режима"}</h2><table><tr><th>Профиль / тип</th><th>MAE до ↓</th><th>MAE после ↓</th><th>F1 после ↑</th></tr>{rows}</table><p>Регрессии Windows: {html.escape(str(reports["desktop"]["summary"]["regressions"]))}</p><p><a href="../{folder}/reports/{native}/index.html">Windows: исходник / VM / до / после</a> · <a href="../{folder}/reports/wasm-joint-release-016/index.html">WASM / VM</a></p></section>')
    result['parity']=parity;result['parity_failures']=[p for p in parity if not p['passed']]
    result['performance']=bench.read(bench.ROOT/'build/joint-raster/performance016.json')
    bench.write(bench.ROOT/'docs/QUALITY_016_RESULTS.json',result)
    out=bench.ROOT/'build/quality-release-016';out.mkdir(exist_ok=True)
    text='<!doctype html><meta charset="utf-8"><title>DoctorTracer 0.14 / 0.16 — результаты</title><style>body{font:16px Segoe UI;background:#eff3f8;color:#20334c;margin:28px}section{background:white;padding:22px;border:1px solid #ccd7e4;margin:20px 0}table{border-collapse:collapse;width:100%}td,th{padding:12px;border-bottom:1px solid #ddd;text-align:left}p{line-height:1.6}a{color:#0865ad}</style><h1>DoctorTracer Windows 0.14 / WASM 0.16</h1><p>18 входов · 72 реальных эталона Vector Magic · 144 результата DoctorTracer</p><p>Совместное уточнение палитры и сегментации · выбор кривых по полному растру · GPU с проверкой точности</p>'
    text+=''.join(sections)+f'<section><h2>Переносимость и ограничения</h2><p>Windows / WASM: {len(parity)-len(result["parity_failures"])}/{len(parity)} в допуске. Максимальная RGBA MAE: {max(p["rgba_mae"] for p in parity):.6f}.</p><p>На новом наборе параметры качества не подстраивались; после заморозки исправлялись скорость и устойчивость. Прежняя WASM на новом наборе не завершила полный прогон, поэтому её сводные результаты не приводятся. Равенство с Vector Magic не достигнуто. На новом наборе Hubble / режим рисунка ухудшается (MAE 3.578 → 5.082); Camera / среднее фото со свободной палитрой не проходит межверсионный допуск из-за разного отката после аудита. Подбор кривых проверяет три общих значения натяжения, а не оптимизирует все контрольные точки.</p></section>'
    (out/'index.html').write_text(text,encoding='utf8');print(json.dumps({'parity_failures':result['parity_failures'],'report':str(out)},indent=2))
if __name__=='__main__':main()
