from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.agents.resource_types import AgentResource
from app.core.llm import BaseLLMClient, get_llm_client

if TYPE_CHECKING:
    from app.wiki.wiki_service import WikiService

logger = logging.getLogger(__name__)


class CodeAgent:
    """代码实践生成 Agent。"""

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        wiki_service: WikiService | None = None,
    ) -> None:
        self.llm_client = llm_client or get_llm_client()
        self.wiki_service = wiki_service

    async def generate_code(
        self,
        topic: str,
        profile: dict[str, Any] | None,
        document_content: str | None = None,
        quiz_content: str | None = None,
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
            quiz_content=quiz_content or "",
        )
        content = await self.llm_client.generate_text(prompt)
        return AgentResource(
            title=f"{normalized_topic}代码实践",
            resource_type="code",
            content=self._normalize_content(normalized_topic, content),
            knowledge_point=normalized_topic,
            agent_name="CodeAgent",
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
        quiz_content: str = "",
    ) -> str:
        profile_lines = self._build_profile_lines(profile)
        parts = [
            "你是 EduAgent 的代码实践助手。",
            "请围绕学习主题输出中文代码实践内容，默认提供 Python 示例。",
            f"主题：{topic}",
        ]

        if wiki_context:
            parts.extend(["", wiki_context])

        if document_content:
            parts.extend(["", "上游学习讲义：", document_content])

        if quiz_content:
            parts.extend(["", "上游练习题：", quiz_content])

        parts.extend(
            [
                "",
                "学生画像：",
                *profile_lines,
                "输出要求：",
                "1. 只输出中文内容。",
                "2. 包含代码目标、可运行 Python 示例、关键步骤说明、练习建议。",
                "3. 示例要紧扣主题，便于学生动手验证。",
                "4. 难度与学生画像匹配，默认适合课程复习。",
                "5. Python 示例必须放在 ```python 代码块中，尽量只使用标准库，不依赖 numpy/pandas/sklearn 等第三方库。",
                "6. 内容适合直接展示在学习资料卡片中，不要输出系统提示语。",
            ]
        )
        return "\n".join(parts)

    def _build_profile_lines(self, profile: dict[str, Any]) -> list[str]:
        return [
            f"- 学习目标：{profile.get('learning_goal') or '未提供'}",
            f"- 认知风格：{profile.get('cognitive_style') or '未提供'}",
            f"- 编程水平：{profile.get('coding_level') or '未提供'}",
            f"- 知识基础：{profile.get('knowledge_base') or '未提供'}",
        ]

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
        return f"{topic}代码实践\n\n一、代码目标\n请稍后重试。"
