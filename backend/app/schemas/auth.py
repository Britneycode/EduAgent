from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., max_length=128, description="密码")
    display_name: str | None = Field(
        default=None, max_length=100, description="显示名称"
    )


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., max_length=128, description="当前密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
