from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.code_agent import CodeAgent
from app.agents.content_guard import (
    audit_model_output,
    format_source_citations,
    guard_content,
)
from app.agents.doc_agent import DocAgent
from app.agents.media_agent import MediaAgent
from app.agents.quiz_agent import QuizAgent
from app.agents.reading_agent import ReadingAgent
from app.agents.resource_types import AgentResource
from app.api.chat import encode_sse_event
from app.core.speech import SpeechRecognitionClient, SpeechRecognitionError
from app.core.auth import get_current_user
from app.core.code_sandbox import CodeSandboxError, execute_python_code, extract_python_code
from app.core.database import get_db
from app.core.pptx_export import build_pptx
from app.core.storage import get_asset_storage
from app.core.video_export import build_animation_export_package
from app.core.xunfei_tts import (
    XunfeiTTSError,
    get_xunfei_tts_client,
    prepare_resource_tts_text,
)
from app.models.user import User
from app.schemas.chat import (
    CodeExecutionRequest,
    CodeExecutionResponse,
    FavoriteResourceRequest,
    ResourceAssetResponse,
    ResourceResponse,
)
from app.services.chat_service import ChatService
from app.services.profile_service import ProfileService
from app.wiki import get_wiki_service

router = APIRouter(prefix="/api/resources", tags=["resources"])
logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    document = "document"
    quiz = "quiz"
    code = "code"
    mindmap = "mindmap"
    ppt = "ppt"
    animation = "animation"
    reading = "reading"


@router.get("", response_model=list[ResourceResponse])
async def list_resources(
    resource_type: ResourceType | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ResourceResponse]:
    chat_service = ChatService(session=db)
    resources = await chat_service.list_all_resources(
        user_id=user.id, resource_type=resource_type.value if resource_type else None
    )
    return [
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
    ]


@router.post("/{resource_id}/speech")
async def synthesize_resource_speech(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    chat_service = ChatService(session=db)
    resource = await chat_service.get_resource(resource_id, user_id=user.id)
    if resource is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    tts_client = get_xunfei_tts_client()
    if tts_client is None:
        raise HTTPException(status_code=503, detail="讯飞 TTS 未启用")

    text = prepare_resource_tts_text(
        title=resource.title,
        content=resource.content,
        resource_type=resource.resource_type,
    )
    try:
        audio = await tts_client.synthesize(text)
    except XunfeiTTSError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'inline; filename="resource-{resource_id}.mp3"',
            "Cache-Control": "private, max-age=300",
        },
    )


