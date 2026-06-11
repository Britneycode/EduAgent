from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: int | None = Field(default=None, description="会话 ID，可为空")
    course_id: str | None = Field(default=None, description="课程 ID，可为空")
    message: str = Field(..., description="用户输入")
    study_mode: bool = Field(default=False, description="是否启用分步辅导模式")


class ChatSessionResponse(BaseModel):
    id: int
    title: str
    course_id: str | None = None
    created_at: str
    updated_at: str
    is_pinned: bool = False
    pinned_at: str | None = None


class RenameSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="会话标题")


class PinSessionRequest(BaseModel):
    is_pinned: bool = Field(..., description="是否置顶")


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    message_type: str = "text"
    turn_id: str | None = None
    created_at: str


class ResourceResponse(BaseModel):
    id: int
    resource_type: str
    title: str
    content: str
    knowledge_point: str | None = None
    agent_name: str | None = None
    turn_id: str | None = None
    is_favorite: bool = False
    created_at: str
    confidence: float | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)


class ResourceAssetResponse(BaseModel):
    url: str
    filename: str
    media_type: str
    size_bytes: int


class FavoriteResourceRequest(BaseModel):
    is_favorite: bool = Field(..., description="是否收藏资源")


class CodeExecutionRequest(BaseModel):
    code_index: int = Field(default=0, ge=0, le=20, description="要执行的 Python 代码块序号")


class CodeExecutionResponse(BaseModel):
    status: Literal["success", "error", "timeout", "blocked"]
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: int = 0


class SessionDetailResponse(BaseModel):
    id: int
    title: str
    course_id: str | None = None
    created_at: str
    updated_at: str
    messages: list[MessageResponse] = Field(default_factory=list)
    resources: list[ResourceResponse] = Field(default_factory=list)


class ResourceCardPayload(BaseModel):
    id: int | None = Field(default=None, description="资源 ID（落库后可填）")
    resource_type: Literal[
        "document", "quiz", "code", "mindmap", "ppt", "ppt_images", "animation", "reading"
    ]
    title: str
    content: str
    knowledge_point: str | None = None
    agent_name: str | None = None
    turn_id: str | None = None
    confidence: float | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)


class SSEEvent(BaseModel):
    type: Literal[
        "agent_status",
        "profile_updated",
        "token",
        "resource_card",
        "wiki_fallback",
        "done",
        "error",
    ]
    session_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


def agent_status_event(
    *,
    agent: str,
    status: str,
    message: str,
    session_id: int | None = None,
) -> SSEEvent:
    return SSEEvent(
        type="agent_status",
        session_id=session_id,
        payload={"agent": agent, "status": status, "message": message},
    )


def profile_updated_event(*, session_id: int | None = None) -> SSEEvent:
    return SSEEvent(type="profile_updated", session_id=session_id, payload={})


def token_event(*, token: str, session_id: int | None = None) -> SSEEvent:
    return SSEEvent(type="token", session_id=session_id, payload={"token": token})


def resource_card_event(
    *,
    resource: ResourceCardPayload,
    session_id: int | None = None,
) -> SSEEvent:
    return SSEEvent(
        type="resource_card",
        session_id=session_id,
        payload=resource.model_dump(),
    )


def done_event(*, session_id: int | None = None) -> SSEEvent:
    return SSEEvent(type="done", session_id=session_id, payload={})


def error_event(*, message: str, session_id: int | None = None) -> SSEEvent:
    return SSEEvent(type="error", session_id=session_id, payload={"message": message})


def wiki_fallback_event(*, session_id: int | None = None) -> SSEEvent:
    return SSEEvent(
        type="wiki_fallback",
        session_id=session_id,
        payload={"message": "当前知识库未命中相关内容，生成结果未附带知识引用"},
    )
