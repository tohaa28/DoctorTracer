## 2026-11-21 · DoctorTracer 0.21.3-wasm-preview. Исходный растр без уменьшения. PR #3 merged 53951f8fe5bba254ff65244db23164897a9f777f; проверенный функциональный коммит bdb8ad49464e242b213aea0f618f24bc6aa90bbc. Relief Forge PR #125 a7f289b89815db0e8365e15d282f6de029fcbb70: CircleCI success https://app.circleci.com/workflow/ff01b9f9-9774-45a6-9962-30c2803b2b5d/job/a6e3f6e8-9a30-48b5-9426-182ed0ddac34; GitHub Actions https://github.com/tohaa28/relief-forge/actions/runs/44943840009 success; 431 JS и 17 Rust PASS. Реальный мастер: PNG побайтно совпал, 3001×181 на import/analyze/palette/trace, FNV RGBA 1069192609 во всех стадиях, standalone также без изменения. Отдельно растрирование 3165×472, 1199.9976 DPI (pHYs), alpha 0/153. Отказ 4097×1 проверен; текущие безопасные пределы WASM 4096 по стороне / 8 млн пикселей сохраняются. WASM бинарники неизменны. Контракт native-raster-v1 предотвращает передачу в старый мастер. Публикация в gh-pages после синхронизации версии, предыдущая контрольная точка f06691d2fed3fcfb8192c7910519e6fbe54fce5f. Расширение лимитов и реальный частный EPS не подтверждены.

## 2026-11-21 · DoctorTracer 0.21.2-wasm-preview. Исправление входных резких краёв из Relief Forge, PR #2 merged 1f61ffd11968be355daa787b77ccd3f7820dd281. Проверенный функциональный коммит 4e567ee9c8010c702f44733aaa3bc051e6557485. Сквозной Chromium реального мастера, реальный Worker/WASM и тесты политики: Relief Forge PR #124 ffa45188ce823c41a4ba2b9d35a56f6962796392, CircleCI https://app.circleci.com/workflow/c7d566fe-ad7f-4393-b173-17951a177c03/job/e07aa89d-fa50-46b2-aafe-721e66354ab9 success, GitHub Actions https://github.com/tohaa28/relief-forge/actions/runs/44941378586 success. Синтетический PNG 3001×181, импорт 2400×145, анализ 900×54, палитра 500×30 и trace 2400×145: во всех четырёх стадиях ровно четыре RGBA-класса [0,0,0,0; 0,0,255,255; 0,255,0,153; 255,0,0,255]; CSS pixelated в bitmap, вектор без нового CSS, возврат Bitmap корректный. Standalone сохраняет auto и >32 классов при уменьшении, как раньше. WASM бинарники и декодеры не меняются; не пересобирать ядро без нужды. Релизный номер и cache key 0.21.2. Лимит 2400 и порог WASM 128/255 не отменены; тест не гарантирует отсутствия дефектов произвольной EPS геометрии. Предыдущий опубликованный снимок gh-pages 48dfa7b6ea268df1b45bc6ea22981eaba1ee9026. Публикацию подтвердить по live version.json.

# DoctorTracer — начать здесь

Обновление 29.10.2026: Windows **0.18.0-preview** / WASM **0.20.0-wasm-preview** — «Выравнивание контуров»: общие прямые и глобальная подгонка плавных дуг готового SVG. [Описание и проверки](docs/REGULARIZE_020.md). Pages: https://tohaa28.github.io/DoctorTracer/?v=0.20.0 .

Обновление 29.10.2026: Windows **0.17.0-preview** / WASM **0.19.0-wasm-preview** — восстановление тонких овальных рамок и острых звёзд в малых двухцветных логотипах на высоком качестве. [Описание, сравнение NF и ограничения](docs/LOGO_HIGH_019.md). Pages: https://tohaa28.github.io/DoctorTracer/?v=0.19.0 .

Обновление 28.10.2026: Windows **0.16.0-preview** / WASM **0.18.0-wasm-preview** — модуль «Очистка и упрощение»: удаление изолированных островков и сокращение узлов общих кривых, предпросмотр, отмена. [Описание и проверки](docs/POST_CLEAN_018.md). Pages: https://tohaa28.github.io/DoctorTracer/?v=0.18.0 .

Обновление 28.10.2026: Windows **0.15.0-preview** / WASM **0.17.0-wasm-preview** — дополнительное сглаживание готовых векторов, предпросмотр, сила, защита углов, применение/отмена. [Описание и проверки](docs/POST_SMOOTH_017.md). Pages: https://tohaa28.github.io/DoctorTracer/?v=0.17.0 .

