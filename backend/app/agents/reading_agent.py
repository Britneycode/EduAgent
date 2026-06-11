from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.agents.resource_types import AgentResource
from app.core.llm import BaseLLMClient, get_llm_client

if TYPE_CHECKING:
    from app.wiki.wiki_service import WikiService

logger = logging.getLogger(__name__)


class ReadingAgent:
    """拓展阅读 Agent — 基于课程 Wiki 组织课后阅读清单。"""

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        wiki_service: WikiService | None = None,
    ) -> None:
        self.llm_client = llm_client or get_llm_client()
        self.wiki_service = wiki_service

    async def generate_reading(
        self,
        topic: str,
        profile: dict[str, Any] | None,
        document_content: str | None = None,
        course_id: str | None = None,
    ) -> AgentResource:
        normalized_topic = topic.strip() if topic else "当前学习主题"
        wiki_context, wiki_fallback, confidence, sources = (
            await self._build_wiki_context(normalized_topic, course_id=course_id)
        )
        prompt = self.build_prompt(
            normalized_topic,
            profile or {},
            wiki_context=wiki_context,
            document_content=document_content or "",
        )
        content = await self.llm_client.generate_text(prompt)
        return AgentResource(
            title=f"{normalized_topic}拓展阅读",
            resource_type="reading",
            content=self._normalize_content(normalized_topic, content),
            knowledge_point=normalized_topic,
            agent_name="ReadingAgent",
            wiki_fallback=wiki_fallback,
            wiki_context=wiki_context,
            confidence=confidence,
            sources=sources,
        )

    def build_prompt(
        self,
        topic: str,
        profile: dict[str, Any],
        *,
        wiki_context: str = "",
        document_content: str = "",
    ) -> str:
        parts = [
            "你是 EduAgent 的拓展阅读助手。",
            "请围绕学习主题输出一份中文拓展阅读清单，帮助高校学生从课程内容延伸到实践与研究。",
            f"主题：{topic}",
        ]

        if wiki_context:
            parts.extend(["", wiki_context])
        if document_content:
            parts.extend(["", "上游学习讲义摘要：", document_content[:1200]])

        parts.extend(
            [
                "",
                "学生画像：",
                f"- 学习目标：{profile.get('learning_goal') or '未提供'}",
                f"- 认知风格：{profile.get('cognitive_style') or '未提供'}",
                f"- 编程水平：{profile.get('coding_level') or '未提供'}",
                "",
                "输出要求：",
                "1. 只输出中文内容。",
                "2. 包含：阅读顺序、推荐材料类型、推荐理由、阅读时重点问题。",
                "3. 至少给出 5 条阅读建议，覆盖教材章节、课程讲义、论文/博客、实践资料。",
                "4. 如果使用了参考知识，请说明对应章节或知识点。",
                "5. 内容适合直接展示在拓展阅读资源卡片中，不要输出系统提示语。",
            ]
        )
        return "\n".join(parts)

    async def _build_wiki_context(
        self, topic: str, course_id: str | None = None
    ) -> tuple[str, bool, float, list[dict[str, Any]]]:
        if self.wiki_service is None:
            return "", True, 0.0, []
        try:
            ctx_with_sources = await self.wiki_service.build_context_with_sources(
                query=topic, top_k=3, course_id=course_id
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
            logger.warning("Wiki 检索失败，将不使用知识库上下文", exc_info=True)
            return "", True, 0.0, []

    def _normalize_content(self, topic: str, content: str) -> str:
        normalized = content.strip()
        if normalized:
            return normalized
        return f"{topic}拓展阅读\n\n1. 建议先复习教材相关章节，再结合课程讲义和实践资料加深理解。"
