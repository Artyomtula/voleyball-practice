"""Выделение розыгрышей по покадровым детекциям мяча и игроков.

Цепочка обработки:
детекции -> траектория и скорость мяча -> временная фильтрация -> GAME/NON_GAME
-> объединение сегментов -> розыгрыши.
"""

import math
from dataclasses import dataclass

GAME = "GAME"
NON_GAME = "NON_GAME"


@dataclass
class RallyParams:
    min_speed: float = 0.1  # мяч считается «живым», если движется быстрее (ширин кадра в секунду)
    max_gap: float = 1.0  # пропуск детекции мяча внутри розыгрыша, который заполняется, с
    min_duration: float = 2.0  # более короткие игровые фрагменты считаются шумом, с
    merge_gap: float = 2.0  # фрагменты с паузой не больше этой объединяются в один розыгрыш, с


def seconds_to_frames(seconds: float, fps: float) -> int:
    return round(seconds * fps)


def format_time(seconds: float) -> str:
    """83.46 -> '01:23.5'"""
    tenths = round(seconds * 10)
    return f"{tenths // 600:02d}:{tenths % 600 / 10:04.1f}"


def ball_speeds(frames: list[dict], fps: float, width: int, max_step: int) -> list[float | None]:
    """Скорость мяча в каждом кадре в ширинах кадра за секунду.

    Скорость считается по предыдущей детекции мяча, если она была не раньше max_step кадров назад.
    Если мяч не найден или предыдущей детекции нет, возвращается None.
    """
    speeds = []
    previous = None
    for item in frames:
        if item["ball_x"] is None:
            speeds.append(None)
            continue
        speed = None
        if previous is not None and item["frame"] - previous["frame"] <= max_step:
            seconds = (item["frame"] - previous["frame"]) / fps
            distance = math.hypot(item["ball_x"] - previous["ball_x"], item["ball_y"] - previous["ball_y"])
            speed = distance / width / seconds
        speeds.append(speed)
        previous = item
    return speeds


def active_frames(frames: list[dict], fps: float, width: int, params: RallyParams) -> list[bool]:
    """Сырая разметка кадров: мяч найден и летит не медленнее порога min_speed."""
    speeds = ball_speeds(frames, fps, width, seconds_to_frames(params.max_gap, fps))
    return [speed is not None and speed >= params.min_speed for speed in speeds]


def fill_gaps(flags: list[bool], max_gap_frames: int) -> list[bool]:
    """Заполняет короткие провалы (не длиннее max_gap_frames) между активными кадрами."""
    result = list(flags)
    last_active = None
    for i, flag in enumerate(flags):
        if not flag:
            continue
        if last_active is not None and i - last_active - 1 <= max_gap_frames:
            for k in range(last_active + 1, i):
                result[k] = True
        last_active = i
    return result


def find_segments(flags: list[bool]) -> list[tuple[int, int]]:
    """Превращает последовательность флагов в отрезки (первый кадр, последний кадр)."""
    segments = []
    start = None
    for i, flag in enumerate(flags):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            segments.append((start, i - 1))
            start = None
    if start is not None:
        segments.append((start, len(flags) - 1))
    return segments


def merge_segments(segments: list[tuple[int, int]], merge_gap_frames: int) -> list[tuple[int, int]]:
    """Объединяет соседние отрезки, если пауза между ними не больше merge_gap_frames."""
    merged = []
    for start, end in segments:
        if merged and start - merged[-1][1] - 1 <= merge_gap_frames:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def classify_frames(frames: list[dict], fps: float, width: int, params: RallyParams) -> list[str]:
    """Состояние GAME/NON_GAME для каждого кадра после временной фильтрации."""
    active = active_frames(frames, fps, width, params)
    game = fill_gaps(active, seconds_to_frames(params.max_gap, fps))
    min_frames = seconds_to_frames(params.min_duration, fps)

    labels = [NON_GAME] * len(frames)
    for start, end in find_segments(game):
        if end - start + 1 >= min_frames:
            for i in range(start, end + 1):
                labels[i] = GAME
    return labels


def find_rallies(frames: list[dict], fps: float, width: int, params: RallyParams | None = None) -> list[dict]:
    """Главная функция: покадровые данные -> список розыгрышей.

    frames - список словарей с ключами frame, ball_x, ball_y (кадры идут подряд с нуля).
    """
    params = params or RallyParams()
    labels = classify_frames(frames, fps, width, params)
    segments = find_segments([label == GAME for label in labels])
    segments = merge_segments(segments, seconds_to_frames(params.merge_gap, fps))

    rallies = []
    for number, (start, end) in enumerate(segments, start=1):
        rallies.append(
            {
                "number": number,
                "start": round(start / fps, 2),
                "end": round(end / fps, 2),
                "start_frame": start,
                "end_frame": end,
                "serve_side": "unknown",
            }
        )
    return rallies
