> Полная сводная история и продолжение: [PROJECT_HISTORY.md](PROJECT_HISTORY.md), [CONTINUE_HERE.md](CONTINUE_HERE.md). Этот файл сохраняет прежние записи.

Обновление качества 26.10.2026: Windows **0.13.0-preview** / WASM **0.15.0-wasm-preview**. [Изменения и ограничения](QUALITY_015.md), [числа](QUALITY_015_RESULTS.json). Ограниченная палитра фото: MAE 10.084→8.015; Chelsea ухудшается. Подбор смеси/общих границ и локальный refit; это не глобальная оптимизация и не равенство VM. Pages: https://tohaa28.github.io/DoctorTracer/?v=0.15.0 .

Испытания 26.10.2026: [внешний стенд v2](PUBLIC_BENCHMARK_V2.md), 12 новых входов / 48 эталонов VM / 96 результатов. Главная проблема — подбор ограниченной палитры; oracle-опыт 10.08→1.85 не является исправлением алгоритма. Один стрессовый тест переносимости WASM не прошёл. [Исследование алгоритма VM](VECTOR_MAGIC_ALGORITHM_RESEARCH.md). Версии приложений не менялись.

# Разработка после 0.6

## 2026-10-25 — 0.9 preview

- Исправлены внутренние границы участков: геометрия одного RGB объединяется.
- PDF содержит один составной объект на цвет; в CorelDRAW проверены 8 объектов
  после импорта контрольного PDF с восьмью цветами.
- Большие цветовые пути отрисовываются напрямую, без лимита SVG-парсера Qt.
- Добавлены понятные векторные иконки и GPU bilateral-предобработка.
- GPU и пространственный режим фото с палитрой включены по умолчанию.
- Полный перенос всех расчётов на GPU и идентичность оригиналу не достигнуты.
  Подробности: `COREL_IMPORT.md`.

## 2026-10-24 — 0.8 preview

- Добавлены SVG-группы RGB и обязательное геометрическое удаление закрытых частей.
- Добавлены пространственные участки и четыре отдельных процесса для крупных работ.
- Каждая область проходит независимый целочисленный аудит пересечений с допуском
  0.0001 рабочего пикселя²; резервные области могут содержать линейные сегменты.
- EPS адаптирован к группированному SVG; исходные размеры и отверстия сохраняются.
- GPU-сегментация сохранена; геометрический этап выполняется на CPU.
- Подробности и ограничения: `VECTOR_LAYOUT.md`.

## 2026-10-24 — 0.7 preview

- Исправлено пропадание цветов в Qt SVG при огромном compound path из Potrace CLI.
- Добавлена отключаемая пространственная сегментация фиксированной палитры фото,
  с CPU/OpenCL parity и однократной выгрузкой итоговых GPU-меток.
- Добавлено сохранение опции в настройках и блокирование устаревшего экспорта.
- Исправлено переключение фото в иллюстрацию в расширенном мастере.
- Успешны основные тесты, новые GPU/UI-тесты, реальные portable worker и GUI,
  четыре эталонных сравнения, 14 конфигураций синтетики, 36 layout-проверок.
- Алгоритм остаётся экспериментальным. Полного соответствия Vector Magic нет.
  Статус и ограничения: `SPATIAL_PALETTE.md`; прежняя 0.6 доступна для отката.

## 2026-10-25 — испытательный стенд качества

Добавлены quality/bench.py, генератор 40 синтетических входов, регистрация реальных
эталонов, Desktop/WASM runner и автономный HTML-отчёт со шторкой и регрессиями.
Локальный корпус — 42 входа, 84 экспорта Vector Magic для двух профилей.
Стенд выявил пять выходящих за допуск расхождений WASM относительно Desktop.
Алгоритм не изменён; полный результат и ограничения: [quality/BASELINE.md](../quality/BASELINE.md).

## 2026-10-25 — Windows 0.11 / WASM 0.13

Fixed-photo переведён на общий граф без просветов; детали сохраняются более
консервативным сглаживанием. WASM cleanup=0 согласован с базовым Windows-мастером.
Исправлена неточность параметров стенда, пересняты сопоставимые baseline.
Средняя ошибка fixed-палитры относительно оригинала снижена примерно на 16%,
но отдельные boundary/IoU предупреждения остаются. [Полный отчёт](QUALITY_013.md).


## 26.10.2026 — исправление палитр

Windows 0.11.1 / WASM 0.13.1: прозрачный слот, выравнивание, соответствие выбранной и используемой палитр, защита от устаревших ответов. Проверки и ограничение старых сравнений: [PALETTE_FIX_0131.md](PALETTE_FIX_0131.md).


