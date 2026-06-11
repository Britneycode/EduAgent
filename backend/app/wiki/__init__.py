"""LLM Wiki 知识中枢 — 全局初始化与工厂函数。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache_backend
from app.core.config import get_settings
from app.wiki.courses import (
    CourseTemplate,
    discover_course_templates,
)
from app.wiki.embeddings import get_embedding_client
from app.wiki.graph import KnowledgeGraph
from app.wiki.ingestion import KnowledgeIngestion
from app.wiki.rag_engine import RAGEngine
from app.wiki.vector_store import (
    ChromaHttpVectorStore,
    VectorStore,
    VectorStoreBackendName,
    create_vector_store,
)
from app.wiki.wiki_service import WikiService

logger = logging.getLogger(__name__)

_vector_store: VectorStore | ChromaHttpVectorStore | None = None
_vector_store_backend: VectorStoreBackendName | None = None
_knowledge_graph: KnowledgeGraph | None = None
_rag_engine: RAGEngine | None = None
_course_templates: list[CourseTemplate] = []
_default_course_id: str | None = None


async def init_wiki(session: AsyncSession | None = None) -> None:
    """初始化 Wiki 知识中枢（应用启动时调用）。

    1. 初始化 Embedding 客户端
    2. 初始化 Chroma 向量存储
    3. 加载知识图谱
    4. 初始化 RAG 引擎
    5. 若向量库为空且开启自动导入，执行知识导入
    """
    global _vector_store, _vector_store_backend, _knowledge_graph, _rag_engine
    global _course_templates, _default_course_id

    settings = get_settings()

    # 1. Embedding 客户端
    embedding_client = get_embedding_client(dev_mode=settings.wiki_embedding_dev_mode)

    # 2. 向量存储
    chroma_dir = Path(settings.wiki_chroma_dir)
    _vector_store, _vector_store_backend = create_vector_store(
        embedding_client=embedding_client,
        backend=settings.wiki_vector_backend,
        persist_directory=chroma_dir,
        chroma_host=settings.wiki_chroma_host,
        chroma_port=settings.wiki_chroma_port,
        chroma_ssl=settings.wiki_chroma_ssl,
        chroma_collection=settings.wiki_chroma_collection,
    )
    logger.info(
        "Wiki 向量存储已初始化，后端: %s，路径: %s",
        _vector_store_backend,
        chroma_dir,
    )

    # 3. 知识图谱
    knowledge_dir = Path(settings.wiki_knowledge_dir)
    _course_templates = discover_course_templates(knowledge_dir)
    _default_course_id = _course_templates[0].id if _course_templates else None
    _knowledge_graph = KnowledgeGraph()

    for index, course in enumerate(_course_templates):
        graph_file = course.path / "knowledge_graph.json"
        metadata_file = course.path / "metadata.json"
        if graph_file.exists():
            _knowledge_graph.load_from_file(
                graph_file,
                course_id=course.id,
                course_title=course.title,
                clear=index == 0,
            )
        else:
            logger.warning("知识图谱文件不存在: %s", graph_file)
            if index == 0:
                _knowledge_graph.load_from_dict(
                    {},
                    course_id=course.id,
                    course_title=course.title,
                )
        if metadata_file.exists():
            with open(metadata_file, encoding="utf-8") as f:
                _knowledge_graph.load_chapter_metadata(
                    json.load(f),
                    course_id=course.id,
                )
    if not _course_templates:
        logger.warning("未发现课程知识库目录: %s", knowledge_dir)

    # 4. RAG 引擎
    _rag_engine = RAGEngine(
        vector_store=_vector_store,
        cache_backend=get_cache_backend(),
        cache_ttl_seconds=settings.cache_ttl_seconds,
    )

    # 5. 自动导入
    if settings.wiki_auto_ingest and _course_templates:
        ingestion = KnowledgeIngestion(
            vector_store=_vector_store,
            session=session,
        )
        total_count = 0
        for course in _course_templates:
            if _course_has_vectors(course.id):
                logger.info("课程 %s 已存在向量数据，跳过自动导入", course.id)
                continue
            count = await ingestion.ingest_course(course.path, course_id=course.id)
            total_count += count
            logger.info(
                "课程 %s 自动导入完成，共 %d 个知识块",
                course.id,
                count,
            )
        logger.info("课程知识库自动导入完成，共 %d 个知识块", total_count)

    logger.info(
        "Wiki 知识中枢初始化完成（向量库: %d 条，知识图谱: %d 个概念）",
        _vector_store.count(),
        len(_knowledge_graph.list_all_concepts()),
    )


def get_vector_store_status() -> dict[str, object | None]:
    """返回 Wiki 向量存储运行状态，供健康检查展示。"""
    return {
        "backend": _vector_store_backend,
        "count": _vector_store.count() if _vector_store is not None else None,
        "default_course_id": _default_course_id,
        "courses": [course.id for course in _course_templates],
    }


def get_wiki_service(session: AsyncSession | None = None) -> WikiService:
    """获取 WikiService 实例。"""
    if _vector_store is None or _knowledge_graph is None or _rag_engine is None:
        raise RuntimeError("Wiki 知识中枢尚未初始化，请先调用 init_wiki()")

    return WikiService(
        rag_engine=_rag_engine,
        knowledge_graph=_knowledge_graph,
        vector_store=_vector_store,
        session=session,
        courses=_course_templates,
        default_course_id=_default_course_id,
    )


def get_default_course_id() -> str | None:
    return _default_course_id


def _course_has_vectors(course_id: str) -> bool:
    if _vector_store is None:
        return False
    try:
        return bool(
            _vector_store.search(
                query=course_id,
                top_k=1,
                where={"course_id": course_id},
            )
        )
    except Exception:
        logger.warning("检查课程向量数据失败，将尝试重新导入: %s", course_id)
        return False
