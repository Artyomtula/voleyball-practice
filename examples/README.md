# Данные и результаты эксперимента

Сами видео в архив не входят (сотни мегабайт), но их можно скачать по ссылкам ниже.
Покадровые детекции, полученные нейросетями, лежат в `experiment/` — по ним можно
повторить подбор параметров без видео и без запуска нейросетей.

## Видео

| Файл | Источник | Лицензия |
|---|---|---|
| `gtu_20250316_002.mp4` — 33 с, статичная камера за лицевой линией | [fast-volleyball-tracking-inference/examples](https://github.com/asigatchov/fast-volleyball-tracking-inference/tree/master/examples) | MIT |
| `gtu_20250316_003.mp4`, `gtu_20250316_005.mp4` и разметка мяча `*_ball.csv` | датасет автора [asigatchov/vball-net](https://huggingface.co/datasets/asigatchov/vball-net), папка `test/match_gtu_20250316_backline` | открытый доступ, лицензия не указана |
| `teva_kamnik_2012_part.mp4` — 7 мин 56 с телетрансляции | [TEVA GRC – CALCIT KAMNIK (2012-12-14)](https://commons.wikimedia.org/wiki/File:TEVA_GRC_-_CALCIT_KAMNIK_(2012-12-14).webm), версия 480p, фрагмент с 4:00 до 11:56 | CC BY 3.0, Régió Plusz Televízió |

Фрагмент трансляции вырезан средствами OpenCV: кадры с 6000-го (4:00 при 25 кадрах/с)
до конца скачанной части записаны в MP4 без изменения размера.

## Файлы

- `ground_truth/teva_kamnik_2012_part.json` — ручная разметка 16 розыгрышей фрагмента трансляции
  (шаг просмотра 0,5 с, погрешность границ около 1 с).
- `experiment/*_detections.json` — покадровые детекции: `frame`, `ball_x`, `ball_y`,
  `ball_confidence`, `players[]` (рамки `[x1, y1, x2, y2, confidence]`).
- `experiment/*_rallies.json` — найденные розыгрыши при параметрах по умолчанию.
- `experiment/teva_kamnik_2012_part_evaluation.csv` — исследование параметров.
- `experiment/ball_models.md` — сравнение детекторов мяча.

## Как повторить

Из папки `backend`:

```bash
# розыгрыши по готовым детекциям
python -m scripts.analyze_video --detections ../examples/experiment/teva_kamnik_2012_part_detections.json

# оценка по ручной разметке и перебор параметров
python -m scripts.evaluate ../examples/experiment/teva_kamnik_2012_part_detections.json \
    ../examples/ground_truth/teva_kamnik_2012_part.json --sweep

# полный анализ видео с нейросетями
python -m scripts.analyze_video путь/к/видео.mp4 --out results
```
