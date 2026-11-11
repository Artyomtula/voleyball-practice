"""Сравнение детекторов мяча с эталонной разметкой.

Сравниваются модели VballNet (fast-volleyball-tracking) и YOLO26 с классом COCO «sports ball».
Разметка - CSV из датасета автора fast-volleyball-tracking: Frame, Visibility, X, Y.

Запуск из папки backend:
    python -m scripts.compare_ball_models video.mp4 video_ball.csv
"""

import argparse
import csv
import math
import time
from pathlib import Path

import cv2
from ultralytics import YOLO

from app.config import BASE_DIR, PLAYER_MODEL
from app.detection import SEQUENCE_LENGTH, BallDetector, read_frames

SPORTS_BALL_CLASS = 32
VBALLNET_MODELS = [
    BASE_DIR / "models" / "VballNetV4c_seq9_grayscale_20260908_213829.onnx",
    BASE_DIR / "models" / "VballNetFastV1_seq9_grayscale_233_h288_w512.onnx",
]


def load_truth(path: Path) -> dict[int, tuple[float, float] | None]:
    truth = {}
    with path.open() as file:
        for row in csv.DictReader(file):
            visible = int(row["Visibility"]) == 1
            truth[int(row["Frame"])] = (float(row["X"]), float(row["Y"])) if visible else None
    return truth


def vballnet_points(video: Path, model_path: Path) -> list:
    detector = BallDetector(model_path)
    capture = cv2.VideoCapture(str(video))
    points = []
    while True:
        batch = read_frames(capture, SEQUENCE_LENGTH)
        if not batch:
            break
        points += [None if ball["x"] is None else (ball["x"], ball["y"]) for ball in detector.detect(batch)]
    capture.release()
    return points


def yolo_points(video: Path, model_path: str, image_size: int) -> list:
    model = YOLO(model_path)
    capture = cv2.VideoCapture(str(video))
    points = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        boxes = model.predict(frame, classes=[SPORTS_BALL_CLASS], imgsz=image_size, verbose=False)[0].boxes
        if len(boxes) == 0:
            points.append(None)
            continue
        x1, y1, x2, y2 = boxes.xyxy[int(boxes.conf.argmax())].tolist()
        points.append(((x1 + x2) / 2, (y1 + y2) / 2))
    capture.release()
    return points


def score(points: list, truth: dict, tolerance: float) -> dict:
    """Попадание - точка не дальше tolerance пикселей от размеченного мяча (как в README автора)."""
    tp = fp = fn = 0
    for frame, point in enumerate(points):
        true_point = truth.get(frame)
        if point is None:
            fn += true_point is not None
        elif true_point is not None and math.dist(point, true_point) <= tolerance:
            tp += 1
        else:
            fp += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Сравнение детекторов мяча")
    parser.add_argument("video", type=Path)
    parser.add_argument("truth", type=Path)
    args = parser.parse_args()

    truth = load_truth(args.truth)
    width = cv2.VideoCapture(str(args.video)).get(cv2.CAP_PROP_FRAME_WIDTH)
    tolerance = 9 * width / 1920  # 9 пикселей при ширине кадра 1920

    candidates = [(path.stem.split("_")[0], lambda p=path: vballnet_points(args.video, p)) for path in VBALLNET_MODELS]
    candidates += [
        (f"YOLO26n sports ball, imgsz={size}", lambda s=size: yolo_points(args.video, PLAYER_MODEL, s))
        for size in (640, 1280)
    ]

    print("model | precision | recall | f1 | ms_per_frame")
    for name, predict in candidates:
        started = time.perf_counter()
        points = predict()
        ms_per_frame = (time.perf_counter() - started) * 1000 / len(points)
        result = score(points, truth, tolerance)
        print(f"{name} | {result['precision']} | {result['recall']} | {result['f1']} | {ms_per_frame:.1f}")


if __name__ == "__main__":
    main()
