from __future__ import annotations

from datetime import timezone, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SessionMaterial(Base):
    """会话学习材料模型。

    学生上传到某个聊天会话的资料（md/txt/pdf/pptx 等）。材料按会话隔离，
    向量块写入 `course_id="session:{session_id}"` + `scope="session"` 命名空间，
    知识库未命中时作为兜底检索源。原始文件经资产存储落盘，stored_key 指向文件。
    """

    __tablename__ = "session_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(50), default="text", nullable=False
    )
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    chapter: Mapped[str | None] = mapped_column(String(100), nullable=True)
    section: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<SessionMaterial id={self.id} session_id={self.session_id} "
            f"filename={self.filename!r} chunks={self.chunk_count}>"
        )