## 26.10.2026 — GPU-контуры

Windows 0.12 / WASM 0.14: OpenCL FP64 shared smoothing, RDP, Bezier arithmetic; точное целочисленное WebGPU-сглаживание. 168 CPU/GPU SVG-проверок, 24 WebGPU + 2 worker, 4 полноразмерных случая в EXE. Измеренное ускорение Windows 1.06–1.35× без изменения SVG. Отрицательные результаты WASM учитываются при выборе пути. Подробности: [GPU_CONTOURS_014.md](GPU_CONTOURS_014.md).


## 26.10.2026 — Windows 0.14 / WASM 0.16

Совместное уточнение пространственной сегментации и автоматической палитры; единый Rust full-raster refit. Новый набор выбран в 2388ad7; параметры заморожены в 88d2263; затем исправлялись скорость и устойчивость геометрии. См. [QUALITY_016.md](QUALITY_016.md) и [QUALITY_016_RESULTS.json](QUALITY_016_RESULTS.json). Полная идентичность VM не заявляется.


## 2026-11-21 · Кандидат для исправления сглаживания в связке Relief Forge → DoctorTracer. Опубликованный 0.21.1 (gh-pages 48dfa7b6ea268df1b45bc6ea22981eaba1ee9026, version.json sourceCommit 4f011fb2d92ff4ad8191f07bf7384aaec8add61b) использует Canvas drawImage с включённой по умолчанию интерполяцией: load() 2400 px, analyzeSource() 900 px, requestPalette() 500 px, batch import. Bitmap масштабируется CSS без image-rendering — даже корректный PNG визуально сглажен. Relief Forge alpha.90 уже устраняет вторичный resize при 2400 px, но не внутренний анализ, палитру и визуализацию. Метод: same-origin parent /relief-forge/ либо явная опция ?raster=crisp включает nearest-neighbour при всех входных drawImage (включая batch и подачу в Worker); CSS только для bitmap/segments; обычная автономная работа и векторный предпросмотр сохраняют прежнее поведение. Реальная прозрачность PNG не порогуется здесь. Существующий порог WASM 128/255 для сегментации не изменён; ограничение 2400 px сохранено. Фильтрация/геометрическое сглаживание в выбранных режимах трассировки — отдельные операции, не входной ресемплинг. Добавлен unit test политики. Не считать релизом до фактического Chromium-теста реального мастера и проверки Pages. Частный EPS не доступен; никакие пользовательские изображения не публикуются.


## 2026-11-21 · DoctorTracer 0.21.2-wasm-preview. Исправление входных резких краёв из Relief Forge, PR #2 merged 1f61ffd11968be355daa787b77ccd3f7820dd281. Проверенный функциональный коммит 4e567ee9c8010c702f44733aaa3bc051e6557485. Сквозной Chromium реального мастера, реальный Worker/WASM и тесты политики: Relief Forge PR #124 ffa45188ce823c41a4ba2b9d35a56f6962796392, CircleCI https://app.circleci.com/workflow/c7d566fe-ad7f-4393-b173-17951a177c03/job/e07aa89d-fa50-46b2-aafe-721e66354ab9 success, GitHub Actions https://github.com/tohaa28/relief-forge/actions/runs/44941378586 success. Синтетический PNG 3001×181, импорт 2400×145, анализ 900×54, палитра 500×30 и trace 2400×145: во всех четырёх стадиях ровно четыре RGBA-класса [0,0,0,0; 0,0,255,255; 0,255,0,153; 255,0,0,255]; CSS pixelated в bitmap, вектор без нового CSS, возврат Bitmap корректный. Standalone сохраняет auto и >32 классов при уменьшении, как раньше. WASM бинарники и декодеры не меняются; не пересобирать ядро без нужды. Релизный номер и cache key 0.21.2. Лимит 2400 и порог WASM 128/255 не отменены; тест не гарантирует отсутствия дефектов произвольной EPS геометрии. Предыдущий опубликованный снимок gh-pages 48dfa7b6ea268df1b45bc6ea22981eaba1ee9026. Публикацию подтвердить по live version.json.


