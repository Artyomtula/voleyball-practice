from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    duration: float
    fps: float
    width: int
    height: int
    status: str
    created_at: datetime


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    status: str
    progress: int
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None


class RallyOut(BaseModel):
    number: int
    start: float
    end: float
    start_frame: int
    end_frame: int
    serve_side: str


class RalliesOut(BaseModel):
    video_id: int
    rallies: list[RallyOut]
