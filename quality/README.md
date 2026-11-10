# Стенд качества DoctorTracer

## Новый внешний набор v2 (26.10.2026)

12 новых входов из интернета, фиксированные коммиты, хеши и лицензии; 48 реальных эталонов VM 1.15, по 48 трассировок Windows/WASM. [Методика и результаты](../docs/PUBLIC_BENCHMARK_V2.md). Старый корпус ниже остаётся отдельным экспериментом.

```powershell
python quality/public_corpus.py
python quality/bench.py --corpus build/quality-public-v2 queue
python quality/bench.py --corpus build/quality-public-v2 run --name desktop-public-v2 --engine desktop --profiles photo-medium-auto,photo-high-auto,photo-medium-9,graphic-medium-9 --compute cpu
python quality/bench.py --corpus build/quality-public-v2 run --name wasm-public-v2 --engine wasm --profiles photo-medium-auto,photo-high-auto,photo-medium-9,graphic-medium-9 --compute cpu
```

До сравнения получить SVG в установленной VM для всех входов и каждого из четырёх профилей. В пакетном режиме явно выбрать тип (фото / рисунок со смешиванием), Medium/High и свободную палитру либо лимит 9. Сохранить прозрачность. Перед обработкой снять настройки, после неё сохранить реальные SVG и импортировать каждый профиль:

```powershell
python quality/bench.py --corpus build/quality-public-v2 import-batch --directory build/quality-public-v2/vm-raw/photo-medium-9 --profile photo-medium-9 --evidence build/quality-public-v2/vm-raw/photo-medium-9/settings.png --version 1.15 --verified --notes "Настройки проверены в интерфейсе VM"
python quality/bench.py --corpus build/quality-public-v2 compare --run desktop-public-v2 --name desktop-public-v2 --require-complete
python quality/bench.py --corpus build/quality-public-v2 compare --run wasm-public-v2 --name wasm-public-v2 --require-complete
python quality/palette_diagnostic.py --corpus build/quality-public-v2
python quality/public_report.py --corpus build/quality-public-v2
```

`--verified` допустим только после проверки реальной программы. Повторить import-batch для остальных трёх профилей с соответствующими путями/снимками. Не подменять эталоны результатами DoctorTracer. Существующие прогоны/отчёты не перезаписывать: новое имя для нового эксперимента. Объединённый public_report ожидает имена из примера; для новой серии использовать отдельный каталог корпуса. Все новые метрики применяются к schema 2, старые schema 1 сохраняют прежнюю семантику.

Прозрачность занимает слот лимита. Кандидат получает предложение палитры из своего мастера; одинаковый лимит с VM не означает одинаковые RGB. Отдельный palette_diagnostic использует RGB из эталона и **не включается** в независимую оценку. 20 комбинаций соответствуют типу входа, 28 — стрессовые. Фильтры и шторка работают в HTML без сервера; известные SVG дополнительно сравниваются при ×4. Стенд не доказывает равенство качества по одному MAE/F1. Контролируемого тайминга VM нет; CPU-серия не заменяет прежние GPU-тесты.


Локальный корпус, подтверждённые SVG Vector Magic, версии результатов Desktop/WASM,
HTML-отчёт и контроль регрессий. Все данные по умолчанию в игнорируемом `build/quality`.
Стенд не меняет алгоритм приложения и не требует отправки изображений на сервер.

## Создать корпус

```powershell
python quality/bench.py init
python quality/bench.py add-image --id my-photo --input C:/images/photo.jpg --category photo --split holdout
```

Генератор создаёт 40 оригинальных PNG: по 5 вариантов логотипов, текста, тонких
линий, отверстий, полупрозрачности, градиентов, текстур и условной акварели.
24 development и 16 holdout. Варианты одного генератора коррелируют: holdout
здесь предназначен для технической регрессии, не доказывает обобщение на реальные
фотографии. Для полноценной проверки нужны дополнительные ранее не использованные
реальные входы. Текст использует установленный Arial или DejaVu/встроенный шрифт;
переносить уже созданные PNG вместе с manifest, а не полагаться на побайтную
идентичность шрифтов разных ОС. SHA-256 исходников фиксируется в corpus.json.

В локальном первом корпусе добавлены два прежних пользовательских изображения:
42 входа. Они отмечены development, поскольку уже участвовали в подборе алгоритма.
В Git их нет. Изменение PNG/JPG после регистрации обнаруживается до запуска.

## Получить настоящие эталоны

`reference-queue.json` перечисляет входы/профили и фактическое покрытие.
Доступны photo-medium-auto, photo-high-auto, photo-medium-9, graphic-medium-9,
hard-medium-2. Первая серия собрана только для первых и третьих профилей.
Остальные профили остаются в очереди; их нельзя считать проверенными.

В Vector Magic Desktop 1.15 открыть **Пакетная обработка**, добавить входы из
inputs/. Установить явно тип, качество, цветовой режим/количество, сохранение
прозрачности и SVG; использовать пустую отдельную выходную папку для каждого
профиля. Сделать скриншот настроек до запуска и проверить завершение/число файлов.
В первом прогоне использовался размер «По рекомендации», все входы менее 1000 px.
Фоторежим на логотипах — намеренный тест одного фиксированного режима, не выбор
наилучшего режима для каждого сюжета. Для графики есть отдельные профили.