## 2026-11-21 · Отказ от любых скрытых уменьшений растра (кандидат). База 0.21.2 d5fd8a32034523fe2991bfae2820dba7e44d698d. Удалены ограничения масштаба load 2400, analyze 900, palette 500, batch 2400, начальный PDF render больше не понижается до 2400 (scale 3 или явная ошибка). Native bitmap и оригинальный PNG/JPEG/WebP/BMP Blob сохраняются; PNG pHYs не теряется в предпросмотре. Все drawInputRaster только 1:1, Worker проверяет размер RGBA. Устаревший API WASM valid(w,h) = до 4096 по стороне и 8 млн пикселей; не изменён без отдельного нагрузочного теста и сборки Rust. Для больших входов явная ошибка, без ресемплинга и без запуска трассировки старого файла. Существующие выбранные операции трассировки (фильтрация/сегментация) не отменяются. Контракт native-raster-v1 для предотвращения передачи в устаревший мастер. Тесты добавлены, CI пока не подтверждён, публикации нет. Расширение WASM для A4/600–1200 dpi требует отдельного доказательства памяти/глобальной геометрии; нельзя подменять его скрытым уменьшением или плитками со швами.


## 2026-11-21 · DoctorTracer 0.21.3-wasm-preview. Исходный растр без уменьшения. PR #3 merged 53951f8fe5bba254ff65244db23164897a9f777f; проверенный функциональный коммит bdb8ad49464e242b213aea0f618f24bc6aa90bbc. Relief Forge PR #125 a7f289b89815db0e8365e15d282f6de029fcbb70: CircleCI success https://app.circleci.com/workflow/ff01b9f9-9774-45a6-9962-30c2803b2b5d/job/a6e3f6e8-9a30-48b5-9426-182ed0ddac34; GitHub Actions https://github.com/tohaa28/relief-forge/actions/runs/44943840009 success; 431 JS и 17 Rust PASS. Реальный мастер: PNG побайтно совпал, 3001×181 на import/analyze/palette/trace, FNV RGBA 1069192609 во всех стадиях, standalone также без изменения. Отдельно растрирование 3165×472, 1199.9976 DPI (pHYs), alpha 0/153. Отказ 4097×1 проверен; текущие безопасные пределы WASM 4096 по стороне / 8 млн пикселей сохраняются. WASM бинарники неизменны. Контракт native-raster-v1 предотвращает передачу в старый мастер. Публикация в gh-pages после синхронизации версии, предыдущая контрольная точка f06691d2fed3fcfb8192c7910519e6fbe54fce5f. Расширение лимитов и реальный частный EPS не подтверждены.


## 2026-11-22 · Candidate 0.21.4 adaptive crisp-grid curves
Problem: after Ghostscript rasterization with AA off (Relief Forge alpha.92), fully opaque or fully transparent exact-palette pixels set `exactGrid=true` in `web/desktop-curves.mjs`, which was treated as `polygon=true`; this forced all rounded and diagonal objects to remain stair-step polygons. Change: decouple exact pixel colors from output geometry. Keep polygons for orthogonal long-run boundaries, explicit straight-segment mode or `smooth=false`. Otherwise use the existing Rust/WASM single-owner planar boundary graph with conservative fixed smoothing and cubic Bézier fitting, native paired-border contract, small-loop pins and geometry audit. No raster modification, no new binary ABI, no separate per-color contours, no postprocessing. Added real WASM regression of exact rectangle, binary circle, mixed artwork, explicit polygon/smooth=false and contract. Sources: https://potrace.sourceforge.net/potracelib.pdf (corner/curve analysis), https://github.com/tohaa28/relief-forge/pull/126 (Ghostscript AA-free). This stage is source-written only. A browser/CI gate and publication remain unverified; user-supplied actual EPS not reproduced. Known tradeoff: in a single mixed artwork shared-graph smoothing may adjust some corners; must not claim zero distortions without measured test. Rollback 0.21.3 at 42cbbdf6dd95e87f5b8943d8c971bccc0c170a95.


## 2026-11-22 · DoctorTracer WASM 0.21.4 — adaptive sharp-raster curve tracing. PR #4 merged f84aa0ace0056ba01c032c9329cce5066702b4f7; tested functional commit 6d67342b2305a4a18a0ee64c96f3b4cdf5aa4cd3. Real Rust/WASM, Browser and handoff integration tested on isolated Relief Forge CI PR #127 (never merge it): GitHub Actions https://github.com/tohaa28/relief-forge/actions/runs/45005717026 passed, CircleCI https://app.circleci.com/workflow/c3dccfa4-e260-42cc-8c5d-cb23e7a996d7/job/bc7e9680-4d52-4429-bb7f-5601cc1ffa03 passed. DoctorTracer tests/crisp_grid_curves.mjs PASS: exact pixel rectangle retains L geometry and right angles, 1-bit circle yields C cubic Bézier, explicit polygon/smooth=false yield L, mixed shapes yield C, data-boundary-contract=paired and native audit pass. Legacy real handoff test preserves byte-identical source PNG at 3001×181 in analyze/palette/trace, unchanged RGBA hash 1069192609. Relief Forge regression suite 434 JS/17 Rust PASS, exact Ghostscript EPS/PDF sharp raster stage unchanged. Root cause was exactGrid forcing polygon in web/desktop-curves.mjs; now its orthogonal/explicit-polygon logic permits paired Rust smooth curves for natural stair-steps. Uses unchanged 0.21.3 Rust WASM/audit binaries, no raster interpolation, rescale, alpha quantization or bitmap postprocessing. Existing 4096×4096/8M pixel cap remains; sharp corners in arbitrary mixed scene and original user EPS remain unverified. Alpha.92 Relief Forge unchanged. Source metadata bump and website deployment are separate steps; publication not verified until Pages deploy passes. Rollback gh-pages 6d750419db6fa75afc52b35c9445b8c93dc8aa29 and original source 42cbbdf6dd95e87f5b8943d8c971bccc0c170a95; test harness branch PR #127 remains draft.


