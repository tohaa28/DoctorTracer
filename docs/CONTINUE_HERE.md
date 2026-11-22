## 2026-11-22 · PUBLISHED DoctorTracer WASM 0.21.4 (adaptive crisp-grid Bézier). Source functional PR #4 merged f84aa0ace0056ba01c032c9329cce5066702b4f7, metadata release commit fe580f2b318aaa814e3075c0d31b02c4414bf37e; gh-pages commit 5050912a54940f1ce1c5154e7a0339c370606751. GitHub Pages Actions https://github.com/tohaa28/DoctorTracer/actions/runs/45006236691: build SUCCESS, report-build-status SUCCESS, deploy SUCCESS. Site https://tohaa28.github.io/DoctorTracer/?v=0.21.4 ; version.json says 0.21.4-wasm-preview, sourceCommit fe580f2b318aaa814e3075c0d31b02c4414bf37e, unchanged native rust tracer and audit WASM hashes. Functionally tested DoctorTracer source 6d67342b2305a4a18a0ee64c96f3b4cdf5aa4cd3 via isolated Relief Forge PR #127, CircleCI https://app.circleci.com/workflow/c3dccfa4-e260-42cc-8c5d-cb23e7a996d7/job/bc7e9680-4d52-4429-bb7f-5601cc1ffa03 SUCCESS and GitHub Actions https://github.com/tohaa28/relief-forge/actions/runs/45005717026 SUCCESS: binary circle -> cubic C, polygon rectangle and explicit straight -> L, mixed shapes -> cubic, paired boundary contract and native audit PASS, byte-identical PNG 3001×181 in analyze/palette/trace, 434 JS + 17 Rust tests in RF PASS. Need manual test on user's actual non-AA Ghostscript EPS PNG; no original uploaded in this turn. Known limits 4096 px/8M pixels; arbitrary complex acute corners may need further calibration. No image raster postprocess or interpolation. Published state derived from GitHub Actions deploy success, independent external web fetch failed so live browser smoke is not claimed. RF test-only PR #127 must NOT merge. Rollback gh-pages 6d750419db6fa75afc52b35c9445b8c93dc8aa29; source 42cbbdf6dd95e87f5b8943d8c971bccc0c170a95.

## 2026-11-22 · DoctorTracer WASM 0.21.4 — adaptive sharp-raster curve tracing. PR #4 merged f84aa0ace0056ba01c032c9329cce5066702b4f7; tested functional commit 6d67342b2305a4a18a0ee64c96f3b4cdf5aa4cd3. Real Rust/WASM, Browser and handoff integration tested on isolated Relief Forge CI PR #127 (never merge it): GitHub Actions https://github.com/tohaa28/relief-forge/actions/runs/45005717026 passed, CircleCI https://app.circleci.com/workflow/c3dccfa4-e260-42cc-8c5d-cb23e7a996d7/job/bc7e9680-4d52-4429-bb7f-5601cc1ffa03 passed. DoctorTracer tests/crisp_grid_curves.mjs PASS: exact pixel rectangle retains L geometry and right angles, 1-bit circle yields C cubic Bézier, explicit polygon/smooth=false yield L, mixed shapes yield C, data-boundary-contract=paired and native audit pass. Legacy real handoff test preserves byte-identical source PNG at 3001×181 in analyze/palette/trace, unchanged RGBA hash 1069192609. Relief Forge regression suite 434 JS/17 Rust PASS, exact Ghostscript EPS/PDF sharp raster stage unchanged. Root cause was exactGrid forcing polygon in web/desktop-curves.mjs; now its orthogonal/explicit-polygon logic permits paired Rust smooth curves for natural stair-steps. Uses unchanged 0.21.3 Rust WASM/audit binaries, no raster interpolation, rescale, alpha quantization or bitmap postprocessing. Existing 4096×4096/8M pixel cap remains; sharp corners in arbitrary mixed scene and original user EPS remain unverified. Alpha.92 Relief Forge unchanged. Source metadata bump and website deployment are separate steps; publication not verified until Pages deploy passes. Rollback gh-pages 6d750419db6fa75afc52b35c9445b8c93dc8aa29 and original source 42cbbdf6dd95e87f5b8943d8c971bccc0c170a95; test harness branch PR #127 remains draft.

