# Примеры запросов к API

Ответы получены на запущенном через Docker Compose проекте 11 ноября 2026 г.
на ролике `gtu_20250316_005.mp4` (4,8 с). Регистрации и входа нет, это задание ИР 2.

```bash
B=http://localhost:8000/api
```

## Загрузка видео

```bash
curl -F "file=@gtu_20250316_005.mp4" $B/videos
```
```json
{"id":1,"filename":"gtu_20250316_005.mp4","duration":4.838,"fps":29.97,"width":1920,"height":1080,"status":"uploaded","created_at":"2026-11-11T11:16:23"}
```

Файл с другим расширением — `400 {"detail":"Поддерживаются файлы mp4, mov, avi, mkv"}`.

## Запуск обработки и статус

```bash
curl -X POST $B/videos/1/process
```
```json
{"id":1,"video_id":1,"status":"queued","progress":0,"started_at":null,"finished_at":null,"error_message":null}
```

Повторный запуск, пока видео в очереди: `409 {"detail":"Видео уже стоит в очереди или обрабатывается"}`.

```bash
curl $B/videos/1/job
```
```json
{"id":1,"video_id":1,"status":"processing","progress":0,"started_at":"2026-11-11T11:16:27.151347","finished_at":null,"error_message":null}
```

После завершения (в Docker Desktop на Apple M1 Pro обработка заняла 32 с):

```json
{"id":1,"video_id":1,"status":"completed","progress":100,"started_at":"2026-11-11T11:16:27.151347","finished_at":"2026-11-11T11:16:59.237273","error_message":null}
```

## Розыгрыши

```bash
curl $B/videos/1/rallies
```
```json
{"video_id":1,"rallies":[{"number":1,"start":0.3,"end":4.74,"start_frame":9,"end_frame":142,"serve_side":"unknown"}]}
```

## Несуществующее видео

```bash
curl $B/videos/999   # 404 {"detail":"Видео не найдено"}
```