Обновление 28.10.2026: Windows **0.14.2** / WASM **0.16.3** строят общие границы цветов и проверяют точное совпадение обеих сторон, включая прозрачность. [Описание и проверки](docs/SHARED_BOUNDARIES_0163.md).

Обновление 28.10.2026: Windows **0.14.1** / WASM **0.16.2** исправляют расширение чёрных контуров при малой палитре. [Причина и проверки](docs/AA_SUPPORT_0162.md).

Обновление 28.10.2026: **WASM 0.16.1** удаляет внутренние границы квадратов из результата трассировки. [Описание и проверки](docs/TILE_SEAMS_0161.md). Windows 0.14 проверена тем же тестом; этап объединения в ней уже был.

Обновление 26.10.2026: Windows **0.14.0-preview** / WASM **0.16.0-wasm-preview**. Совместное уточнение палитры, выбор кривых по полному растру, ускоренный аудит и исправление Chelsea. [Методика и ограничения](docs/QUALITY_016.md), [числа](docs/QUALITY_016_RESULTS.json).

Обновление качества 26.10.2026: Windows **0.13.0-preview** / WASM **0.15.0-wasm-preview**. [Изменения и ограничения](docs/QUALITY_015.md), [числа](docs/QUALITY_015_RESULTS.json). Ограниченная палитра фото: MAE 10.084→8.015; Chelsea ухудшается. Подбор смеси/общих границ и локальный refit; это не глобальная оптимизация и не равенство VM. Pages: https://tohaa28.github.io/DoctorTracer/?v=0.15.0 .

Испытания 26.10.2026: [внешний стенд v2](docs/PUBLIC_BENCHMARK_V2.md), 12 новых входов / 48 эталонов VM / 96 результатов. Главная проблема — подбор ограниченной палитры; oracle-опыт 10.08→1.85 не является исправлением алгоритма. Один стрессовый тест переносимости WASM не прошёл. [Исследование алгоритма VM](docs/VECTOR_MAGIC_ALGORITHM_RESEARCH.md). Версии приложений не менялись.

Обновление GPU 26.10.2026: Windows **0.12.0-preview**, WASM **0.14.0-wasm-preview**. [Перенос операций, замеры и проверки](docs/GPU_CONTOURS_014.md). Pages: https://tohaa28.github.io/DoctorTracer/?v=0.14.0 .

Обновление 26.10.2026: палитры исправлены в Windows **0.11.1-preview** и WASM **0.13.1-wasm-preview**. [Описание и проверки](docs/PALETTE_FIX_0131.md). Прозрачность занимает слот в интерфейсе, но исключена из RGB-палитры ядра. Pages: https://tohaa28.github.io/DoctorTracer/?v=0.13.1 . Ниже сохранён предыдущий снимок контекста.

Снимок контекста: 25 октября 2026, Europe/Moscow.

1. [История разработки и требования](docs/PROJECT_HISTORY.md).
2. [Текущее состояние и продолжение](docs/CONTINUE_HERE.md).
3. [Методика проверки Desktop/WASM](docs/DESKTOP_WASM_PARITY.md).
4. [Неудачные подходы](docs/FAILED_APPROACHES.md), [лицензии](NOTICE.md).

Рабочая ветка: `spatial-photo-preview`. Последнее изменение приложения перед
фиксацией истории: `eccf5c9` — PDF по умолчанию в обеих версиях.
История коммитов и релизов: [машиночитаемый снимок](docs/development-snapshot.json).

Релизы: [Windows 0.10.3](https://github.com/tohaa28/DoctorTracer/releases/tag/v0.10.3-preview),
[WASM 0.12.1](https://github.com/tohaa28/DoctorTracer/releases/tag/v0.12.1-wasm-preview).
[Работающее приложение](https://tohaa28.github.io/DoctorTracer/?v=0.12.1).

Пользовательские изображения и эталонные экспорты остаются локально.
Это инженерная история по доступному чату, Git, отчётам и переданному handoff,
а не дословный экспорт всех разговоров. Первые прототипы до первого коммита
не имеют отдельной восстановимой ревизии в этом репозитории.

Испытательный стенд с корпусом и реальными эталонами Vector Magic: [quality/README.md](quality/README.md).

Обновление алгоритма Windows 0.11 / WASM 0.13: [QUALITY_013.md](docs/QUALITY_013.md).
