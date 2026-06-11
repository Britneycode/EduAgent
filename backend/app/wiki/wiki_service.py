from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wiki import WikiEntry
from app.wiki.courses import CourseTemplate
from app.wiki.graph import KnowledgeGraph
from app.wiki.ingestion import KnowledgeIngestion, UploadedDocumentIngestionResult
from app.wiki.rag_engine import RAGEngine, SearchResult, ContextWithSources
from app.wiki.vector_store import ChromaHttpVectorStore, VectorStore

logger = logging.getLogger(__name__)


class WikiService:
    """Wiki 知识中枢门面服务。

    统一对外暴露检索、知识图谱查询和内容回写接口。
    """

    def __init__(
        self,
        rag_engine: RAGEngine,
        knowledge_graph: KnowledgeGraph,
        vector_store: VectorStore | ChromaHttpVectorStore,
        session: AsyncSession | None = None,
        courses: list[CourseTemplate] | None = None,
        default_course_id: str | None = None,
    ) -> None:
        self._rag_engine = rag_engine
        self._knowledge_graph = knowledge_graph
        self._vector_store = vector_store
        self._session = session
        self._courses = courses or []
        self._default_course_id = default_course_id

    async def search(
        self,
        query: str,
        top_k: int = 5,
        chapter: str | None = None,
        course_id: str | None = None,
    ) -> list[SearchResult]:
        """语义检索知识片段。"""
        return await self._rag_engine.search(
            query=query,
            top_k=top_k,
            chapter=chapter,
            course_id=course_id,
        )

    async def build_context(
        self,
        query: str,
        top_k: int = 3,
        chapter: str | None = None,
        course_id: str | None = None,
    ) -> str:
        """检索并格式化为 prompt 上下文（Agent 主要使用此接口）。"""
        return await self._rag_engine.build_context(
            query=query,
            top_k=top_k,
            chapter=chapter,
            course_id=course_id,
        )

    async def build_context_with_sources(
        self,
        query: str,
        top_k: int = 3,
        chapter: str | None = None,
        course_id: str | None = None,
    ) -> ContextWithSources:
        """检索并返回带来源引用的上下文。"""
        return await self._rag_engine.build_context_with_sources(
            query=query,
            top_k=top_k,
            chapter=chapter,
            course_id=course_id,
        )

    def get_prerequisites(
        self,
        topic: str,
        course_id: str | None = None,
    ) -> list[str]:
        """获取某概念的全部前置知识（拓扑排序）。"""
        return self._knowledge_graph.get_all_prerequisites(
            topic,
            course_id=course_id,
        )

    def get_knowledge_tree(
        self,
        chapter_id: str,
        course_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取某章的知识树结构。"""
        concepts = self._knowledge_graph.get_chapter_concepts(
            chapter_id,
            course_id=course_id,
        )
        return [
            {
                "name": c.name,
                "course_id": c.course_id,
                "chapter": c.chapter,
                "section": c.section,
                "prerequisites": c.prerequisites,
                "description": c.description,
            }
            for c in concepts
        ]

    def get_related(
        self,
        topic: str,
        course_id: str | None = None,
    ) -> list[str]:
        """获取关联概念列表。"""
        return self._knowledge_graph.get_related(topic, course_id=course_id)

    def list_chapters(self, course_id: str | None = None) -> list[dict[str, str]]:
        """列出所有章节。"""
        return self._knowledge_graph.list_chapters(course_id=course_id)

    def list_courses(self) -> list[dict[str, Any]]:
        """列出可用课程模板。"""
        graph_courses = {
            str(course["id"]): course for course in self._knowledge_graph.list_courses()
        }
        items: list[dict[str, Any]] = []
        for course in self._courses:
            graph_course = graph_courses.get(course.id, {})
            items.append(
                {
                    "id": course.id,
                    "title": course.title,
                    "description": course.description,
                    "metadata_course_id": course.metadata_course_id,
                    "chapter_count": course.chapter_count
                    or int(graph_course.get("chapter_count") or 0),
                    "concept_count": int(graph_course.get("concept_count") or 0),
                    "estimated_hours": course.estimated_hours,
                    "is_default": course.id == self._default_course_id
                    or course.is_default,
                }
            )

        for course_id, graph_course in graph_courses.items():
            if any(item["id"] == course_id for item in items):
                continue
            items.append(
                {
                    "id": course_id,
                    "title": graph_course.get("title") or course_id,
                    "description": graph_course.get("description") or "",
                    "metadata_course_id": "",
                    "chapter_count": int(graph_course.get("chapter_count") or 0),
                    "concept_count": int(graph_course.get("concept_count") or 0),
                    "estimated_hours": 0,
                    "is_default": course_id == self._default_course_id,
                }
            )
        return items

    async def write_back(
        self,
        title: str,
        content: str,
        source_agent: str,
        chapter: str | None = None,
        section: str | None = None,
        tags: list[str] | None = None,
        course_id: str | None = None,
    ) -> str | None:
        """Agent 生成内容回写到知识库（双写：向量库 + 数据库）。

        返回 chunk_id，失败则返回 None。
        """
        chunk_id = f"agent_{source_agent}_{title}"

        try:
            await asyncio.to_thread(
                self._vector_store.add,
                chunk_ids=[chunk_id],
                documents=[f"{title}\n\n{content}"],
                metadatas=[
                    {
                        "chapter": chapter or "",
                        "section": section or "",
                        "course_id": course_id or "",
                        "title": title,
                        "source_agent": source_agent,
                    }
                ],
            )
        except Exception:
            logger.exception("回写向量存储失败: %s", title)
            return None

        await self._rag_engine.clear_cache()

        if self._session is not None:
            try:
                entry = WikiEntry(
                    course_id=course_id,
                    chapter=chapter,
                    section=section,
                    title=title,
                    content=content,
                    content_type="agent_generated",
                    source_agent=source_agent,
                    chunk_id=chunk_id,
                    tags=tags or [],
                )
                self._session.add(entry)
                await self._session.commit()
            except Exception:
                logger.exception("回写数据库失败: %s", title)

        return chunk_id

    async def ingest_uploaded_document(
        self,
        *,
        filename: str,
        content: bytes,
        mime_type: str = "",
        chapter: str | None = None,
        section: str | None = None,
        tags: list[str] | None = None,
        course_id: str | None = None,
    ) -> UploadedDocumentIngestionResult:
        """将用户上传的课程资料写入 Wiki 和向量库。"""
        ingestion = KnowledgeIngestion(
            vector_store=self._vector_store,
            session=self._session,
        )
        result = await ingestion.ingest_uploaded_document(
            filename=filename,
            content=content,
            mime_type=mime_type,
            chapter=chapter,
            section=section,
            tags=tags,
            course_id=course_id,
        )
        await self._rag_engine.clear_cache()
        return result
