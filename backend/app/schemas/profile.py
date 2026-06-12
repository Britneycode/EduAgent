from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProfileResponse(BaseModel):
    """稳定的学生画像响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int = 1
    session_id: int | None = None
    major: str | None = None
    grade: str | None = None
    knowledge_base: dict[str, Any] = Field(default_factory=dict)
    cognitive_style: str | None = None
    learning_goal: str | None = None
    weak_points: list[str] = Field(default_factory=list)
    learning_pace: str | None = None
    interest_areas: list[str] = Field(default_factory=list)
    coding_level: str | None = None
    weekly_hours: int | None = None


class ProfileUpdateRequest(BaseModel):
    """用户主动编辑画像的请求模型。"""

    major: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=50)
    knowledge_base: dict[str, Any] | None = None
    cognitive_style: str | None = Field(default=None, max_length=100)
    learning_goal: str | None = Field(default=None, max_length=255)
    weak_points: list[str] | None = None
    learning_pace: str | None = Field(default=None, max_length=100)
    interest_areas: list[str] | None = None
    coding_level: str | None = Field(default=None, max_length=100)
    weekly_hours: int | None = Field(default=None, ge=0, le=168)


class AgentProfileUpdateConfirmRequest(BaseModel):
    """学生确认 Agent 候选画像变更后提交的请求。"""

    session_id: int | None = None
    update: ProfileUpdateRequest


class ProfileHistoryItem(BaseModel):
    """单条画像历史快照。"""

    id: int
    user_id: int
    session_id: int | None = None
    source: str
    changed_fields: list[str] = Field(default_factory=list)
    profile_data: dict[str, Any] = Field(default_factory=dict)
    created_at: str
