from __future__ import annotations

from datetime import timezone, datetime

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StudentProfile(Base):
    """学生画像模型。

    画像绑定 user_id，跨 session 累积更新。
    session_id 仅记录最后更新来源，便于调试。
    """

    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True
    )
    session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    major: Mapped[str | None] = mapped_column(String(100), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    knowledge_base: Mapped[dict[str, str]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    cognitive_style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    learning_goal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    weak_points: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    learning_pace: Mapped[str | None] = mapped_column(String(100), nullable=True)
    interest_areas: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    coding_level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    weekly_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ProfileSnapshot(Base):
    """学生画像历史快照。"""

    __tablename__ = "profile_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_fields: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    profile_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
