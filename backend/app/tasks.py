import json
from datetime import datetime, timezone
from pathlib import Path

from celery import Celery
from celery.utils.log import get_task_logger

from app.config import BALL_MODEL_PATH, PLAYER_MODEL, REDIS_URL, RESULTS_DIR
from app.database import SessionLocal
from app.models import ProcessingJob, Rally
from app.rallies import RallyParams, find_rallies

# Redis используется как брокер: API кладёт задачу в очередь, воркер её забирает
celery_app = Celery("volleyball", broker=REDIS_URL)
logger = get_task_logger(__name__)


@celery_app.task(name="process_video")
def process_video(job_id: int) -> None:
    # PyTorch и ONNX Runtime загружаются только в воркере, API их не импортирует
    from app.detection import detect_video

    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            logger.warning("Задание %s не найдено", job_id)
            return
        video = job.video
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        video.status = "processing"
        db.commit()

        def save_progress(percent: int) -> None:
            job.progress = percent
            db.commit()

        try:
            detections = detect_video(Path(video.file_path), BALL_MODEL_PATH, PLAYER_MODEL, save_progress)

            # Покадровые детекции сохраняются в JSON-файл, в БД остаётся только путь к нему
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            detections_path = RESULTS_DIR / f"job_{job.id}_detections.json"
            detections_path.write_text(json.dumps(detections))

            rallies = find_rallies(detections["frames"], detections["fps"], detections["width"], RallyParams())

            # При повторной обработке старые розыгрыши удаляются
            video.rallies.clear()
            db.flush()
            for rally in rallies:
                video.rallies.append(
                    Rally(
                        number=rally["number"],
                        start_time=rally["start"],
                        end_time=rally["end"],
                        start_frame=rally["start_frame"],
                        end_frame=rally["end_frame"],
                        serve_side=rally["serve_side"],
                    )
                )
            job.detections_path = str(detections_path)
            job.status = "completed"
            job.progress = 100
            video.status = "completed"
        except Exception as error:
            logger.exception("Ошибка в задании %s", job_id)
            db.rollback()
            job.status = "error"
            job.error_message = str(error)[:1000]
            video.status = "error"

        job.finished_at = datetime.now(timezone.utc)
        db.commit()