## 2026-11-22 · PUBLISHED DoctorTracer WASM 0.21.4 (adaptive crisp-grid Bézier). Source functional PR #4 merged f84aa0ace0056ba01c032c9329cce5066702b4f7, metadata release commit fe580f2b318aaa814e3075c0d31b02c4414bf37e; gh-pages commit 5050912a54940f1ce1c5154e7a0339c370606751. GitHub Pages Actions https://github.com/tohaa28/DoctorTracer/actions/runs/45006236691: build SUCCESS, report-build-status SUCCESS, deploy SUCCESS. Site https://tohaa28.github.io/DoctorTracer/?v=0.21.4 ; version.json says 0.21.4-wasm-preview, sourceCommit fe580f2b318aaa814e3075c0d31b02c4414bf37e, unchanged native rust tracer and audit WASM hashes. Functionally tested DoctorTracer source 6d67342b2305a4a18a0ee64c96f3b4cdf5aa4cd3 via isolated Relief Forge PR #127, CircleCI https://app.circleci.com/workflow/c3dccfa4-e260-42cc-8c5d-cb23e7a996d7/job/bc7e9680-4d52-4429-bb7f-5601cc1ffa03 SUCCESS and GitHub Actions https://github.com/tohaa28/relief-forge/actions/runs/45005717026 SUCCESS: binary circle -> cubic C, polygon rectangle and explicit straight -> L, mixed shapes -> cubic, paired boundary contract and native audit PASS, byte-identical PNG 3001×181 in analyze/palette/trace, 434 JS + 17 Rust tests in RF PASS. Need manual test on user's actual non-AA Ghostscript EPS PNG; no original uploaded in this turn. Known limits 4096 px/8M pixels; arbitrary complex acute corners may need further calibration. No image raster postprocess or interpolation. Published state derived from GitHub Actions deploy success, independent external web fetch failed so live browser smoke is not claimed. RF test-only PR #127 must NOT merge. Rollback gh-pages 6d750419db6fa75afc52b35c9445b8c93dc8aa29; source 42cbbdf6dd95e87f5b8943d8c971bccc0c170a95.


## 2026-11-22: Candidate 0.21.5, pixel-aware quantization fit. Root cause: even after 0.21.4, local Rust lattice smoothing cannot reconstruct a globally averaged continuous curve from a no-antialiasing circle/ellipse. New `web/pixel-grid-trace.mjs` routes exactly binary two-face hard-edged inputs with a uniform border to existing native Potrace 1.16 WASM. The 1px grid constrains an unknown vector crossing between disagreeing cell centers to ±0.5 pixel; Potrace globally optimizes its polygon and fits subpixel cubic Béziers. 0.18px optimisation tolerance and alphamax 1.0; physical tolerance 0.18 * 25.4/dpi mm. Parse/serialize all native M/L/C/Z paths; reverse the exact same Bézier handles for the other color's face. Accept candidate only after pixel-center winding/raster-fidelity errors <=8% of measured lattice boundary edges and independent native vector geometry audit. Else fallback to 0.21.4 Rust paired grid. Do not alter, interpolate, scale, threshold or overwrite input PNG. Explicit polygon and true orthogonal boundaries retained; multi-color or edge-touching scenes remain on proven shared Rust route. Added real WASM test `tests/pixel_grid_trace.mjs`: circle, ellipse, concentric hole/ring, rectangle, mixed image, determinism and exact center-cell fidelity. CI NOT YET RUN. Public research reference Selinger (2003): https://potrace.sourceforge.net/potrace.pdf . Baseline source 0aaa1171d027a50be9b39c227154781d2862b2c5, candidate 2506f02384d348dda0e356badf34cba5ba3f7bd6; rollback existing gh-pages 5050912a54940f1ce1c5154e7a0339c370606751. Original user's EPS/PNG unavailable, no real-art fidelity claim.
