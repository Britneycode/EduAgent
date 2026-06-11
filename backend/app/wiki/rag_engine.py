from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.cache import CacheBackend, make_cache_key
from app.wiki.vector_store import (
    ChromaHttpVectorStore,
    VectorSearchResult,
    VectorStore,
    tokenize_for_lexical,
)


@dataclass(slots=True)
class SearchResult:
    """RAG 检索结果。"""

    chunk_id: str
    title: str
    content: str
    course_id: str = ""
    chapter: str = ""
    section: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceReference:
    """来源引用信息，用于防幻觉溯源。"""

    chapter: str
    section: str
    title: str
    score: float
    course_id: str = ""
    chunk_id: str = ""
    snippet: str = ""
    source_name: str = ""


@dataclass(slots=True)
class ContextWithSources:
    """带来源引用的上下文。"""

    context: str
    sources: list[SourceReference]
    confidence: float


@dataclass(slots=True)
class _HybridCandidate:
    chunk_id: str
    content: str
    metadata: dict[str, Any]
    vector_score: float = 0.0
    lexical_score: float = 0.0
    lexical_raw_score: float = 0.0


class RAGEngine:
    """RAG 检索引擎。

    使用向量检索 + BM25 词法检索的混合召回，并通过轻量规则 Rerank 排序。
    """

    _CACHE_NAMESPACE = "rag:search"

    def __init__(
        self,
        vector_store: VectorStore | ChromaHttpVectorStore,
        cache_backend: CacheBackend | None = None,
        cache_ttl_seconds: int = 1800,
    ) -> None:
        self._vector_store = vector_store
        self._cache = cache_backend
        self._cache_ttl_seconds = cache_ttl_seconds

    async def search(
        self,
        query: str,
        top_k: int = 5,
        chapter: str | None = None,
        course_id: str | None = None,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """混合检索，返回排序后的结果列表。"""
        cache_key = make_cache_key(
            self._CACHE_NAMESPACE, query, top_k, chapter, course_id, min_score
        )
        cached_results = await self._get_cached_search_results(cache_key)
        if cached_results is not None:
            return cached_results

        where: dict[str, Any] = {}
        if chapter:
            where["chapter"] = chapter
        if course_id:
            where["course_id"] = course_id
        normalized_where = where or None
        candidate_k = max(top_k * 4, 8)
        vector_task = asyncio.to_thread(
            self._vector_store.search,
            query=query,
            top_k=candidate_k,
            where=normalized_where,
        )
        lexical_task = asyncio.to_thread(
            self._vector_store.lexical_search,
            query=query,
            top_k=candidate_k,
            where=normalized_where,
        )
        vector_results, lexical_results = await asyncio.gather(
            vector_task, lexical_task
        )

        candidates: dict[str, _HybridCandidate] = {}
        for item in vector_results:
            candidate = self._get_or_create_candidate(candidates, item)
            candidate.vector_score = max(0.0, 1.0 - item.distance)

        for item in lexical_results:
            candidate = self._get_or_create_candidate(candidates, item)
            candidate.lexical_score = float(item.metadata.get("lexical_score", 0.0))
            candidate.lexical_raw_score = float(
                item.metadata.get("lexical_raw_score", 0.0)
            )

        reranked = []
        for candidate in candidates.values():
            score, overlap_score, exact_score = self._rerank_score(query, candidate)
            if score < min_score:
                continue

            metadata = dict(candidate.metadata)
            metadata["retrieval"] = {
                "vector_score": candidate.vector_score,
                "lexical_score": candidate.lexical_score,
                "lexical_raw_score": candidate.lexical_raw_score,
                "overlap_score": overlap_score,
                "exact_score": exact_score,
                "rerank_score": score,
            }
            reranked.append(
                SearchResult(
                    chunk_id=candidate.chunk_id,
                    title=candidate.metadata.get("title", ""),
                    content=candidate.content,
                    course_id=candidate.metadata.get("course_id", ""),
                    chapter=candidate.metadata.get("chapter", ""),
                    section=candidate.metadata.get("section", ""),
                    score=score,
                    metadata=metadata,
                )
            )

        reranked.sort(key=lambda item: item.score, reverse=True)
        final_results = reranked[:top_k]
        await self._set_cached_search_results(cache_key, final_results)
        return final_results

    def _get_or_create_candidate(
        self,
        candidates: dict[str, _HybridCandidate],
        result: VectorSearchResult,
    ) -> _HybridCandidate:
        candidate = candidates.get(result.chunk_id)
        if candidate is None:
            candidate = _HybridCandidate(
                chunk_id=result.chunk_id,
                content=result.content,
                metadata=dict(result.metadata),
            )
            candidates[result.chunk_id] = candidate
        else:
            candidate.metadata.update(result.metadata)
        return candidate

    def _rerank_score(
        self, query: str, candidate: _HybridCandidate
    ) -> tuple[float, float, float]:
        query_tokens = set(tokenize_for_lexical(query))
        candidate_text = (
            f"{candidate.metadata.get('title', '')}\n"
            f"{candidate.metadata.get('chapter', '')}\n"
            f"{candidate.metadata.get('section', '')}\n"
            f"{candidate.content}"
        )
        candidate_tokens = set(tokenize_for_lexical(candidate_text))
        overlap_score = (
            len(query_tokens & candidate_tokens) / len(query_tokens)
            if query_tokens
            else 0.0
        )

        normalized_query = query.strip().lower()
        exact_score = (
            1.0
            if normalized_query and normalized_query in candidate_text.lower()
            else 0.0
        )
        score = (
            candidate.vector_score * 0.5
            + candidate.lexical_score * 0.35
            + overlap_score * 0.1
            + exact_score * 0.05
        )
        return min(1.0, score), overlap_score, exact_score

    async def clear_cache(self) -> None:
        if self._cache is not None:
            await self._cache.clear_namespace(self._CACHE_NAMESPACE)

    async def _get_cached_search_results(
        self, cache_key: str
    ) -> list[SearchResult] | None:
        if self._cache is None:
            return None

        raw = await self._cache.get(cache_key)
        if not raw:
            return None

        try:
            payload = json.loads(raw)
            return [SearchResult(**item) for item in payload]
        except (TypeError, json.JSONDecodeError):
            return None

    async def _set_cached_search_results(
        self, cache_key: str, results: list[SearchResult]
    ) -> None:
        if self._cache is None:
            return

        payload = [
            {
                "chunk_id": result.chunk_id,
                "title": result.title,
                "content": result.content,
                "course_id": result.course_id,
                "chapter": result.chapter,
                "section": result.section,
                "score": result.score,
                "metadata": result.metadata,
            }
            for result in results
        ]
        await self._cache.set(
            cache_key,
            json.dumps(payload, ensure_ascii=False),
            ttl_seconds=self._cache_ttl_seconds,
        )

    async def build_context(
        self,
        query: str,
        top_k: int = 3,
        chapter: str | None = None,
        course_id: str | None = None,
    ) -> str:
        """检索相关知识并格式化为可注入 prompt 的上下文字符串。

        这是 Agent 最常调用的接口。
        """
        result = await self.build_context_with_sources(
            query=query,
            top_k=top_k,
            chapter=chapter,
            course_id=course_id,
        )
        return result.context

    async def build_context_with_sources(
        self,
        query: str,
        top_k: int = 3,
        chapter: str | None = None,
        course_id: str | None = None,
    ) -> ContextWithSources:
        """检索相关知识并返回带来源引用的上下文。"""
        results = await self.search(
            query=query,
            top_k=top_k,
            chapter=chapter,
            course_id=course_id,
        )
        if not results:
            return ContextWithSources(context="", sources=[], confidence=0.0)

        sources: list[SourceReference] = []
        parts = ["以下是与问题相关的参考知识：\n"]
        for i, r in enumerate(results, 1):
            chapter_label = r.chapter or "未知章节"
            section_label = r.section or ""
            source_tag = f"[来源：{chapter_label}"
            if section_label:
                source_tag += f" > {section_label}"
            source_tag += f" | 相关度：{r.score:.0%}]"

            parts.append(f"【参考 {i}】{r.title} {source_tag}")
            parts.append(r.content)
            parts.append("")

            sources.append(
                SourceReference(
                    chapter=r.chapter,
                    section=r.section,
                    title=r.title,
                    score=r.score,
                    course_id=r.course_id,
                    chunk_id=r.chunk_id,
                    snippet=_build_source_snippet(r.content),
                    source_name=str(r.metadata.get("source_name", "")),
                )
            )

        avg_score = sum(s.score for s in sources) / len(sources) if sources else 0.0
        confidence = min(1.0, avg_score)

        context = "\n".join(parts).strip()
        cite_hint = "\n\n请在回答中注明参考来源，确保回答与以上知识库内容一致。"
        context += cite_hint

        return ContextWithSources(
            context=context, sources=sources, confidence=confidence
        )


def _build_source_snippet(content: str, max_chars: int = 160) -> str:
    """Return a compact source excerpt suitable for UI citation panels."""
    normalized = re.sub(r"\s+", " ", content).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."