@router.post("/{resource_id}/assets/speech", response_model=ResourceAssetResponse)
async def create_resource_speech_asset(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResourceAssetResponse:
    chat_service = ChatService(session=db)
    resource = await chat_service.get_resource(resource_id, user_id=user.id)
    if resource is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    tts_client = get_xunfei_tts_client()
    if tts_client is None:
        raise HTTPException(status_code=503, detail="讯飞 TTS 未启用")

    text = prepare_resource_tts_text(
        title=resource.title,
        content=resource.content,
        resource_type=resource.resource_type,
    )
    try:
        audio = await tts_client.synthesize(text)
    except XunfeiTTSError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    asset = get_asset_storage().save_bytes(
        data=audio,
        filename=f"resource-{resource_id}.mp3",
        media_type="audio/mpeg",
        namespace=f"resource-{resource_id}",
    )
    return _asset_response(asset)


@router.patch("/{resource_id}/favorite", response_model=ResourceResponse)
async def set_resource_favorite(
    resource_id: int,
    request: FavoriteResourceRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResourceResponse:
    chat_service = ChatService(session=db)
    resource = await chat_service.set_resource_favorite(
        resource_id=resource_id,
        user_id=user.id,
        is_favorite=request.is_favorite,
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    return ResourceResponse(
        id=resource.id,
        resource_type=resource.resource_type,
        title=resource.title,
        content=resource.content,
        knowledge_point=resource.knowledge_point,
        agent_name=resource.agent_name,
        turn_id=resource.turn_id,
        is_favorite=resource.is_favorite,
        created_at=resource.created_at.isoformat(),
    )


@router.post("/{resource_id}/regenerate", response_model=ResourceResponse)
async def regenerate_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResourceResponse:
    """只重生成单张资源卡，不重跑整轮对话和资源包。"""
    chat_service = ChatService(session=db)
    resource = await chat_service.get_resource(resource_id, user_id=user.id)
    if resource is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    try:
        generated = await _generate_replacement_resource(
            resource=resource,
            user=user,
            chat_service=chat_service,
            db=db,
        )
        content = await _finalize_regenerated_content(generated, resource.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    updated = await chat_service.update_resource(
        resource_id=resource.id,
        user_id=user.id,
        title=generated.title,
        content=content,
        knowledge_point=generated.knowledge_point,
        agent_name=generated.agent_name,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    return ResourceResponse(
        id=updated.id,
        resource_type=updated.resource_type,
        title=updated.title,
        content=updated.content,
        knowledge_point=updated.knowledge_point,
        agent_name=updated.agent_name,
        turn_id=updated.turn_id,
        is_favorite=updated.is_favorite,
        created_at=updated.created_at.isoformat(),
        confidence=generated.confidence,
        sources=generated.sources,
    )


@router.get("/{resource_id}/export")
async def export_resource(
    resource_id: int,
    format: Literal["markdown", "pptx"] = Query(default="markdown"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    chat_service = ChatService(session=db)
    resource = await chat_service.get_resource(resource_id, user_id=user.id)
    if resource is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    if format == "pptx":
        if resource.resource_type != "ppt":
            raise HTTPException(status_code=400, detail="只有教学演示资源可以导出 PPTX")

        pptx_bytes = build_pptx(title=resource.title, content=resource.content)
        return Response(
            content=pptx_bytes,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            ),
            headers={
                "Content-Disposition": (
                    f'attachment; filename="resource-{resource_id}.pptx"'
                ),
                "Cache-Control": "private, max-age=60",
            },
        )

    markdown = _build_resource_markdown(resource)

    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="resource-{resource_id}.md"',
            "Cache-Control": "private, max-age=60",
        },
    )


@router.post("/{resource_id}/assets/export", response_model=ResourceAssetResponse)
async def create_resource_export_asset(
    resource_id: int,
    format: Literal["markdown", "pptx"] = Query(default="markdown"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResourceAssetResponse:
    chat_service = ChatService(session=db)
    resource = await chat_service.get_resource(resource_id, user_id=user.id)
    if resource is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    if format == "pptx":
        if resource.resource_type != "ppt":
            raise HTTPException(status_code=400, detail="只有教学演示资源可以导出 PPTX")
        payload = build_pptx(title=resource.title, content=resource.content)
        filename = f"resource-{resource_id}.pptx"
        media_type = (
            "application/vnd.openxmlformats-officedocument."
            "presentationml.presentation"
        )
    else:
        payload = _build_resource_markdown(resource).encode("utf-8")
        filename = f"resource-{resource_id}.md"
        media_type = "text/markdown; charset=utf-8"

    asset = get_asset_storage().save_bytes(
        data=payload,
        filename=filename,
        media_type=media_type,
        namespace=f"resource-{resource_id}",
    )
    return _asset_response(asset)


@router.post("/{resource_id}/assets/animation", response_model=ResourceAssetResponse)
async def create_animation_export_asset(
    resource_id: int,
    include_audio: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResourceAssetResponse:
    chat_service = ChatService(session=db)
    resource = await chat_service.get_resource(resource_id, user_id=user.id)
    if resource is None:
        raise HTTPException(status_code=404, detail="资源不存在")
    if resource.resource_type != ResourceType.animation.value:
        raise HTTPException(status_code=400, detail="只有算法动画资源可以导出动画包")

    audio: bytes | None = None
    tts_client = get_xunfei_tts_client() if include_audio else None
    if tts_client is not None:
        text = prepare_resource_tts_text(
            title=resource.title,
            content=resource.content,
            resource_type=resource.resource_type,
        )
        try:
            audio = await tts_client.synthesize(text)
        except XunfeiTTSError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    payload = build_animation_export_package(
        title=resource.title,
        content=resource.content,
        audio=audio,
    )
    asset = get_asset_storage().save_bytes(
        data=payload,
        filename=f"resource-{resource_id}-animation.zip",
        media_type="application/zip",
        namespace=f"resource-{resource_id}",
    )
    return _asset_response(asset)


@router.post("/{resource_id}/execute", response_model=CodeExecutionResponse)
async def execute_resource_code(
    resource_id: int,
    request: CodeExecutionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CodeExecutionResponse:
    chat_service = ChatService(session=db)
    resource = await chat_service.get_resource(resource_id, user_id=user.id)
    if resource is None:
        raise HTTPException(status_code=404, detail="资源不存在")
    if resource.resource_type != "code":
        raise HTTPException(status_code=400, detail="只有代码实践资源可以执行")

    code_index = request.code_index if request is not None else 0
    try:
        code = extract_python_code(resource.content, code_index=code_index)
    except CodeSandboxError as exc:
        return CodeExecutionResponse(status="blocked", stderr=str(exc))

    result = await execute_python_code(code)
    return CodeExecutionResponse(
        status=result.status,  # type: ignore[arg-type]
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
    )


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResourceResponse:
    chat_service = ChatService(session=db)
    resource = await chat_service.get_resource(resource_id, user_id=user.id)
    if resource is None:
        raise HTTPException(status_code=404, detail="资源不存在")
    return ResourceResponse(
        id=resource.id,
        resource_type=resource.resource_type,
        title=resource.title,
        content=resource.content,
        knowledge_point=resource.knowledge_point,
        agent_name=resource.agent_name,
        turn_id=resource.turn_id,
        is_favorite=resource.is_favorite,
        created_at=resource.created_at.isoformat(),
    )


async def _generate_replacement_resource(
    *,
    resource: Any,
    user: User,
    chat_service: ChatService,
    db: AsyncSession,
) -> AgentResource:
    profile_service = ProfileService(session=db)
    profile = await profile_service.get_or_create_profile(
        session_id=resource.session_id,
        user_id=user.id,
    )
    profile_dict = profile.model_dump()
    topic = resource.knowledge_point or resource.title
    wiki_service = get_wiki_service(session=db)
    session_resources = await chat_service.list_resources(resource.session_id)
    chat_session = await chat_service.get_session(resource.session_id, user_id=user.id)
    course_id = chat_session.course_id if chat_session is not None else None
    document_content = _find_context_content(session_resources, "document", resource.id)
    quiz_content = _find_context_content(session_resources, "quiz", resource.id)

    if resource.resource_type == ResourceType.document.value:
        return await DocAgent(wiki_service=wiki_service).generate_document(
            topic, profile_dict, course_id=course_id
        )
    if resource.resource_type == ResourceType.quiz.value:
        return await QuizAgent(wiki_service=wiki_service).generate_quiz(
            topic,
            profile_dict,
            document_content=document_content,
            course_id=course_id,
        )
    if resource.resource_type == ResourceType.code.value:
        return await CodeAgent(wiki_service=wiki_service).generate_code(
            topic,
            profile_dict,
            document_content=document_content,
            quiz_content=quiz_content,
            course_id=course_id,
        )
    if resource.resource_type == ResourceType.mindmap.value:
        return await MediaAgent(wiki_service=wiki_service).generate_mindmap(
            topic,
            profile_dict,
            document_content=document_content,
            course_id=course_id,
        )
    if resource.resource_type == ResourceType.ppt.value:
        return await MediaAgent(wiki_service=wiki_service).generate_ppt_outline(
            topic,
            profile_dict,
            document_content=document_content,
            course_id=course_id,
        )
    if resource.resource_type == ResourceType.animation.value:
        return await MediaAgent(wiki_service=wiki_service).generate_animation_script(
            topic,
            profile_dict,
            document_content=document_content,
            course_id=course_id,
        )
    if resource.resource_type == ResourceType.reading.value:
        return await ReadingAgent(wiki_service=wiki_service).generate_reading(
            topic,
            profile_dict,
            document_content=document_content,
            course_id=course_id,
        )

    raise ValueError("该资源类型暂不支持重生成")


async def _finalize_regenerated_content(
    resource: AgentResource,
    session_id: int,
) -> str:
    content = resource.content
    audited, audit_warnings, audit_allowed = await audit_model_output(
        content,
        chat_sid=f"session-{session_id}:regenerate:{resource.resource_type}",
    )
    content = audited
    for warning in audit_warnings:
        logger.info("讯飞安全护栏警告 [%s]: %s", resource.title, warning)

    if audit_allowed and resource.resource_type != ResourceType.quiz.value:
        guarded, warnings = guard_content(
            content,
            wiki_context=resource.wiki_context,
            topic=resource.knowledge_point,
            confidence=resource.confidence or None,
        )
        content = guarded
        for warning in warnings:
            logger.info("内容防护警告 [%s]: %s", resource.title, warning)

        if resource.sources:
            content += format_source_citations(
                resource.sources,
                confidence=resource.confidence,
            )

    return content


def _find_context_content(
    resources: list[Any],
    resource_type: str,
    current_resource_id: int,
) -> str | None:
    for resource in resources:
        if resource.id == current_resource_id:
            continue
        if resource.resource_type == resource_type:
            return resource.content
    return None


@router.post("/ppt-images")
async def generate_ppt_images_endpoint(
    topic: str = Query(..., description="PPT 主题"),
    user=Depends(get_current_user),
) -> StreamingResponse:
    """直接生成 PPT 风格知识图片，不受编排器影响。"""
    from app.schemas.chat import (
        ResourceCardPayload,
        agent_status_event,
        done_event,
        error_event,
        resource_card_event,
    )
    from app.core.llm import get_llm_client

    media_agent = MediaAgent(llm_client=get_llm_client())

    async def event_stream():
        try:
            resource = await media_agent.generate_ppt_images(topic, {})
            payload = ResourceCardPayload(
                id=None,
                resource_type=resource.resource_type,
                title=resource.title,
                content=resource.content,
                knowledge_point=resource.knowledge_point,
                agent_name=resource.agent_name,
                confidence=resource.confidence,
                sources=resource.sources,
            )
            yield encode_sse_event(resource_card_event(resource=payload))
            yield encode_sse_event(done_event())
        except Exception as exc:
            logger.exception("PPT 图片生成失败")
            yield encode_sse_event(error_event(message=str(exc) or "PPT 图片生成失败"))

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/speech-recognize")
async def speech_recognize(
    request: Request,
    user=Depends(get_current_user),
) -> dict[str, str]:
    """语音识别 — 上传音频返回文字。"""
    try:
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="未收到音频数据")
    except Exception:
        raise HTTPException(status_code=400, detail="读取音频数据失败")

    client = SpeechRecognitionClient()
    try:
        text = await client.recognize(body, audio_format="wav")
        return {"text": text}
    except SpeechRecognitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def _build_resource_markdown(resource: Any) -> str:
    lines = [
        f"# {resource.title}",
        "",
        f"- 资源类型：{resource.resource_type}",
    ]
    if resource.knowledge_point:
        lines.append(f"- 知识点：{resource.knowledge_point}")
    if resource.agent_name:
        lines.append(f"- 生成 Agent：{resource.agent_name}")
    lines.extend(["", "---", "", resource.content])
    return "\n".join(lines)


def _asset_response(asset: Any) -> ResourceAssetResponse:
    return ResourceAssetResponse(
        url=asset.url,
        filename=asset.filename,
        media_type=asset.media_type,
        size_bytes=asset.size_bytes,
    )