## 2026-11-22 · 0.21.4 curve candidate (not yet published)
Base 42cbbdf6dd95e87f5b8943d8c971bccc0c170a95; branch feature/adaptive-crisp-grid-curves. Raster byte data unchanged; remove exactGrid from implicit polygon forcing; maintain manual polygon and orthogonal. Real WASM test tests/crisp_grid_curves.mjs must pass; then pinned live browser test in relief-forge CI, update version/cache, docs, gh-pages. Do not publish before checking CI. No Rust binary rebuilt.

## 2026-11-21 · DoctorTracer 0.21.3-wasm-preview. Исходный растр без уменьшения. PR #3 merged 53951f8fe5bba254ff65244db23164897a9f777f; проверенный функциональный коммит bdb8ad49464e242b213aea0f618f24bc6aa90bbc. Relief Forge PR #125 a7f289b89815db0e8365e15d282f6de029fcbb70: CircleCI success https://app.circleci.com/workflow/ff01b9f9-9774-45a6-9962-30c2803b2b5d/job/a6e3f6e8-9a30-48b5-9426-182ed0ddac34; GitHub Actions https://github.com/tohaa28/relief-forge/actions/runs/44943840009 success; 431 JS и 17 Rust PASS. Реальный мастер: PNG побайтно совпал, 3001×181 на import/analyze/palette/trace, FNV RGBA 1069192609 во всех стадиях, standalone также без изменения. Отдельно растрирование 3165×472, 1199.9976 DPI (pHYs), alpha 0/153. Отказ 4097×1 проверен; текущие безопасные пределы WASM 4096 по стороне / 8 млн пикселей сохраняются. WASM бинарники неизменны. Контракт native-raster-v1 предотвращает передачу в старый мастер. Публикация в gh-pages после синхронизации версии, предыдущая контрольная точка f06691d2fed3fcfb8192c7910519e6fbe54fce5f. Расширение лимитов и реальный частный EPS не подтверждены.

## 2026-11-21 · Отказ от любых скрытых уменьшений растра (кандидат). База 0.21.2 d5fd8a32034523fe2991bfae2820dba7e44d698d. Удалены ограничения масштаба load 2400, analyze 900, palette 500, batch 2400, начальный PDF render больше не понижается до 2400 (scale 3 или явная ошибка). Native bitmap и оригинальный PNG/JPEG/WebP/BMP Blob сохраняются; PNG pHYs не теряется в предпросмотре. Все drawInputRaster только 1:1, Worker проверяет размер RGBA. Устаревший API WASM valid(w,h) = до 4096 по стороне и 8 млн пикселей; не изменён без отдельного нагрузочного теста и сборки Rust. Для больших входов явная ошибка, без ресемплинга и без запуска трассировки старого файла. Существующие выбранные операции трассировки (фильтрация/сегментация) не отменяются. Контракт native-raster-v1 для предотвращения передачи в устаревший мастер. Тесты добавлены, CI пока не подтверждён, публикации нет. Расширение WASM для A4/600–1200 dpi требует отдельного доказательства памяти/глобальной геометрии; нельзя подменять его скрытым уменьшением или плитками со швами.

## 2026-11-21 · DoctorTracer 0.21.2-wasm-preview. Исправление входных резких краёв из Relief Forge, PR #2 merged 1f61ffd11968be355daa787b77ccd3f7820dd281. Проверенный функциональный коммит 4e567ee9c8010c702f44733aaa3bc051e6557485. Сквозной Chromium реального мастера, реальный Worker/WASM и тесты политики: Relief Forge PR #124 ffa45188ce823c41a4ba2b9d35a56f6962796392, CircleCI https://app.circleci.com/workflow/c7d566fe-ad7f-4393-b173-17951a177c03/job/e07aa89d-fa50-46b2-aafe-721e66354ab9 success, GitHub Actions https://github.com/tohaa28/relief-forge/actions/runs/44941378586 success. Синтетический PNG 3001×181, импорт 2400×145, анализ 900×54, палитра 500×30 и trace 2400×145: во всех четырёх стадиях ровно четыре RGBA-класса [0,0,0,0; 0,0,255,255; 0,255,0,153; 255,0,0,255]; CSS pixelated в bitmap, вектор без нового CSS, возврат Bitmap корректный. Standalone сохраняет auto и >32 классов при уменьшении, как раньше. WASM бинарники и декодеры не меняются; не пересобирать ядро без нужды. Релизный номер и cache key 0.21.2. Лимит 2400 и порог WASM 128/255 не отменены; тест не гарантирует отсутствия дефектов произвольной EPS геометрии. Предыдущий опубликованный снимок gh-pages 48dfa7b6ea268df1b45bc6ea22981eaba1ee9026. Публикацию подтвердить по live version.json.

