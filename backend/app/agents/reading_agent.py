from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.agents.common import (
    AnchoredContext,
    build_anchored_context,
    build_profile_lines,
    build_wiki_context_with_sources,
)
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
        session_id: int | None = None,
    ) -> AgentResource:
        normalized_topic = topic.strip() if topic else "当前学习主题"
        anchored: AnchoredContext | None = None
        if session_id is not None:
            # 会话材料锚定：知识库未命中/低置信时回退该会话已挂载材料（统一入口）。
            anchored = await build_anchored_context(
                self.wiki_service,
                query=normalized_topic,
                course_id=course_id,
                session_id=session_id,
                logger=logger,
            )
            wiki_context = anchored.context
            wiki_fallback = anchored.kind == "none"
            confidence = anchored.confidence
            sources = anchored.sources
        else:
            (
                wiki_context,
                wiki_fallback,
                confidence,
                sources,
            ) = await self._build_wiki_context(normalized_topic, course_id=course_id)
        context_kind = anchored.kind if anchored else ""

        prompt = self.build_prompt(
            normalized_topic,
            profile or {},
            wiki_context=wiki_context,
            document_content=document_content or "",
            anchored=anchored,
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
            context_kind=context_kind,
        )

    def build_prompt(
        self,
        topic: str,
        profile: dict[str, Any],
        *,
        wiki_context: str = "",
        document_content: str = "",
        anchored: AnchoredContext | None = None,
    ) -> str:
        parts = [
            "你是 EduAgent 的拓展阅读助手。",
            "请围绕学习主题输出一份中文拓展阅读清单，帮助高校学生从课程内容延伸到实践与研究。",
            f"主题：{topic}",
        ]

        if wiki_context:
            material_section = self._material_section(anchored)
            parts.extend(["", material_section if material_section else wiki_context])
        if document_content:
            parts.extend(["", "上游学习讲义摘要：", document_content[:1200]])

        parts.extend(
            [
                "",
                "学生画像：",
                *build_profile_lines(
                    profile,
                    ("learning_goal", "cognitive_style", "coding_level"),
                ),
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

    def _material_section(self, anchored: AnchoredContext | None) -> str | None:
        """材料锚定时生成带来源标注的上下文段落；其余情况返回 None 走原有路径。"""
        if anchored is None or anchored.kind != "material" or not anchored.context:
            return None
        material_label = "、".join(anchored.material_titles) or "已上传材料"
        return (
            "学生上传的学习材料（检索到的相关片段）：\n"
            f"{anchored.context}\n"
            "推荐依据：结合上述学生材料推荐衔接的拓展阅读，"
            f"并标注材料来源：📎 {material_label}。"
        )

    async def _build_wiki_context(
        self, topic: str, course_id: str | None = None
    ) -> tuple[str, bool, float, list[dict[str, Any]]]:
        return await build_wiki_context_with_sources(
            self.wiki_service,
            query=topic,
            course_id=course_id,
            logger=logger,
        )

    def _normalize_content(self, topic: str, content: str) -> str:
        normalized = content.strip()
        if normalized:
            return normalized
        return f"{topic}拓展阅读\n\n1. 建议先复习教材相关章节，再结合课程讲义和实践资料加深理解。"
