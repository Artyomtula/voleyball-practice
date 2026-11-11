import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Все данные приложения (база, загруженные видео, результаты) лежат в одной папке
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
RESULTS_DIR = DATA_DIR / "results"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Модель мяча из репозитория fast-volleyball-tracking-inference и модель игроков YOLO26
BALL_MODEL_PATH = Path(
    os.getenv("BALL_MODEL_PATH", BASE_DIR / "models" / "VballNetV4c_seq9_grayscale_20260908_213829.onnx")
)
PLAYER_MODEL = os.getenv("PLAYER_MODEL", str(BASE_DIR / "models" / "yolo26n.pt"))

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