## 2026-11-21 · Кандидат для исправления сглаживания в связке Relief Forge → DoctorTracer. Опубликованный 0.21.1 (gh-pages 48dfa7b6ea268df1b45bc6ea22981eaba1ee9026, version.json sourceCommit 4f011fb2d92ff4ad8191f07bf7384aaec8add61b) использует Canvas drawImage с включённой по умолчанию интерполяцией: load() 2400 px, analyzeSource() 900 px, requestPalette() 500 px, batch import. Bitmap масштабируется CSS без image-rendering — даже корректный PNG визуально сглажен. Relief Forge alpha.90 уже устраняет вторичный resize при 2400 px, но не внутренний анализ, палитру и визуализацию. Метод: same-origin parent /relief-forge/ либо явная опция ?raster=crisp включает nearest-neighbour при всех входных drawImage (включая batch и подачу в Worker); CSS только для bitmap/segments; обычная автономная работа и векторный предпросмотр сохраняют прежнее поведение. Реальная прозрачность PNG не порогуется здесь. Существующий порог WASM 128/255 для сегментации не изменён; ограничение 2400 px сохранено. Фильтрация/геометрическое сглаживание в выбранных режимах трассировки — отдельные операции, не входной ресемплинг. Добавлен unit test политики. Не считать релизом до фактического Chromium-теста реального мастера и проверки Pages. Частный EPS не доступен; никакие пользовательские изображения не публикуются.

# Продолжение разработки

Обновление 29.10.2026: Windows **0.18.0-preview** / WASM **0.20.0-wasm-preview** — «Выравнивание контуров»: общие прямые и глобальная подгонка плавных дуг готового SVG. [Описание и проверки](REGULARIZE_020.md). Pages: https://tohaa28.github.io/DoctorTracer/?v=0.20.0 .

Обновление 29.10.2026: Windows **0.17.0-preview** / WASM **0.19.0-wasm-preview** — восстановление тонких овальных рамок и острых звёзд в малых двухцветных логотипах на высоком качестве. [Описание, сравнение NF и ограничения](LOGO_HIGH_019.md). Pages: https://tohaa28.github.io/DoctorTracer/?v=0.19.0 .

Обновление 28.10.2026: Windows **0.16.0-preview** / WASM **0.18.0-wasm-preview** — модуль «Очистка и упрощение»: удаление изолированных островков и сокращение узлов общих кривых, предпросмотр, отмена. [Описание и проверки](POST_CLEAN_018.md). Pages: https://tohaa28.github.io/DoctorTracer/?v=0.18.0 .

Обновление 28.10.2026: Windows **0.15.0-preview** / WASM **0.17.0-wasm-preview** — дополнительное сглаживание готовых векторов, предпросмотр, сила, защита углов, применение/отмена. [Описание и проверки](POST_SMOOTH_017.md). Pages: https://tohaa28.github.io/DoctorTracer/?v=0.17.0 .

Обновление качества 26.10.2026: Windows **0.13.0-preview** / WASM **0.15.0-wasm-preview**. [Изменения и ограничения](QUALITY_015.md), [числа](QUALITY_015_RESULTS.json). Ограниченная палитра фото: MAE 10.084→8.015; Chelsea ухудшается. Подбор смеси/общих границ и локальный refit; это не глобальная оптимизация и не равенство VM. Pages: https://tohaa28.github.io/DoctorTracer/?v=0.15.0 .

