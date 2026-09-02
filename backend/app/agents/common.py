from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol


class WikiSourceLike(Protocol):
    chapter: str
    section: str
    title: str
    score: float
    chunk_id: str
    snippet: str
    source_name: str


class WikiContextLike(Protocol):
    context: str
    confidence: float
    sources: list[WikiSourceLike]


class WikiServiceLike(Protocol):
    async def build_context_with_sources(
        self,
        *,
        query: str,
        top_k: int,
        course_id: str | None = None,
        session_id: int | None = None,
    ) -> WikiContextLike: ...

    async def build_context(
        self,
        *,
        query: str,
        top_k: int,
        course_id: str | None = None,
        session_id: int | None = None,
    ) -> str: ...


def parse_json_object(raw: str) -> dict[str, Any]:
    """Extract the first JSON object from common LLM markdown wrappers."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and start <= end:
        cleaned = cleaned[start : end + 1]

    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON 输出不是对象")
    return parsed


async def build_wiki_context_with_sources(
    wiki_service: WikiServiceLike | None,
    *,
    query: str,
    course_id: str | None = None,
    session_id: int | None = None,
    top_k: int = 3,
    logger: logging.Logger | None = None,
) -> tuple[str, bool, float, list[dict[str, Any]]]:
    if wiki_service is None:
        return "", True, 0.0, []
    try:
        ctx_with_sources = await wiki_service.build_context_with_sources(
            query=query,
            top_k=top_k,
            course_id=course_id,
            session_id=session_id,
        )
        if not ctx_with_sources.context.strip():
            return "", True, 0.0, []
        sources = [
            {
                "chapter": s.chapter,
                "section": s.section,
                "title": s.title,
                "score": s.score,
                "chunk_id": s.chunk_id,
                "snippet": s.snippet,
                "source_name": s.source_name,
            }
            for s in ctx_with_sources.sources
        ]
        return ctx_with_sources.context, False, ctx_with_sources.confidence, sources
    except Exception:
        if logger is not None:
            logger.warning("Wiki 检索失败，将不使用知识库上下文", exc_info=True)
        return "", True, 0.0, []


async def build_plain_wiki_context(
    wiki_service: WikiServiceLike | None,
    *,
    query: str,
    course_id: str | None = None,
    session_id: int | None = None,
    top_k: int = 3,
    logger: logging.Logger | None = None,
) -> str:
    if wiki_service is None:
        return ""
    try:
        context = await wiki_service.build_context(
            query=query,
            top_k=top_k,
            course_id=course_id,
            session_id=session_id,
        )
        return context.strip()
    except Exception:
        if logger is not None:
            logger.warning("Wiki 检索失败", exc_info=True)
        return ""


@dataclass
class AnchoredContext:
    """Agent 生成可用的锚定上下文：知识库 / 会话材料 / 均未覆盖。"""

    context: str
    kind: str  # "knowledge" | "material" | "none"
    confidence: float
    sources: list[dict[str, Any]]
    material_titles: list[str]


# 锚定置信度门槛：知识库与材料检索低于该值均视为「覆盖不足」，不作为锚定上下文。
MIN_ANCHOR_CONFIDENCE = 0.3


async def build_anchored_context(
    wiki_service: WikiServiceLike | None,
    *,
    query: str,
    course_id: str | None = None,
    session_id: int | None = None,
    top_k: int = 3,
    logger: logging.Logger | None = None,
) -> AnchoredContext:
    """按「知识库 → 会话材料 → 无覆盖」顺序构建锚定上下文。

    这是防幻觉兜底的统一入口：
    1. 先在课程知识库检索；置信度达标且命中则使用知识库（kind="knowledge"）。
    2. 知识库未命中或置信度不足、且会话绑定了学习材料时，切到该会话的材料检索
       （kind="material"），材料同样需达到锚定置信度门槛。
    3. 两者均未命中或置信度不足时返回空上下文（kind="none"），由 Agent 如实说明，不编造。
    """
    if wiki_service is None:
        return AnchoredContext(
            context="", kind="none", confidence=0.0, sources=[], material_titles=[]
        )

    kb_context, _, kb_confidence, kb_sources = await build_wiki_context_with_sources(
        wiki_service,
        query=query,
        course_id=course_id,
        top_k=top_k,
        logger=logger,
    )
    if kb_context and kb_sources and kb_confidence >= MIN_ANCHOR_CONFIDENCE:
        return AnchoredContext(
            context=kb_context,
            kind="knowledge",
            confidence=kb_confidence,
            sources=kb_sources,
            material_titles=[],
        )

    if session_id is not None:
        material_context, _, material_confidence, material_sources = (
            await build_wiki_context_with_sources(
                wiki_service,
                query=query,
                session_id=session_id,
                top_k=top_k,
                logger=logger,
            )
        )
        if (
            material_context
            and material_sources
            and material_confidence >= MIN_ANCHOR_CONFIDENCE
        ):
            material_titles = sorted(
                {
                    str(source.get("source_name") or source.get("title") or "")
                    for source in material_sources
                }
            )
            return AnchoredContext(
                context=material_context,
                kind="material",
                confidence=material_confidence,
                sources=material_sources,
                material_titles=material_titles,
            )

    return AnchoredContext(
        context="",
        kind="none",
        confidence=kb_confidence,
        sources=kb_sources,
        material_titles=[],
    )


def build_profile_lines(
    profile: dict[str, Any],
    fields: tuple[str, ...] = (
        "major",
        "grade",
        "learning_goal",
        "cognitive_style",
        "knowledge_base",
        "learning_pace",
        "coding_level",
        "weekly_hours",
    ),
) -> list[str]:
    labels = {
        "major": "专业",
        "grade": "年级",
        "learning_goal": "学习目标",
        "cognitive_style": "认知风格",
        "knowledge_base": "知识基础",
        "learning_pace": "学习节奏",
        "coding_level": "编程水平",
        "weekly_hours": "每周可投入时间",
        "weak_points": "薄弱知识点",
        "interest_areas": "兴趣方向",
    }
    lines: list[str] = []
    for field in fields:
        value = profile.get(field)
        if field == "knowledge_base":
            value = format_knowledge_base(value)
        elif isinstance(value, list):
            value = "、".join(str(item) for item in value if str(item).strip())
        elif isinstance(value, dict):
            value = format_knowledge_base(value)
        lines.append(f"- {labels.get(field, field)}：{value or '未提供'}")
    return lines


def format_knowledge_base(knowledge_base: Any) -> str:
    if not isinstance(knowledge_base, dict) or not knowledge_base:
        return "未提供"

    parts: list[str] = []
    for concept, raw_level in knowledge_base.items():
        if isinstance(raw_level, dict):
            raw_level = raw_level.get("level") or raw_level.get("status")
        parts.append(f"{concept}（{raw_level}）" if raw_level else str(concept))
    return "、".join(parts) if parts else "未提供"
