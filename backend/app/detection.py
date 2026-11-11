"""Нейросетевая часть: мяч ищет модель fast-volleyball-tracking (ONNX), игроков - YOLO26."""

from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from ultralytics import YOLO

from app.video_utils import read_video_info

# Модель мяча получает 9 кадров подряд в оттенках серого размером 512x288
SEQUENCE_LENGTH = 9
INPUT_WIDTH = 512
INPUT_HEIGHT = 288
PERSON_CLASS = 0  # номер класса «person» в наборе COCO


def preprocess(frame: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (INPUT_WIDTH, INPUT_HEIGHT))
    return gray.astype(np.float32) / 255.0


def find_ball(heatmap: np.ndarray, threshold: float, scale_x: float, scale_y: float) -> dict:
    """Центр самой большой области тепловой карты выше порога, в координатах исходного кадра."""
    mask = (heatmap > threshold).astype(np.uint8)
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask)
    if count < 2:  # метка 0 - это фон, значит мяч не найден
        return {"x": None, "y": None, "confidence": float(heatmap.max())}
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y = centroids[biggest]
    confidence = float(heatmap[labels == biggest].max())
    return {"x": x * scale_x, "y": y * scale_y, "confidence": confidence}


class BallDetector:
    """Модель VballNet из репозитория fast-volleyball-tracking-inference."""

    def __init__(self, model_path: Path, threshold: float = 0.5):
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.threshold = threshold

    def detect(self, frames: list[np.ndarray]) -> list[dict]:
        clip = [preprocess(frame) for frame in frames]
        while len(clip) < SEQUENCE_LENGTH:  # неполный последний пакет дополняем копиями кадра
            clip.append(clip[-1])
        tensor = np.stack(clip)[np.newaxis]  # форма (1, 9, 288, 512)
        output = self.session.run(None, {self.input_name: tensor})[0][0]

        # Первые 9 каналов выхода - тепловые карты (у VballNetV4c дальше идут карты радиуса мяча)
        height, width = frames[0].shape[:2]
        scale_x, scale_y = width / INPUT_WIDTH, height / INPUT_HEIGHT
        return [find_ball(output[i], self.threshold, scale_x, scale_y) for i in range(len(frames))]


class PlayerDetector:
    """YOLO26, предобученная на COCO: из всех классов берём только людей."""

    def __init__(self, model_name: str, confidence: float = 0.3):
        self.model = YOLO(model_name)
        self.confidence = confidence

    def detect(self, frames: list[np.ndarray]) -> list[list[list[float]]]:
        results = self.model.predict(frames, classes=[PERSON_CLASS], conf=self.confidence, verbose=False)
        players = []
        for result in results:
            boxes = result.boxes.xyxy.tolist()
            scores = result.boxes.conf.tolist()
            players.append([[round(v, 1) for v in box] + [round(score, 3)] for box, score in zip(boxes, scores)])
        return players


def read_frames(capture: cv2.VideoCapture, count: int) -> list[np.ndarray]:
    frames = []
    for _ in range(count):
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    return frames


def detect_video(
    video_path: Path,
    ball_model_path: Path,
    player_model: str,
    on_progress: Callable[[int], None] | None = None,
) -> dict:
    """Покадровый временной ряд: frame, ball_x, ball_y, ball_confidence, players[].

    players - список рамок [x1, y1, x2, y2, confidence] в пикселях исходного кадра.
    """
    info = read_video_info(video_path)
    if info is None:
        raise ValueError(f"Не удалось открыть видео {video_path}")
    ball_detector = BallDetector(ball_model_path)
    player_detector = PlayerDetector(player_model)

    frames = []
    last_percent = -1
    capture = cv2.VideoCapture(str(video_path))
    try:
        while True:
            batch = read_frames(capture, SEQUENCE_LENGTH)
            if not batch:
                break
            balls = ball_detector.detect(batch)
            players = player_detector.detect(batch)
            for ball, boxes in zip(balls, players):
                frames.append(
                    {
                        "frame": len(frames),
                        "ball_x": None if ball["x"] is None else round(ball["x"], 1),
                        "ball_y": None if ball["y"] is None else round(ball["y"], 1),
                        "ball_confidence": round(ball["confidence"], 3),
                        "players": boxes,
                    }
                )
            percent = min(99, len(frames) * 100 // info["frame_count"])
            if on_progress and percent != last_percent:
                on_progress(percent)
                last_percent = percent
    finally:
        capture.release()

    return {
        "fps": info["fps"],
        "width": info["width"],
        "height": info["height"],
        "frame_count": len(frames),
        "frames": frames,
    }