Испытания 26.10.2026: [внешний стенд v2](PUBLIC_BENCHMARK_V2.md), 12 новых входов / 48 эталонов VM / 96 результатов. Главная проблема — подбор ограниченной палитры; oracle-опыт 10.08→1.85 не является исправлением алгоритма. Один стрессовый тест переносимости WASM не прошёл. [Исследование алгоритма VM](VECTOR_MAGIC_ALGORITHM_RESEARCH.md). Версии приложений не менялись.

Текущее обновление: Windows 0.12.0 / WASM 0.14.0 — GPU-контуры. Прочесть [GPU_CONTOURS_014.md](GPU_CONTOURS_014.md) и [результаты](GPU_CONTOURS_014_RESULTS.json). OpenCL FP64 ускоряет сглаживание, RDP и Безье; WebGPU exact integer включён для крупных свободных фото. Аудит остаётся независимым CPU.

Обновление 26.10.2026: палитры исправлены в Windows **0.11.1-preview** и WASM **0.13.1-wasm-preview**. [Описание и проверки](PALETTE_FIX_0131.md). Прозрачность занимает слот в интерфейсе, но исключена из RGB-палитры ядра. Pages: https://tohaa28.github.io/DoctorTracer/?v=0.13.1 . Ниже сохранён предыдущий снимок контекста.

Состояние на 25.10.2026. Сначала прочесть ../START_HERE.md и PROJECT_HISTORY.md.

## Что является текущим

- Репозиторий https://github.com/tohaa28/DoctorTracer, ветка spatial-photo-preview.
- Код приложения на момент снимка: eccf5c9. Документационные коммиты идут после него.
- Windows v0.10.3-preview, WASM v0.12.1-wasm-preview.
- Pages: https://tohaa28.github.io/DoctorTracer/?v=0.12.1 . Публикация из gh-pages,
  источник /, штатная legacy Pages build. build/site — игнорируемый отдельный checkout.
- PDF — формат векторного экспорта по умолчанию. Не возвращать SVG первым при
  перестройке страницы. PNG предназначен для отдельного растрового экспорта.
- Пользователь разрешил публикацию проекта в GitHub. Исходные изображения,
  их SVG/PDF/CDR, stage dumps и снимки с личными данными туда не добавлять.

## Карта кода

Windows: desktop/app.py → refined.py / wizard.py; engine.py;
accelerator.py (OpenCL); photo_regions.py и shared_regions.py;
boundary_smoothing.py; vector_partition.py, vector_render.py, color_objects.py
(PDF-группы и объекты).
Rust: rust/src/desktop_filters.rs, desktop_palette.rs, desktop_regions.rs,
desktop_shared.rs; lib.rs — raw ABI и стадии для тестов.
Web: app.js, worker.js, gpu.js, rust-tracer.mjs, desktop-curves.mjs;
geometry.mjs / paths.mjs, exports.mjs, preview.mjs; vendor/ — бинарные адаптеры.
Core: Potrace 1.16, wasm_mask.c, wasm_audit.cpp, Clipper C++.

## Проверки и сборка

```powershell
python tests/desktop_smoke.py
python tests/photo_regions.py
python tests/pdf_color_groups.py
node tests/rust_wasm.mjs
python scripts/verify_wasm.py --image <локальный-вход-1> --image <локальный-вход-2>
```

Не запускать полный набор после чисто документального изменения. Для алгоритмов
нужны quality gates; для UI проверять реальный мастер, прокрутку и экспорт.
Браузер: tests/browser.html (сервер из корня репозитория) или опубликованный
https://tohaa28.github.io/DoctorTracer/diagnostics.html . При gpuCases=0 GPU
не был проверен. Результаты и исходные эталоны хранятся в build/.

```powershell
python scripts/build_mask_wasm.py
python scripts/build_audit_wasm.py
python scripts/build_wasm.py
python -m PyInstaller --noconfirm desktop/DoctorTracer.spec --distpath rebuilt --workpath build/desktop-build
```

