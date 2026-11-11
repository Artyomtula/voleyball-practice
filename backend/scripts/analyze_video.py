"""Анализ видео из командной строки, без веб-приложения.

Запуск из папки backend:
    python -m scripts.analyze_video ../examples/video.mp4 --out results
    python -m scripts.analyze_video --detections results/video_detections.json --max-gap 1.5
"""

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from app.config import BALL_MODEL_PATH, PLAYER_MODEL
from app.rallies import RallyParams, find_rallies, format_time


def parse_args() -> argparse.Namespace:
    defaults = RallyParams()
    parser = argparse.ArgumentParser(description="Выделение розыгрышей в волейбольном видео")
    parser.add_argument("video", nargs="?", type=Path, help="видеофайл")
    parser.add_argument("--detections", type=Path, help="готовый JSON с детекциями: нейросети не запускаются")
    parser.add_argument("--out", type=Path, default=Path("results"), help="папка для результатов")
    parser.add_argument("--ball-model", type=Path, default=BALL_MODEL_PATH)
    parser.add_argument("--min-speed", type=float, default=defaults.min_speed)
    parser.add_argument("--max-gap", type=float, default=defaults.max_gap)
    parser.add_argument("--min-duration", type=float, default=defaults.min_duration)
    parser.add_argument("--merge-gap", type=float, default=defaults.merge_gap)
    args = parser.parse_args()
    if args.video is None and args.detections is None:
        parser.error("нужно указать видео или --detections")
    return args


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.detections:
        detections = json.loads(args.detections.read_text())
        name = args.detections.stem.removesuffix("_detections")
    else:
        from app.detection import detect_video

        started = time.perf_counter()
        detections = detect_video(
            args.video, args.ball_model, PLAYER_MODEL, on_progress=lambda p: print(f"\rДетекция: {p}%", end="")
        )
        seconds = time.perf_counter() - started
        print(f"\rДетекция: {detections['frame_count']} кадров за {seconds:.1f} с")
        name = args.video.stem
        (args.out / f"{name}_detections.json").write_text(json.dumps(detections))

    params = RallyParams(args.min_speed, args.max_gap, args.min_duration, args.merge_gap)
    rallies = find_rallies(detections["frames"], detections["fps"], detections["width"], params)

    result = {"video": name, "params": asdict(params), "rallies": rallies}
    result_path = args.out / f"{name}_rallies.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    print(f"Найдено розыгрышей: {len(rallies)}")
    for rally in rallies:
        print(f"Rally {rally['number']}: {format_time(rally['start'])} → {format_time(rally['end'])}")
    print(f"Результат сохранён в {result_path}")


if __name__ == "__main__":
    main()
