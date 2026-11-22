# Отрицательные результаты после 0.6

- В 0.9 проверены два дополнительных способа убрать видимые щели фото. Полная
  подложка улучшала alpha IoU (около .980 → .992 на UI9/medium), но увеличивала
  число путей 5280 → 9130 и не улучшала RGB на белом фоне (4.402 → 4.424).
  Аддитивное суммирование покрытия цветов повышало ошибку 4.402 → 5.170.
  В приложение эти варианты не включены. Требуется согласованная модель общих
  границ, а не маскировка дефекта наложением или новым способом композиции.

- Глобальная булева обработка тысяч фото-контуров оказывалась слишком медленной
  и иногда не завершалась успешно. Заменена пространственными участками.
- Успешный возврат Skia PathOps сам по себе не гарантировал отсутствие остаточных
  пересечений на сложном входе. Добавлены независимый целочисленный аудит каждого
  участка и пересчёт проблемного участка Clipper. Резервные участки линеаризуют
  кривые при масштабе 64×; это явно отражено в статистике/ограничениях.
- Складывать compound paths с неявным fill rule небезопасно. Для покрытия явно
  выбирается winding rule, проверяются также объекты одного цвета и отверстия.

- В переданном экспериментальном OpenCL-стенде пять RGB-формул использовали
  `dx²+dy²+dz`. На реальной GTX 1080 прошли 5/55 проверок. Эти ядра не внедрены
  в приложение. Исправленная отдельная копия прошла 55/55 и 300 граничных проверок.
  Production `accelerator.py` изначально использовал правильный квадрат dz.
- AA seed-ограничения на фотографической палитре ухудшали локальное сравнение.
  Фоторежим не переводится на AA-классификатор.
- Lab, YCrCb и взвешенный RGB вместо обычного RGB в ближайшей фиксированной
  палитре ухудшали сравнение контрольного входа. Не включены.
- Полная цветная подложка под фотографией уменьшала белые швы, но ухудшала
  ошибку на тёмном фоне (примерно 3.685 → 4.704). В фото не включена.
- Первый прототип пространственного GPU-ядра учитывал невидимые RGB-соседи на
  первом проходе: один из 100 тестов не совпал с CPU. Исправлено явной проверкой
  alpha соседей перед вычислением штрафа; все 100 runtime-тестов прошли.
- Настройка сильного сглаживания по одному числу путей не принимается: цветовая
  ошибка и число компонент не гарантируют сохранение тонких деталей/топологии.

Прежние отрицательные результаты построения кривых сохранены в `CURVES.md`.

## 2026-10-25 — photo detail experiments

- Ограничение слияния соседей цветовой дистанцией 48 оставляло больше мелких областей, но на первом thin-lines примере вызвало ClipperException из-за вырожденных контуров. Не внедрено; нужна отдельная защита топологии.
- Цветовой guard медианного фильтра 48 проверен только на шести development случаях; в production не включён. Базовый cleanup=0 согласован с Windows.
- Общий граф fixed-photo с прежними 8 проходами/.5 допуском чрезмерно смещал мелкие границы; выбран более консервативный режим 2 прохода/.25 для среднего качества. Остаточные метрики ухудшения не скрыты; см. QUALITY_013.md.


## 2026-11-21 · Кандидат для исправления сглаживания в связке Relief Forge → DoctorTracer. Опубликованный 0.21.1 (gh-pages 48dfa7b6ea268df1b45bc6ea22981eaba1ee9026, version.json sourceCommit 4f011fb2d92ff4ad8191f07bf7384aaec8add61b) использует Canvas drawImage с включённой по умолчанию интерполяцией: load() 2400 px, analyzeSource() 900 px, requestPalette() 500 px, batch import. Bitmap масштабируется CSS без image-rendering — даже корректный PNG визуально сглажен. Relief Forge alpha.90 уже устраняет вторичный resize при 2400 px, но не внутренний анализ, палитру и визуализацию. Метод: same-origin parent /relief-forge/ либо явная опция ?raster=crisp включает nearest-neighbour при всех входных drawImage (включая batch и подачу в Worker); CSS только для bitmap/segments; обычная автономная работа и векторный предпросмотр сохраняют прежнее поведение. Реальная прозрачность PNG не порогуется здесь. Существующий порог WASM 128/255 для сегментации не изменён; ограничение 2400 px сохранено. Фильтрация/геометрическое сглаживание в выбранных режимах трассировки — отдельные операции, не входной ресемплинг. Добавлен unit test политики. Не считать релизом до фактического Chromium-теста реального мастера и проверки Pages. Частный EPS не доступен; никакие пользовательские изображения не публикуются.


## 2026-11-22 · Exact grid must not force polygon
The old `exactGrid || orthogonal` predicate equated binary RGBA with vector polygon intent. This was incorrect for a Ghostscript rasterized ellipse, diagonal or cubic. Fix only the decision for natural staircase edges, not source image, transparency, anti-aliasing, palette, adjacency or binary WASM. Preserve manual polygon choice and long-axis rectilinear figures. Source test and browser validation pending.


## 2026-11-22 · Residual corner risk for combined angular/curved compositions
Verified on distinct rectangle and circle and a simple mixed scene, but the global shared graph can still round some nonorthogonal artwork corners in a complex shared edge. No original user EPS test was possible. If the general audit rejects pairing, the Rust tracer falls back to safe polygon geometry; do not claim perfect reconstruction. Algorithm details and rollback at START_HERE.md.


## Previous risk: ambiguous binary cells
A pixel-grid square is not proof of a true 90-degree corner. Do not indiscriminately smooth every vector node; preserve explicit polygons and straight-only borders. Also avoid independent tracing of adjacent colors (gaps/overlaps), alpha-threshold postprocessing, and an arbitrary resizing stage. Potrace candidate MUST be rejected on complex ownership and failed pixel-center or geometry checks; baseline is unchanged. CI pending.


## 2026-11-22 · Failed 0.21.5 candidate calibrations
Run 45009181173: candidate rejected with opaque pre-fallback output, initial 8% edge fidelity budget too strict. Run 45009549102: detailed source mask correct, 30th center mismatch exceeded 29 allowed. Run 45009846852: measured true 59 mismatches across 368 original boundary steps; mean proxy 0.1603. Adjustment introduced independent dual cap <=25% boundary steps and <=2% foreground pixels; actual ring/ellipse/rectangle audited on GH run 45010264233, CircleCI successful. No silent image resampling and no weakening topology. User's actual EPS untested.
