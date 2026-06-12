from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.agents.common import build_profile_lines, build_wiki_context_with_sources
from app.agents.resource_types import AgentResource
from app.core.llm import BaseLLMClient, get_llm_client

if TYPE_CHECKING:
    from app.wiki.wiki_service import WikiService

logger = logging.getLogger(__name__)


class DocAgent:
    """学习文档生成 Agent — 基于 Wiki RAG 检索生成个性化讲义。"""

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        wiki_service: WikiService | None = None,
    ) -> None:
        self.llm_client = llm_client or get_llm_client()
        self.wiki_service = wiki_service

    async def generate_document(
        self,
        topic: str,
        profile: dict[str, Any] | None,
        course_id: str | None = None,
    ) -> AgentResource:
        normalized_topic = topic.strip() if topic else "当前学习主题"

        wiki_context, wiki_fallback, confidence, sources = (
            await build_wiki_context_with_sources(
                self.wiki_service,
                query=normalized_topic,
                course_id=course_id,
                logger=logger,
            )
        )

        prompt = self.build_prompt(normalized_topic, profile or {}, wiki_context)
        content = await self.llm_client.generate_text(prompt)

        return AgentResource(
            title=f"{normalized_topic}个性化学习讲义",
            resource_type="document",
            content=self._normalize_content(normalized_topic, content),
            knowledge_point=normalized_topic,
            agent_name="DocAgent",
            wiki_fallback=wiki_fallback,
            wiki_context=wiki_context,
            confidence=confidence,
            sources=sources,
        )

    def build_prompt(
        self, topic: str, profile: dict[str, Any], wiki_context: str = ""
    ) -> str:
        profile_lines = self._build_profile_lines(profile)
        parts = [
            "你是 EduAgent 的学习文档助手。",
            "请输出一份中文学习讲义，内容面向高校学生，语气清晰、友好、便于自学。",
            f"主题：{topic}",
        ]

        if wiki_context:
            parts.append("")
            parts.append(wiki_context)
            parts.append("")

        parts.extend(
            [
                "学生画像：",
                *profile_lines,
                "写作要求：",
                "1. 只输出中文内容，不要输出英文小节标题。",
                "2. 结构包含：主题概览、核心概念、学习步骤、常见误区、复习建议。",
                "3. 结合学生画像调整难度、节奏和表达方式。",
                "4. 如果认知风格偏图文结合，请多使用类比、分点和层次化说明。",
                "5. 内容要适合直接展示在学习资料卡片中，不要包含系统提示语。",
            ]
        )

        if wiki_context:
            parts.append(
                "6. 请基于以上参考知识生成讲义。如果参考知识不足以覆盖主题，"
                "可以适当补充，但需注明哪些是补充内容。"
            )

        return "\n".join(parts)

    def _build_profile_lines(self, profile: dict[str, Any]) -> list[str]:
        return build_profile_lines(profile)

    def _normalize_content(self, topic: str, content: str) -> str:
        normalized = content.strip()
        if normalized:
            return normalized
        return f"{topic}学习讲义\n\n一、主题概览\n当前未生成到有效正文，请稍后重试。"
