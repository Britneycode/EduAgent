from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="密码至少 6 位"
        )

    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在"
        )

    user = User(
        username=request.username,
        hashed_password=hash_password(request.password),
        display_name=request.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user_id=user.id, hashed_password=user.hashed_password)
    return AuthResponse(access_token=token, user_id=user.id)


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalars().first()
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )

    token = create_access_token(user_id=user.id, hashed_password=user.hashed_password)
    return AuthResponse(access_token=token, user_id=user.id)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    user: User = Depends(get_current_user),
) -> AuthResponse:
    token = create_access_token(user_id=user.id, hashed_password=user.hashed_password)
    return AuthResponse(access_token=token, user_id=user.id)


@router.post("/password", response_model=AuthResponse)
async def change_password(
    request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AuthResponse:
    if not verify_password(request.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误",
        )
    if verify_password(request.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与当前密码相同",
        )

    user.hashed_password = hash_password(request.new_password)
    db.add(user)
    await db.commit()

    token = create_access_token(user_id=user.id, hashed_password=user.hashed_password)
    return AuthResponse(access_token=token, user_id=user.id)