```powershell
python quality/bench.py import-batch --directory build/quality/vm-raw/photo-medium-auto --profile photo-medium-auto --evidence build/quality/vm-raw/photo-medium-auto/settings.png --version 1.15 --verified --notes "Photo / Medium / Unlimited / Preserve / SVG; recommended size"
```

Или отдельный экспорт через базовый мастер:

```powershell
python quality/bench.py reference --id logo-01 --profile graphic-medium-9 --svg C:/references/logo-01.svg --evidence C:/references/settings.png --version 1.15 --wizard basic --verified
```

`--verified` — утверждение оператора о реально проверенных настройках, не
автоматическое распознавание скриншота. Без флага эталон не входит в метрики.
Сохраняются версия, источник, настройки, SHA исходника/SVG/доказательства.
Существующий эталон не перезаписывается. Если получен другой набор настроек,
создать новый корпус/профиль в версии стенда. Имя файла само по себе не доказательство.

Одинаковое число цветов **не означает одинаковые RGB**: эти профили намеренно
проверяют весь процесс, включая автоматический выбор палитры каждой программой.
Сравнение при общей явно заданной RGB-палитре — отдельный будущий профиль.

## Запуски и отчёт

Из корня репозитория (Python с desktop/requirements.txt, Node для WASM):

```powershell
python quality/bench.py run --name desktop-v1 --profiles photo-medium-auto,photo-medium-9
python quality/bench.py run --name wasm-v1 --engine wasm --profiles photo-medium-auto,photo-medium-9
python quality/bench.py compare --run desktop-v1 --name desktop-report --require-complete
python quality/bench.py compare --run wasm-v1 --baseline desktop-v1 --name wasm-report --require-complete
```

Для быстрого контроля добавить `--ids logo-01,holes-01` к run. Общий параметр
`--corpus <папка>` ставится перед подкомандой. Имена прогонов/отчётов уникальны:
результат baseline не перезаписывается. CPU выбран явно для воспроизводимости;
это тест качества алгоритма, не измерение скорости GPU в браузере.
Профили базового мастера используют cleanup=0, spatial_strength=200 для unlimited
и 700 для fixed-photo, допуск кривых .12×4/2/1. Соответствие Qt-мастеру проверяет
tests/quality_bench.py; прежняя ошибка перевода описана в ../docs/QUALITY_013.md.
Node вызывает настоящий опубликованный Rust WASM и Potrace/Skia/Clipper адаптеры.

Отчёт: `build/quality/reports/<name>/index.html`, рядом report.json и assets/.
Доступны поиск, фильтр подтверждённых случаев, полноразмерные картинки и шторка.
При baseline показываются исходник → VM → предыдущий результат → кандидат → разница.
HTML работает без внешних скриптов; для просмотра через браузер:

```powershell
python -m http.server 8770 --bind 127.0.0.1
```

Открыть http://127.0.0.1:8770/build/quality/reports/desktop-report/ .
Папку отчёта можно скопировать целиком для офлайн-просмотра. Она содержит входы,
поэтому её нельзя автоматически публиковать в GitHub Pages.

## Метрики и ограничения

- RGB MAE (0–255) после композиции на белый 255 и тёмный 40; alpha MAE отдельно.
- Alpha IoU при пороге 128; число связных компонент (8-связность) и отверстий.
  У непрозрачного фото эти топологические метрики описывают только силуэт.
- F1 границ Canny на белой композиции, допуск 1 px (квадрат 3×3).
- Число SVG paths и команд; это не равнозначно числу редактируемых узлов Corel.
- Секунды вызова движка записываются, но не являются cold/warm GPU-бенчмарком.

Обе SVG растеризуются **одним** независимым QPainterPath-рендерером с 3× выборкой,
на исходной сетке, с одинаковой обработкой краёв. Он не использует SVG-парсер Qt,
который ранее пропускал слишком большие пути. Поддерживается фактический экспортный
диалект M/L/C/Z, fill/opacity, группы, translate/scale/matrix. Неподдерживаемые
эффекты и команды вызывают ошибку, а не ложную оценку.
Методика отличается от прежнего production-preview рендера; числа между двумя
методиками напрямую сравнивать нельзя. SVG с растровой подложкой не принимаются.
Пересечения векторов и цветовая иерархия PDF проверяются отдельными существующими
geometry/PDF-тестами, по одному рендеру их отсутствие доказать нельзя.

Пропущенные эталоны не входят в средние. `--require-complete` завершает compare
кодом 2 при неполном покрытии; ошибки кандидата тоже дают код 2.
При baseline код 2 означает также регрессию: MAE белый вырос >0.1, IoU упал
>0.001 или boundary F1 упал >0.01. Допуски настраиваются аргументами.
Это допуски ухудшения относительно baseline, **не** критерий «как Vector Magic».
Сравнения с разными настройками/изменёнными файлами отклоняются. Отсутствующий
случай baseline при запросе сравнения также завершает gate ошибкой. Всегда смотреть
отдельные случаи и группы профилей/development/holdout; средняя ошибка может скрыть
пропавшую тонкую деталь. Фотографии и синтетика не должны подменять друг друга.

Проверка самого стенда: `python tests/quality_bench.py`.
