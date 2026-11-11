# Автоматическое выделение розыгрышей в волейбольном видео

Учебный проект по практике (задания ИР 1 и ИР 4). Веб-приложение принимает запись
волейбольного матча, в фоне анализирует её нейросетями и возвращает список розыгрышей:

```json
{"video_id": 1, "rallies": [{"number": 1, "start": 20.68, "end": 29.04, "start_frame": 517, "end_frame": 726, "serve_side": "unknown"}]}
```

- мяч ищет модель **VballNet** из репозитория
  [fast-volleyball-tracking-inference](https://github.com/asigatchov/fast-volleyball-tracking-inference) (ONNX);
- игроков ищет **YOLO26** ([Ultralytics](https://docs.ultralytics.com/ru/models/yolo26));
- по покадровым данным простой пороговый алгоритм размечает кадры как `GAME` / `NON_GAME`
  и собирает из них интервалы розыгрышей.

Стек: React, FastAPI, SQLAlchemy, Alembic, SQLite, Redis, Celery, Docker Compose.

## Структура

```text
volleyball-practice/
├── backend/
│   ├── app/
│   │   ├── main.py          # HTTP API (FastAPI)
│   │   ├── models.py        # таблицы БД (SQLAlchemy)
│   │   ├── schemas.py       # форматы запросов и ответов (Pydantic)
│   │   ├── database.py      # подключение к SQLite
│   │   ├── tasks.py         # фоновая задача Celery
│   │   ├── detection.py     # нейросети: мяч (VballNet) и игроки (YOLO26)
│   │   ├── rallies.py       # алгоритм GAME/NON_GAME и выделение розыгрышей
│   │   ├── video_utils.py   # FPS, размер и длительность видео
│   │   └── config.py        # пути и настройки
│   ├── alembic/             # миграции базы данных
│   ├── models/              # веса нейросетей (ONNX и yolo26n.pt)
│   ├── scripts/             # анализ видео из консоли, оценка качества, сравнение моделей
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # интерфейс на React
├── docs/                    # архитектура, ER-диаграмма, схемы, графики эксперимента
├── examples/                # эталонная разметка и результаты эксперимента
├── docker-compose.yml
├── EXPLANATION.md           # подробное объяснение проекта
└── report.docx              # отчёт по практике
```

## Запуск через Docker Compose

Нужен Docker Desktop (или Docker Engine с плагином compose).

```bash
docker compose up --build
```

- интерфейс: http://localhost:5173
- документация API (Swagger): http://localhost:8000/docs

Первая сборка образа бэкенда занимает несколько минут: скачиваются PyTorch и другие библиотеки.
База и загруженные видео хранятся в томе `app-data` и не пропадают при перезапуске.
Остановить: `docker compose down` (добавьте `-v`, чтобы удалить и данные).

## Запуск без Docker

Нужны Python 3.12, Node.js 22+ и Redis.

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head                       # создать базу backend/data/app.db

docker run -d -p 6379:6379 redis:8.8-alpine   # или локальный redis-server
uvicorn app.main:app --reload              # API на http://localhost:8000
celery -A app.tasks worker --loglevel=info --concurrency=1   # в отдельном терминале

cd ../frontend
npm install
npm run dev                                # интерфейс на http://localhost:5173
```

## Проверка

Проект проверен целиком в Docker Compose: запросы к API через curl (примеры с реальными
ответами — в `examples/api_examples.md`) и сценарий в браузере Chrome (загрузка ролика, обработка,
вывод розыгрышей). Качество алгоритма оценено по ручной разметке скриптом `scripts/evaluate.py`.

## Анализ видео из консоли

Из папки `backend`:

```bash
# нейросети + розыгрыши, результаты в папке results/
python -m scripts.analyze_video путь/к/видео.mp4 --out results

# только алгоритм по готовым детекциям, с другими параметрами
python -m scripts.analyze_video --detections results/video_detections.json --max-gap 1.5

# качество по ручной разметке и перебор параметров
python -m scripts.evaluate ../examples/experiment/teva_kamnik_2012_part_detections.json \
    ../examples/ground_truth/teva_kamnik_2012_part.json --sweep

# сравнение детекторов мяча по разметке мяча
python -m scripts.compare_ball_models видео.mp4 разметка_ball.csv
```

## Параметры алгоритма

| Параметр | По умолчанию | Смысл |
|---|---|---|
| `min_speed` | 0.1 ширины кадра/с | мяч быстрее этого считается летящим, медленнее — в руках или на полу |
| `max_gap` | 1.0 с | пропуск детекции мяча внутри розыгрыша, который заполняется |
| `min_duration` | 2.0 с | более короткие игровые фрагменты отбрасываются как шум |
| `merge_gap` | 2.0 с | сегменты с паузой не больше этой склеиваются в один розыгрыш |

Параметры задаются в `RallyParams` (`backend/app/rallies.py`) и флагами скрипта `analyze_video`.

## Результаты эксперимента

- Детекция мяча на трёх роликах со статичной камерой (по разметке автора датасета):
  VballNet — F1 0,79–0,87; YOLO26n с классом «sports ball» — F1 0,00–0,30.
  Поэтому мяч ищет VballNet, а YOLO26 — игроков (список игроков `players[]` входит во временной ряд,
  алгоритм розыгрышей его не использует).
- Фрагмент телетрансляции 7 мин 56 с, 16 размеченных вручную розыгрышей: найден 31 интервал,
  13 из 16 розыгрышей совпали с эталоном (IoU ≥ 0,5); покадровые точность 0,51, полнота 0,76, F1 0,61.
- Ролики со статичной камерой с непрерывной игрой: найдено по одному интервалу, например 0,0–32,6 с
  на ролике длительностью 33 с.

Подробности — в `docs/architecture.md`, `examples/README.md` и в отчёте.

## Ограничения

- Модель мяча обучена на съёмке статичной камерой; на телетрансляции с монтажом и крупными
  планами мяч находится только в 35 % кадров розыгрышей, отсюда ложные и пропущенные интервалы.
- Сторона подачи (`serve_side`) не определяется — всегда `unknown` (это бонус задания ИР 5).
- Обработка идёт на CPU: без Docker 8 минут видео 854×480 обрабатываются примерно за 8 минут. В Docker Desktop
  на macOS нейросети работают в 2,5–3 раза медленнее: ролик 33 с обрабатывался 5 мин 48 с вместо 49 с.
- Регистрации и входа нет: это задание ИР 2. Таблица `users` есть в базе по заданию ИР 1,
  а поле `videos.user_id` пока остаётся пустым.
- Временной ряд детекций хранится в памяти воркера целиком; для записи всего матча (около 2 часов)
  это сотни мегабайт, такое видео лучше обрабатывать частями.

## Лицензии сторонних компонентов

- Модели VballNet (`backend/models/*.onnx`) — MIT, © Alexander Sigatchov,
  см. `backend/models/LICENSE-fast-volleyball-tracking.txt`.
- YOLO26 и пакет `ultralytics` — AGPL-3.0.
