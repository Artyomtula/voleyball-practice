from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

VIDEO_STATUSES = ("uploaded", "queued", "processing", "completed", "error")
JOB_STATUSES = ("queued", "processing", "completed", "error")
SERVE_SIDES = ("unknown", "near", "far")


def allowed_values(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    videos: Mapped[list["Video"]] = relationship(back_populates="user")


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (CheckConstraint(allowed_values("status", VIDEO_STATUSES), name="ck_videos_status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # Владелец видео; пустой, пока в системе нет входа пользователей (это задание ИР 2)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    # Техническое поле: путь к файлу на диске (filename хранит исходное имя от пользователя)
    file_path: Mapped[str] = mapped_column(String(500))
    duration: Mapped[float]
    fps: Mapped[float]
    width: Mapped[int]
    height: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped[User | None] = relationship(back_populates="videos")
    jobs: Mapped[list["ProcessingJob"]] = relationship(
        back_populates="video", cascade="all, delete-orphan", order_by="ProcessingJob.id"
    )
    rallies: Mapped[list["Rally"]] = relationship(
        back_populates="video", cascade="all, delete-orphan", order_by="Rally.number"
    )


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        CheckConstraint(allowed_values("status", JOB_STATUSES), name="ck_processing_jobs_status"),
        CheckConstraint("progress BETWEEN 0 AND 100", name="ck_processing_jobs_progress"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    progress: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    # Технические поля: путь к JSON с покадровыми детекциями и текст ошибки
    detections_path: Mapped[str | None] = mapped_column(String(500))
    error_message: Mapped[str | None] = mapped_column(String(1000))

    video: Mapped[Video] = relationship(back_populates="jobs")


class Rally(Base):
    __tablename__ = "rallies"
    __table_args__ = (
        UniqueConstraint("video_id", "number", name="uq_rallies_video_number"),
        CheckConstraint(allowed_values("serve_side", SERVE_SIDES), name="ck_rallies_serve_side"),
        CheckConstraint("end_frame >= start_frame", name="ck_rallies_frames"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Отдельный индекс не нужен: поиск по video_id обслуживает уникальный индекс (video_id, number)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    number: Mapped[int]
    start_time: Mapped[float]
    end_time: Mapped[float]
    start_frame: Mapped[int]
    end_frame: Mapped[int]
    serve_side: Mapped[str] = mapped_column(String(10), default="unknown")

    video: Mapped[Video] = relationship(back_populates="rallies")
