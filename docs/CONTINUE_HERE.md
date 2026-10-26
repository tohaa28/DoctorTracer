# Продолжение разработки

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
