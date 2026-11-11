import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, UploadFile, status
from kombu.exceptions import OperationalError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import ALLOWED_VIDEO_EXTENSIONS, UPLOAD_DIR
from app.database import get_db
from app.models import ProcessingJob, Video
from app.schemas import JobOut, RalliesOut, VideoOut
from app.tasks import process_video
from app.video_utils import read_video_info

app = FastAPI(title="Volleyball Rally Analyzer")

DbSession = Annotated[Session, Depends(get_db)]


def get_video_or_404(db: Session, video_id: int) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Видео не найдено")
    return video


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/videos", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
def upload_video(file: UploadFile, db: DbSession):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Поддерживаются файлы mp4, mov, avi, mkv")

    # Уникальное имя на диске, чтобы файлы с одинаковыми именами не перезаписывали друг друга
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    with path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    info = read_video_info(path)
    if info is None:
        path.unlink()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Не удалось прочитать видеофайл")

    video = Video(
        filename=file.filename,
        file_path=str(path),
        duration=info["duration"],
        fps=info["fps"],
        width=info["width"],
        height=info["height"],
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


@app.get("/api/videos", response_model=list[VideoOut])
def list_videos(db: DbSession):
    return db.scalars(select(Video).order_by(Video.id.desc())).all()


@app.get("/api/videos/{video_id}", response_model=VideoOut)
def get_video(video_id: int, db: DbSession):
    return get_video_or_404(db, video_id)


@app.post("/api/videos/{video_id}/process", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def start_processing(video_id: int, db: DbSession):
    video = get_video_or_404(db, video_id)
    if video.status in ("queued", "processing"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Видео уже стоит в очереди или обрабатывается")

    job = ProcessingJob(video=video)
    video.status = "queued"
    db.add(job)
    db.commit()

    # Задача уходит в очередь Redis, её выполнит воркер Celery
    try:
        process_video.delay(job.id)
    except OperationalError:
        job.status = "error"
        job.error_message = "Очередь задач Redis недоступна"
        video.status = "error"
        db.commit()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, job.error_message)
    return job


@app.get("/api/videos/{video_id}/job", response_model=JobOut)
def get_last_job(video_id: int, db: DbSession):
    video = get_video_or_404(db, video_id)
    if not video.jobs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Видео ещё не отправлялось на обработку")
    return video.jobs[-1]


@app.get("/api/videos/{video_id}/rallies", response_model=RalliesOut)
def get_rallies(video_id: int, db: DbSession):
    video = get_video_or_404(db, video_id)
    rallies = [
        {
            "number": rally.number,
            "start": rally.start_time,
            "end": rally.end_time,
            "start_frame": rally.start_frame,
            "end_frame": rally.end_frame,
            "serve_side": rally.serve_side,
        }
        for rally in video.rallies
    ]
    return {"video_id": video.id, "rallies": rallies}