Rust: wasm32-unknown-unknown; рабочий локальный toolchain
1.99.1-x86_64-pc-windows-gnu. Emscripten 4.0.23 для C/C++ адаптеров.
Локальный build cache расположен на D:/DoctorTracer-build-cache:
rust/cargo/bin/cargo.exe, rust/rustup, emsdk/upstream/emscripten.
Перед cargo задать CARGO_HOME и RUSTUP_HOME, затем --toolchain и --cargo в
build_wasm.py. MSVC host без link.exe раньше не собирался; использовать GNU.
Windows зависимости зафиксированы в desktop/requirements.txt.

При публикации обновить cache key в scripts/build_wasm.py, пересобрать build/site,
записать version.json с SHA исходников и WASM, проверить URL/хеш после Pages build.
Архив runtime должен исключать вложенный .git. Соответствующий source ZIP и
лицензии включать в релиз. Не менять старые релизы ради нового исправления.
OAuth не имеет workflow scope: не добавлять .github/workflows через этот токен;
пример workflow остаётся в docs/pages-workflow.example.yml.

## Следующая работа

После фиксации истории пользователь поручил пункт 1 плана: испытательный стенд.
Он добавлен в quality/: 42 локальных входа, 84 подтверждённых эталона Vector Magic
для двух профилей; Desktop/WASM baseline и отчёты в build/quality. См.
../quality/README.md и ../quality/BASELINE.md. Пропуски остальных профилей явные.
Новая оптимизация алгоритма в эту задачу не входит.
При следующем улучшении качества исходить из уже работающего desktop pipeline:

1. Сохранить baseline и подготовить независимый корпус: фото/логотип/акварель,
   тонкие перемычки, отверстия, прозрачность, одинаковые фиксированные RGB.
2. Получить эталоны Vector Magic при строго записанных настройках; сравнивать
   не только рендер, но и компоненты, отверстия, общие границы и число узлов.
3. Проверить текущий PDF ручным импортом в отдельный документ CorelDRAW:
   основная группа → RGB-подгруппы → отдельные кривые; не трогать чужие документы.
4. Лишь после качества профилировать cold/warm и transfers. GPU-ускорение графов
   добавлять по одному этапу с CPU-паритетом, не обещать «всё на GPU» заранее.
5. Любое улучшение включать при прохождении gates и фиксировать отрицательные
   результаты. Проверки 0.12 не заменяют прямое сравнение с Vector Magic.

Исходный исследовательский handoff остаётся в Downloads; не путать его состояние
на 24.10 с текущим кодом. Полного текста чата «Справка Vector Magic» в репозитории нет.

## После стенда: качество 0.13

Общий fixed-photo граф и cleanup=0 внедрены в обе версии. Перевод профилей стенда
исправлен, старые baseline пересняты до изменения кода. Источники, реальные цифры
и оставшиеся незелёные quality gates перечислены в QUALITY_013.md; не объявлять
все метрики улучшенными. GPU/CPU и Desktop/WASM согласованы на новом корпусе.


## 26.10.2026 — Windows 0.14 / WASM 0.16

Совместное уточнение пространственной сегментации и автоматической палитры; единый Rust full-raster refit. Новый набор выбран в 2388ad7; параметры заморожены в 88d2263; затем исправлялись скорость и устойчивость геометрии. См. [QUALITY_016.md](QUALITY_016.md) и [QUALITY_016_RESULTS.json](QUALITY_016_RESULTS.json). Полная идентичность VM не заявляется.


## 28.10.2026 — WASM 0.16.1

Удалены границы вычислительных квадратов из экспорта через окончательный nonzero union по цветам. См. [TILE_SEAMS_0161.md](TILE_SEAMS_0161.md). Windows уже объединяет участки, это подтверждено отдельным тестом.


## 28.10.2026 — исправление жирных контуров

Windows 0.14.1 / WASM 0.16.2: ограничение локальной поддержки цветов применяется только к подтверждённым смесям. Сохранение оттенков, настоящего antialias, CPU/OpenCL/Rust parity проверены. См. [AA_SUPPORT_0162.md](AA_SUPPORT_0162.md).


## 28.10.2026 — общие границы

Windows 0.14.2 / WASM 0.16.3: единый планарный граф вместо независимых цветовых масок, точный контракт двух противоположных владельцев каждого ребра, проверка внешней прозрачной грани. См. [SHARED_BOUNDARIES_0163.md](SHARED_BOUNDARIES_0163.md).
