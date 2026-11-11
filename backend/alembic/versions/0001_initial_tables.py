"""initial tables

Revision ID: 0001
Revises:
Create Date: 2026-11-09 21:35:21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("duration", sa.Double(), nullable=False),
        sa.Column("fps", sa.Double(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint(
            "status IN ('uploaded', 'queued', 'processing', 'completed', 'error')", name="ck_videos_status"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_videos_user_id", "videos", ["user_id"])

    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("detections_path", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'error')", name="ck_processing_jobs_status"
        ),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name="ck_processing_jobs_progress"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_processing_jobs_video_id", "processing_jobs", ["video_id"])

    op.create_table(
        "rallies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Double(), nullable=False),
        sa.Column("end_time", sa.Double(), nullable=False),
        sa.Column("start_frame", sa.Integer(), nullable=False),
        sa.Column("end_frame", sa.Integer(), nullable=False),
        sa.Column("serve_side", sa.String(length=10), nullable=False),
        sa.CheckConstraint("serve_side IN ('unknown', 'near', 'far')", name="ck_rallies_serve_side"),
        sa.CheckConstraint("end_frame >= start_frame", name="ck_rallies_frames"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "number", name="uq_rallies_video_number"),
    )


def downgrade() -> None:
    op.drop_table("rallies")
    op.drop_index("ix_processing_jobs_video_id", table_name="processing_jobs")
    op.drop_table("processing_jobs")
    op.drop_index("ix_videos_user_id", table_name="videos")
    op.drop_table("videos")
    op.drop_table("users")
