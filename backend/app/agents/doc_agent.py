from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.agents.common import (
    AnchoredContext,
    build_anchored_context,
    build_profile_lines,
)
from app.agents.resource_types import AgentResource
from app.core.llm import BaseLLMClient, get_llm_client

if TYPE_CHECKING:
    from app.wiki.wiki_service import WikiService

logger = logging.getLogger(__name__)


class DocAgent:
    """学习文档生成 Agent — 基于 Wiki RAG 检索生成个性化讲义。

    知识来源按「课程知识库 → 会话学习材料 → 无覆盖」三级兜底。
    """

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
        session_id: int | None = None,
    ) -> AgentResource:
        normalized_topic = topic.strip() if topic else "当前学习主题"

        anchored = await build_anchored_context(
            self.wiki_service,
            query=normalized_topic,
            course_id=course_id,
            session_id=session_id,
            logger=logger,
        )

        prompt = self.build_prompt(normalized_topic, profile or {}, anchored)
        content = await self.llm_client.generate_text(prompt)

        return AgentResource(
            title=f"{normalized_topic}个性化学习讲义",
            resource_type="document",
            content=self._normalize_content(normalized_topic, content),
            knowledge_point=normalized_topic,
            agent_name="DocAgent",
            # 仅「完全未锚定」才视为兜底告警；材料锚定（material）有明确来源，属可信生成。
            wiki_fallback=anchored.kind == "none",
            wiki_context=anchored.context,
            confidence=anchored.confidence,
            sources=anchored.sources,
            context_kind=anchored.kind,
        )

    def build_prompt(
        self,
        topic: str,
        profile: dict[str, Any],
        anchored: AnchoredContext | None = None,
    ) -> str:
        profile_lines = self._build_profile_lines(profile)
        anchored = anchored or AnchoredContext(
            context="", kind="none", confidence=0.0, sources=[], material_titles=[]
        )
        parts = [
            "你是 EduAgent 的学习文档助手。",
            "请输出一份中文学习讲义，内容面向高校学生，语气清晰、友好、便于自学。",
            f"主题：{topic}",
        ]

        if anchored.context:
            if anchored.kind == "material":
                material_label = "、".join(anchored.material_titles) or "已上传材料"
                parts.extend(
                    [
                        "",
                        "以下为学生上传的学习材料（检索到的相关片段）：",
                        anchored.context,
                        "",
                        f"写作依据：仅使用上述学生材料，并标注材料来源：📎 {material_label}。",
                    ]
                )
            else:
                parts.extend(
                    [
                        "",
                        anchored.context,
                        "",
                    ]
                )

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

        if anchored.kind == "knowledge":
            parts.append(
                "6. 请基于以上参考知识生成讲义。如果参考知识不足以覆盖主题，"
                "可以适当补充，但需注明哪些是补充内容。"
            )
        elif anchored.kind == "material":
            parts.append(
                "6. 本讲义必须仅依据学生上传的材料生成，不得编造材料之外的具体事实；"
                "材料不足覆盖的部分明确标注「材料未覆盖，建议补充」。"
            )
        else:
            parts.append(
                "6. 课程知识库与学生上传材料均未覆盖该主题：请在讲义开头明确标注"
                "「⚠️ 未经课程知识库与学习材料锚定，请核对教材」，内容仅作通用学习参考。"
            )

        return "\n".join(parts)

    def _build_profile_lines(self, profile: dict[str, Any]) -> list[str]:
        return build_profile_lines(profile)

    def _normalize_content(self, topic: str, content: str) -> str:
        normalized = content.strip()
        if normalized:
            return normalized
        return f"{topic}学习讲义\n\n一、主题概览\n当前未生成到有效正文，请稍后重试。"
