from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.cache import get_cache_backend, make_cache_key
from app.core.config import get_settings
from app.models.user import User
from app.schemas.wiki import (
    CourseTemplateResponse,
    KnowledgeTreeNode,
    KnowledgeTreeResponse,
    PrerequisitesResponse,
    RelatedResponse,
    WikiSearchRequest,
    WikiSearchResponse,
    WikiSearchResultItem,
    WikiUploadResponse,
    WriteBackRequest,
    WriteBackResponse,
)
from app.wiki.ingestion import DocumentIngestionError, UnsupportedDocumentTypeError
from app.wiki import get_wiki_service

router = APIRouter(prefix="/api/wiki", tags=["wiki"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.get("/chapters")
async def list_chapters(
    course_id: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
) -> list[dict[str, str]]:
    """列出所有章节。"""
    wiki = get_wiki_service()
    chapters = wiki.list_chapters(course_id=course_id)
    return chapters


@router.get("/courses", response_model=list[CourseTemplateResponse])
async def list_courses(
    _user: User = Depends(get_current_user),
) -> list[CourseTemplateResponse]:
    """列出可用课程模板。"""
    wiki = get_wiki_service()
    return [CourseTemplateResponse(**course) for course in wiki.list_courses()]


@router.post("/search", response_model=WikiSearchResponse)
async def search_wiki(
    request: WikiSearchRequest,
    _user: User = Depends(get_current_user),
) -> WikiSearchResponse:
    """语义检索知识库。"""
    wiki = get_wiki_service()
    results = await wiki.search(
        query=request.query,
        top_k=request.top_k,
        chapter=request.chapter,
        course_id=request.course_id,
    )
    items = [
        WikiSearchResultItem(
            chunk_id=r.chunk_id,
            title=r.title,
            content=r.content,
            course_id=r.course_id,
            chapter=r.chapter,
            section=r.section,
            score=r.score,
        )
        for r in results
    ]
    return WikiSearchResponse(results=items, total=len(items))


@router.post("/upload", response_model=WikiUploadResponse)
async def upload_wiki_document(
    file: UploadFile = File(...),
    chapter: str | None = Form(default=None),
    section: str | None = Form(default=None),
    course_id: str | None = Form(default=None),
    tags: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> WikiUploadResponse:
    """上传课程资料并写入 Wiki 检索库。"""
    payload = await file.read()
    await file.close()
    if not payload:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="上传文件不能超过 10MB")

    wiki = get_wiki_service(session=db)
    try:
        result = await wiki.ingest_uploaded_document(
            filename=file.filename or "uploaded-document",
            content=payload,
            mime_type=file.content_type or "",
            chapter=chapter,
            section=section,
            course_id=course_id,
            tags=_parse_tags(tags),
        )
    except UnsupportedDocumentTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except DocumentIngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return WikiUploadResponse(
        success=True,
        filename=result.filename,
        title=result.title,
        course_id=result.course_id,
        content_type=result.content_type,
        chunk_count=result.chunk_count,
        chunk_ids=result.chunk_ids,
        char_count=result.char_count,
        chapter=result.chapter,
        section=result.section,
    )


@router.get("/tree/{chapter_id}", response_model=KnowledgeTreeResponse)
async def get_knowledge_tree(
    chapter_id: str,
    course_id: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
) -> KnowledgeTreeResponse:
    """获取章节知识树。"""
    wiki = get_wiki_service()
    tree = await _cached_graph_query(
        "wiki_graph_tree",
        (chapter_id, course_id),
        lambda: wiki.get_knowledge_tree(chapter_id, course_id=course_id),
    )
    concepts = [KnowledgeTreeNode(**node) for node in tree]
    return KnowledgeTreeResponse(
        course_id=course_id,
        chapter_id=chapter_id,
        concepts=concepts,
    )


@router.get("/prerequisites/{topic}", response_model=PrerequisitesResponse)
async def get_prerequisites(
    topic: str,
    course_id: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
) -> PrerequisitesResponse:
    """获取前置知识列表。"""
    wiki = get_wiki_service()
    prerequisites = await _cached_graph_query(
        "wiki_graph_prerequisites",
        (topic, course_id),
        lambda: wiki.get_prerequisites(topic, course_id=course_id),
    )
    return PrerequisitesResponse(topic=topic, prerequisites=prerequisites)


@router.get("/related/{topic}", response_model=RelatedResponse)
async def get_related(
    topic: str,
    course_id: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
) -> RelatedResponse:
    """获取关联知识。"""
    wiki = get_wiki_service()
    related = await _cached_graph_query(
        "wiki_graph_related",
        (topic, course_id),
        lambda: wiki.get_related(topic, course_id=course_id),
    )
    return RelatedResponse(topic=topic, related=related)


@router.post("/write-back", response_model=WriteBackResponse)
async def write_back(
    request: WriteBackRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WriteBackResponse:
    """Agent 生成内容回写知识库。"""
    wiki = get_wiki_service(session=db)
    chunk_id = await wiki.write_back(
        title=request.title,
        content=request.content,
        source_agent=request.source_agent,
        course_id=request.course_id,
        chapter=request.chapter,
        section=request.section,
        tags=request.tags,
    )
    return WriteBackResponse(success=chunk_id is not None, chunk_id=chunk_id)


def _parse_tags(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,，、\n]", value) if item.strip()]


async def _cached_graph_query(
    namespace: str,
    parts: tuple[Any, ...],
    loader: Callable[[], Any],
) -> Any:
    cache = get_cache_backend()
    cache_key = make_cache_key(namespace, *parts)
    try:
        cached = await cache.get(cache_key)
        if cached is not None:
            return json.loads(cached)
    except Exception:
        pass

    value = loader()
    try:
        await cache.set(
            cache_key,
            json.dumps(value, ensure_ascii=False),
            ttl_seconds=get_settings().cache_ttl_seconds,
        )
    except Exception:
        pass
    return value
