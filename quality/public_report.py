"""Join two independent VM comparisons, parity gates and a clearly separated oracle."""
import argparse,html,json,statistics
from pathlib import Path
import numpy as np
from PIL import Image
import bench

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--corpus',type=Path,required=True);args=parser.parse_args()
    folder=args.corpus.resolve();corpus=bench.load(folder);desktop=bench.read(folder/'reports/desktop-public-v2/report.json');wasm=bench.read(folder/'reports/wasm-public-v2/report.json')
    if not desktop['summary']['coverage_complete'] or not wasm['summary']['coverage_complete']:raise ValueError('Reference coverage is incomplete')
    expected=len(corpus['images'])*len(corpus['enabled_profiles'])
    if len(desktop['cases'])!=expected or len(wasm['cases'])!=expected:raise ValueError('The full declared matrix is required')
    for report in [desktop,wasm]:
        keys=[(r['image'],r['profile']) for r in report['cases']]
        if len(set(keys))!=expected:raise ValueError('Duplicate cases in report')
    parity=[]
    for a,b in zip(desktop['cases'],wasm['cases']):
        if (a['image'],a['profile'],a['source_sha256'],a['config'])!=(b['image'],b['profile'],b['source_sha256'],b['config']):raise ValueError('Candidate inputs/settings differ')
        key=a['image']+'--'+a['profile'];left=np.array(Image.open(folder/'runs/desktop-public-v2'/(key+'.png')).convert('RGBA')).astype(float);right=np.array(Image.open(folder/'runs/wasm-public-v2'/(key+'.png')).convert('RGBA')).astype(float)
        mae=float(np.abs(left-right).mean());limit=.25 if a['profile'].startswith('graphic') else .02
        parity.append({'case':key,'rgba_mae':mae,'limit':limit,'passed':mae<=limit,'recommended_domain':a['recommended_domain']})
    diagnostic=bench.read(folder/'diagnostics/palette-diagnostic/diagnostic.json')
    original_art=[r for r in desktop['cases'] if r['profile']=='graphic-medium-9' and r.get('vector_truth_4x')]
    truth={engine:float(np.mean([r['vector_truth_4x'][engine]['rgb_mae_white'] for r in original_art])) for engine in ['reference','candidate']}
    summary={'schema':2,'images':len(corpus['images']),'profiles':corpus['enabled_profiles'],'independent_cases_per_engine':len(desktop['cases']),
             'verified_vm_references':desktop['summary']['verified_reference_cases'],'coverage_complete':True,'quality_equivalence_claimed':False,
             'desktop':desktop['summary'],'wasm':wasm['summary'],'desktop_wasm_parity':parity,
             'vector_truth_4x_graphic_mae':truth,'palette_diagnostic':diagnostic,
             'timing_policy':'Candidate engine timings are recorded, but no controlled VM per-image timing exists; no speed ranking.',
             'source_families':sorted({r['repo'] for r in corpus['images']})}
    out=folder/'reports/public-overview'
    if out.exists():raise ValueError('Overview exists; preserve the experiment')
    out.mkdir(parents=True);bench.write(out/'summary.json',summary)
    esc=html.escape;groups=desktop['summary']['by_profile_category'];rows=''
    for key,a in groups.items():
        profile,category=key.split('/');matched=(category=='photo')==profile.startswith('photo')
        if not matched:continue
        b=wasm['summary']['by_profile_category'][key]
        rows+=f'<tr><td>{esc(key)}</td><td>{a["cases"]}</td><td>{a["mean_rgb_mae_white"]:.3f}</td><td>{b["mean_rgb_mae_white"]:.3f}</td><td>{a["mean_region_boundary_f1"]:.4f}</td></tr>'
    failures=[r for r in parity if not r['passed']]
    before=np.mean([r['desktop']['independent_rgb_mae'] for r in diagnostic['rows']]);after=np.mean([r['desktop']['vm_palette_rgb_mae'] for r in diagnostic['rows']])
    source_cards=''.join('<figure><img src="../../'+esc(r['path'])+'"><figcaption>'+esc(r['id']+' · '+r['license'])+'</figcaption></figure>' for r in corpus['images'])
    text='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>DoctorTracer — внешний испытательный стенд v2</title>
