"""Оценка качества выделения розыгрышей по ручной разметке и исследование параметров.

Запуск из папки backend:
    python -m scripts.evaluate results/match_detections.json ../examples/ground_truth/match.json
    python -m scripts.evaluate results/match_detections.json ../examples/ground_truth/match.json --sweep
"""

import argparse
import csv
import json
from dataclasses import asdict, replace
from pathlib import Path

from app.rallies import GAME, RallyParams, classify_frames, find_rallies

# Значения для исследования: каждый параметр меняется отдельно, остальные остаются по умолчанию
SWEEP = {
    "min_speed": [0.0, 0.02, 0.05, 0.1, 0.2],
    "max_gap": [0.2, 0.5, 1.0, 1.5, 2.0, 3.0],
    "min_duration": [0.5, 1.0, 2.0, 3.0, 5.0],
    "merge_gap": [0.0, 1.0, 2.0, 3.0, 5.0, 8.0],
}


def frames_in_rallies(rallies: list[dict], fps: float, total: int) -> list[bool]:
    """Разметка кадров по интервалам в секундах: True - кадр внутри розыгрыша."""
    flags = [False] * total
    for rally in rallies:
        start = max(0, round(rally["start"] * fps))
        end = min(total - 1, round(rally["end"] * fps))
        for i in range(start, end + 1):
            flags[i] = True
    return flags


def overlap_ratio(a: dict, b: dict) -> float:
    """IoU двух интервалов: длина пересечения, делённая на длину объединения."""
    intersection = min(a["end"], b["end"]) - max(a["start"], b["start"])
    union = max(a["end"], b["end"]) - min(a["start"], b["start"])
    return max(0.0, intersection) / union if union > 0 else 0.0


def evaluate(predicted: list[dict], truth: list[dict], fps: float, total: int) -> dict:
    # Покадровые метрики для класса GAME
    pred_flags = frames_in_rallies(predicted, fps, total)
    true_flags = frames_in_rallies(truth, fps, total)
    tp = sum(p and t for p, t in zip(pred_flags, true_flags))
    fp = sum(p and not t for p, t in zip(pred_flags, true_flags))
    fn = sum(t and not p for p, t in zip(pred_flags, true_flags))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    # Розыгрыш найден, если с эталонным он пересекается по IoU не меньше 0.5
    matched = []
    used = set()
    for true_rally in truth:
        for i, pred_rally in enumerate(predicted):
            if i not in used and overlap_ratio(true_rally, pred_rally) >= 0.5:
                matched.append((true_rally, pred_rally))
                used.add(i)
                break
    start_error = sum(abs(t["start"] - p["start"]) for t, p in matched) / len(matched) if matched else None
    end_error = sum(abs(t["end"] - p["end"]) for t, p in matched) / len(matched) if matched else None

    return {
        "rallies_true": len(truth),
        "rallies_found": len(predicted),
        "rallies_matched": len(matched),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "start_error": None if start_error is None else round(start_error, 2),
        "end_error": None if end_error is None else round(end_error, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Оценка выделения розыгрышей")
    parser.add_argument("detections", type=Path)
    parser.add_argument("truth", type=Path, help="JSON с ручной разметкой розыгрышей")
    parser.add_argument("--sweep", action="store_true", help="перебрать значения параметров")
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()

    detections = json.loads(args.detections.read_text())
    truth = json.loads(args.truth.read_text())["rallies"]
    frames, fps, width = detections["frames"], detections["fps"], detections["width"]
    total = len(frames)

    def run(params: RallyParams) -> dict:
        rallies = find_rallies(frames, fps, width, params)
        return {**asdict(params), **evaluate(rallies, truth, fps, total)}

    default = RallyParams()
    rows = [run(default)]
    if args.sweep:
        for name, values in SWEEP.items():
            for value in values:
                if value != getattr(default, name):
                    rows.append({"changed": name, **run(replace(default, **{name: value}))})

    labels = classify_frames(frames, fps, width, default)
    game_share = sum(label == GAME for label in labels) / total
    print(f"Кадров: {total}, FPS: {fps}, доля GAME при параметрах по умолчанию: {game_share:.1%}")
    param_names = list(asdict(default))
    columns = ["changed", *param_names, *[name for name in rows[0] if name not in param_names]]
    print(" | ".join(columns))
    for row in rows:
        print(" | ".join(str(row.get(column, "-")) for column in columns))

    args.out.mkdir(parents=True, exist_ok=True)
    out_path = args.out / f"{args.detections.stem.removesuffix('_detections')}_evaluation.csv"
    with out_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "default") for column in columns})
    print(f"Таблица сохранена в {out_path}")


if __name__ == "__main__":
    main()
