from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.code_agent import CodeAgent
from app.agents.content_guard import audit_user_input, input_blocked_message
from app.agents.doc_agent import DocAgent
from app.agents.media_agent import MediaAgent
from app.agents.orchestrator import Orchestrator
from app.agents.planner_agent import PlannerAgent
from app.agents.profile_agent import ProfileAgent
from app.agents.quiz_agent import QuizAgent
from app.agents.reading_agent import ReadingAgent
from app.agents.router_agent import RouterAgent
from app.agents.tutor_agent import TutorAgent
from app.core.auth import get_current_user
from app.core.database import AsyncSessionLocal, get_db
from app.core.llm import LLMClientError
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatSessionResponse,
    MessageResponse,
    PinSessionRequest,
    RenameSessionRequest,
    ResourceResponse,
    SessionDetailResponse,
    SSEEvent,
    error_event,
)
from app.services.chat_service import ChatService
from app.services.learning_path_service import LearningPathService
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


def build_orchestrator(db_session: AsyncSession) -> Orchestrator:
    from app.wiki import get_wiki_service

    from app.core.llm import get_llm_client

    try:
        wiki_service = get_wiki_service(session=db_session)
    except RuntimeError:
        wiki_service = None

    llm_client = get_llm_client()

    return Orchestrator(
        router_agent=RouterAgent(llm_client=llm_client),
        profile_agent=ProfileAgent(llm_client=llm_client),
        planner_agent=PlannerAgent(llm_client=llm_client),
        doc_agent=DocAgent(wiki_service=wiki_service),
        quiz_agent=QuizAgent(wiki_service=wiki_service),
        code_agent=CodeAgent(wiki_service=wiki_service),
        media_agent=MediaAgent(wiki_service=wiki_service),
        reading_agent=ReadingAgent(wiki_service=wiki_service),
        tutor_agent=TutorAgent(wiki_service=wiki_service),
        profile_service=ProfileService(session=db_session),
        chat_service=ChatService(session=db_session),
        learning_service=LearningPathService(session=db_session),
    )


def encode_sse_event(event: SSEEvent) -> str:
    return f"data: {json.dumps(event.model_dump(exclude_none=True), ensure_ascii=False, separators=(',', ':'))}\n\n"


@router.post("/session")
async def create_chat_session(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, int]:
    chat_service = ChatService(session=db)
    session_id = await chat_service.create_session(user_id=user.id)
    return {"session_id": session_id}


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    user_id = user.id

    async def event_stream() -> AsyncGenerator[str, None]:
        async with AsyncSessionLocal() as db:
            chat_service = ChatService(session=db)
            session_id = request.session_id
            active_course_id = request.course_id
            if session_id is None:
                session_id = await chat_service.create_session(
                    user_id=user_id,
                    course_id=request.course_id,
                )
            elif not await chat_service.session_exists(session_id, user_id=user_id):
                yield encode_sse_event(
                    error_event(
                        message="会话不存在，请先创建会话后再发送消息",
                        session_id=session_id,
                    )
                )
                return
            elif request.course_id is not None:
                session = await chat_service.update_session_course(
                    session_id=session_id,
                    course_id=request.course_id,
                    user_id=user_id,
                )
                active_course_id = session.course_id if session else request.course_id
            else:
                session = await chat_service.get_session(session_id, user_id=user_id)
                active_course_id = session.course_id if session else None

            try:
                history = await chat_service.list_recent_messages(
                    session_id,
                    limit=10,
                )
            except Exception:
                history = []

            audited_message, audit_warnings, allowed = await audit_user_input(
                request.message,
                chat_sid=f"session-{session_id}",
                history=history,
            )
            if audit_warnings:
                for warning in audit_warnings:
                    logger.info("内容安全审核警告: %s", warning)
            if not allowed:
                yield encode_sse_event(
                    error_event(
                        message=input_blocked_message(),
                        session_id=session_id,
                    )
                )
                return

            try:
                await chat_service.save_message(
                    session_id=session_id,
                    role="user",
                    content=request.message,
                )
            except Exception:
                yield encode_sse_event(
                    error_event(
                        message="保存聊天消息失败，请稍后重试",
                        session_id=session_id,
                    )
                )
                return

            orchestrator = build_orchestrator(db)
            try:
                async for event in orchestrator.run(
                    session_id=session_id,
                    user_message=audited_message,
                    user_id=user_id,
                    history=history,
                    study_mode=request.study_mode,
                    course_id=active_course_id,
                ):
                    yield encode_sse_event(event)
            except LLMClientError as exc:
                yield encode_sse_event(
                    error_event(message=str(exc), session_id=session_id)
                )
            except Exception:
                logger.exception("聊天流式处理异常")
                yield encode_sse_event(
                    error_event(
                        message="聊天处理失败，请稍后重试",
                        session_id=session_id,
                    )
                )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ChatSessionResponse]:
    chat_service = ChatService(session=db)
    sessions = await chat_service.list_sessions(user_id=user.id)
    return [
        ChatSessionResponse(
            id=s.id,
            title=s.title,
            course_id=s.course_id,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
            is_pinned=s.is_pinned,
            pinned_at=s.pinned_at.isoformat() if s.pinned_at else None,
        )
        for s in sessions
    ]


@router.patch("/sessions/{session_id}/title", response_model=ChatSessionResponse)
async def rename_session(
    session_id: int,
    request: RenameSessionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatSessionResponse:
    chat_service = ChatService(session=db)
    session = await chat_service.update_session_title(
        session_id=session_id,
        title=request.title.strip(),
        user_id=user.id,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        course_id=session.course_id,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        is_pinned=session.is_pinned,
        pinned_at=session.pinned_at.isoformat() if session.pinned_at else None,
    )


@router.patch("/sessions/{session_id}/pin", response_model=ChatSessionResponse)
async def pin_session(
    session_id: int,
    request: PinSessionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatSessionResponse:
    chat_service = ChatService(session=db)
    session = await chat_service.set_session_pinned(
        session_id=session_id,
        is_pinned=request.is_pinned,
        user_id=user.id,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        course_id=session.course_id,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        is_pinned=session.is_pinned,
        pinned_at=session.pinned_at.isoformat() if session.pinned_at else None,
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, bool]:
    chat_service = ChatService(session=db)
    deleted = await chat_service.delete_session(session_id, user_id=user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True}


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionDetailResponse:
    chat_service = ChatService(session=db)
    session = await chat_service.get_session(session_id, user_id=user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = await chat_service.list_messages(session_id)
    resources = await chat_service.list_resources(session_id)

    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        course_id=session.course_id,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                message_type=m.message_type,
                turn_id=m.turn_id,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
        resources=[
            ResourceResponse(
                id=r.id,
                resource_type=r.resource_type,
                title=r.title,
                content=r.content,
                knowledge_point=r.knowledge_point,
                agent_name=r.agent_name,
                turn_id=r.turn_id,
                is_favorite=r.is_favorite,
                created_at=r.created_at.isoformat(),
            )
            for r in resources
        ],
    )