<style>body{font:16px Segoe UI,system-ui;margin:28px;background:#f3f6fa;color:#172b43}h1{font-size:28px}.card{background:white;border:1px solid #cbd6e2;padding:20px;border-radius:10px;margin:18px 0}table{border-collapse:collapse;width:100%}td,th{padding:11px;text-align:left;border-bottom:1px solid #dbe2ea}th{font-size:13px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}figure{margin:0}img{width:100%;height:140px;object-fit:contain;background:repeating-conic-gradient(#eee 0 25%,white 0 50%) 0/12px 12px}figcaption{font-size:12px}a{color:#075baf}.links a{display:inline-block;padding:10px 18px;margin-right:12px;background:#e6f0fc;border-radius:5px}p{line-height:1.6}pre{white-space:pre-wrap}.warning{color:#9b4224}.note{font-size:13px;color:#52647a}</style>
<h1>DoctorTracer ↔ Vector Magic: новый внешний набор</h1>
<p>12 новых изображений · 4 профиля · 48 настоящих эталонов Vector Magic 1.15 · 96 независимых трассировок Windows/WASM.</p>
<p class="links"><a href="../desktop-public-v2/index.html">Windows: все 48 сравнений</a><a href="../wasm-public-v2/index.html">WASM: все 48 сравнений</a><a href="summary.json">Полные числа JSON</a><a href="../../ATTRIBUTION.md">Источники и лицензии</a></p>
<section class="card"><h2>Основные результаты на соответствующих типах входа</h2><p>MAE — различие с Vector Magic, шкала 0–255, меньше лучше. F1 границ — без сравнения RGB, допуск 1 пиксель, больше лучше.</p><table><tr><th>Профиль / тип</th><th>N</th><th>MAE Windows ↓</th><th>MAE WASM ↓</th><th>F1 Windows ↑</th></tr>'''+rows+'''</table><p class="warning">Полное покрытие не означает равенство качества. Фотографии с ограниченной палитрой всё ещё заметно отличаются от оригинала.</p></section>
<section class="card"><h2>Где находится расхождение</h2>'''+f'<p>На четырёх фотографиях средняя MAE ограниченной палитры: <b>{before:.2f}</b>. При передаче DoctorTracer RGB-палитры из экспорта VM: <b>{after:.2f}</b>. Это условный oracle-опыт, исключённый из независимых оценок: он показывает вклад выбора цветов, а не готовое улучшение алгоритма.</p>'+f'<p>Известный исходный SVG при ×4, восемь графических входов: MAE Vector Magic <b>{truth["reference"]:.3f}</b>, DoctorTracer Windows <b>{truth["candidate"]:.3f}</b>. Пример QR-кода — исключение: DoctorTracer совпал с исходным SVG точнее. Близкая F1 на исходном размере скрывает часть отличий.</p>'+'''<p>VM использовал на лисе/бабочке четыре RGB-цвета при лимите девять слотов, DoctorTracer — восемь. Заданный лимит не обязывает заполнять всю палитру смешанными краевыми цветами.</p></section>
<section class="card"><h2>Windows ↔ WASM: отдельная проверка</h2>'''+f'<p>Средняя RGBA MAE: {np.mean([r["rgba_mae"] for r in parity]):.6f}. Порог превышен в {len(failures)} из {len(parity)} случаев. Использованы прежние допуски стенда: 0.02 для фото-профилей, 0.25 для графики.</p><pre>'+esc(json.dumps(failures,ensure_ascii=False,indent=2))+'''</pre><p class="note">Случай не скрыт из отчёта: это отдельное расхождение версий, даже если профиль является стрессовым для QR-кода.</p></section>
<section class="card"><h2>Новый корпус</h2><div class="grid">'''+source_cards+'''</div><p class="note">Исходники взяты из зафиксированных коммитов, хеши и лицензии сохранены. Четыре семейства источников; набор невелик и после этой проверки уже не является невидимым holdout для будущей настройки. 20 случаев соответствуют типу входа, 28 — намеренные стрессовые комбинации. Измерения скорости DoctorTracer записаны в исходных run.json; сопоставимого тайминга VM нет, рейтинг скорости не строился.</p></section></html>'''
    (out/'index.html').write_text(text,encoding='utf8');print(out/'index.html')

if __name__=='__main__':main()
