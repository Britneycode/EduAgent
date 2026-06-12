from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from app.agents.common import build_wiki_context_with_sources, parse_json_object
from app.agents.resource_types import AgentResource
from app.core.image_gen import ImageGenClient, ImageGenError
from app.core.llm import BaseLLMClient, get_llm_client

if TYPE_CHECKING:
    from app.wiki.wiki_service import WikiService

logger = logging.getLogger(__name__)

_PPT_IMAGE_EXTRACT_PROMPT = """\
你是 EduAgent 的教学内容提炼专家。请根据给定的学习主题和参考资料，提炼出适合生成 PPT 图片的知识要点。

主题：{topic}

参考资料：
{wiki_context}

请输出 JSON 格式（不要输出其他内容）：
{{
  "slides": [
    {{
      "title": "封面标题（含副标题）",
      "key_points": ["要点1", "要点2", "要点3"],
      "summary": "一句话总结本页内容"
    }}
  ]
}}

要求：
1. 生成 2 页幻灯片的提炼内容（1封面 + 1核心知识总结）
2. 第 1 页为封面页（标题+概述），第 2 页为核心知识点+总结
3. 每页 key_points 控制在 3-5 条，精炼准确
4. 内容基于参考资料，不编造
5. 全部使用中文"""


class MediaAgent:
    """多媒体生成 Agent — 思维导图（Mermaid）和 PPT 大纲。"""

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        wiki_service: WikiService | None = None,
    ) -> None:
        self.llm_client = llm_client or get_llm_client()
        self.wiki_service = wiki_service

    async def generate_mindmap(
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
        prompt = self._build_mindmap_prompt(
            normalized_topic, profile or {}, wiki_context, document_content or ""
        )
        content = await self.llm_client.generate_text(prompt)
        return AgentResource(
            title=f"{normalized_topic}思维导图",
            resource_type="mindmap",
            content=self._normalize_content(normalized_topic, content, "思维导图"),
            knowledge_point=normalized_topic,
            agent_name="MediaAgent",
            wiki_fallback=wiki_fallback,
            wiki_context=wiki_context,
            confidence=confidence,
            sources=sources,
        )

    async def generate_ppt_outline(
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
        prompt = self._build_ppt_prompt(
            normalized_topic, profile or {}, wiki_context, document_content or ""
        )
        content = await self.llm_client.generate_text(prompt)
        return AgentResource(
            title=f"{normalized_topic}教学演示大纲",
            resource_type="ppt",
            content=self._normalize_content(normalized_topic, content, "PPT 大纲"),
            knowledge_point=normalized_topic,
            agent_name="MediaAgent",
            wiki_fallback=wiki_fallback,
            wiki_context=wiki_context,
            confidence=confidence,
            sources=sources,
        )

    async def generate_ppt_images(
        self,
        topic: str,
        profile: dict[str, Any] | None,
        document_content: str | None = None,
        course_id: str | None = None,
    ) -> AgentResource:
        """生成 PPT 风格的知识总结图片。"""
        normalized_topic = topic.strip() if topic else "当前学习主题"
        wiki_context, wiki_fallback, confidence, sources = (
            await self._build_wiki_context(normalized_topic, course_id=course_id)
        )

        # 1. 用 LLM 提炼知识要点
        slides = await self._extract_slide_content(
            normalized_topic, wiki_context
        )

        # 2. 用图片生成模型生成 PPT 风格图片
        image_prompts = [
            f"主题：{slide['title']}\n要点：{'；'.join(slide.get('key_points', []))}\n总结：{slide.get('summary', '')}"
            for slide in slides
        ]

        image_client = ImageGenClient()
        try:
            generated_images = await image_client.generate_images(image_prompts)
        except ImageGenError as exc:
            logger.warning("PPT 图片生成失败: %s", exc)
            # 回退到普通 PPT 大纲
            return await self.generate_ppt_outline(
                topic, profile, document_content, course_id
            )

        # 3. 组装结果
        ppt_data = {
            "type": "ppt_images",
            "topic": normalized_topic,
            "slides": [],
        }
        for i, slide in enumerate(slides):
            img_info = (
                generated_images[i]
                if i < len(generated_images)
                else {"error": "未生成"}
            )
            ppt_data["slides"].append(
                {
                    "title": slide.get("title", ""),
                    "key_points": slide.get("key_points", []),
                    "summary": slide.get("summary", ""),
                    "image_url": img_info.get("url", ""),
                    "error": img_info.get("error"),
                }
            )

        content = json.dumps(ppt_data, ensure_ascii=False)
        return AgentResource(
            title=f"{normalized_topic}教学演示PPT",
            resource_type="ppt",
            content=content,
            knowledge_point=normalized_topic,
            agent_name="MediaAgent",
            wiki_fallback=wiki_fallback,
            wiki_context=wiki_context,
            confidence=confidence,
            sources=sources,
        )

    async def _extract_slide_content(
        self, topic: str, wiki_context: str
    ) -> list[dict[str, Any]]:
        """用 LLM 提炼 PPT 各页的知识要点。"""
        prompt = _PPT_IMAGE_EXTRACT_PROMPT.format(
            topic=topic,
            wiki_context=wiki_context or "无额外参考资料，请基于通用知识提炼",
        )
        try:
            raw = await self.llm_client.generate_text(prompt)
            parsed = self._parse_json(raw)
            slides = parsed.get("slides", [])
            if isinstance(slides, list) and len(slides) >= 2:
                return slides
        except Exception:
            logger.warning("LLM 提炼 PPT 要点失败，使用默认结构", exc_info=True)

        # 回退：双页结构
        return [
            {
                "title": f"{topic} — 概述",
                "key_points": [
                    f"{topic}的核心概念与定义",
                    f"{topic}的关键原理与机制",
                    f"{topic}的典型应用场景",
                ],
                "summary": f"掌握{topic}的基础知识体系",
            },
            {
                "title": f"{topic} — 核心要点与总结",
                "key_points": [
                    "知识要点一：基本定义与特征",
                    "知识要点二：主要方法与技术",
                    "知识要点三：实践应用与案例",
                    "知识要点四：常见误区与注意点",
                ],
                "summary": f"理解{topic}的关键知识点，建立完整知识框架",
            },
        ]

    async def generate_animation_script(
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
        prompt = self._build_animation_prompt(
            normalized_topic, profile or {}, wiki_context, document_content or ""
        )
        content = await self.llm_client.generate_text(prompt)
        return AgentResource(
            title=f"{normalized_topic}动画讲解脚本",
            resource_type="animation",
            content=self._normalize_content(normalized_topic, content, "动画脚本"),
            knowledge_point=normalized_topic,
            agent_name="MediaAgent",
            wiki_fallback=wiki_fallback,
            wiki_context=wiki_context,
            confidence=confidence,
            sources=sources,
        )

    def _build_mindmap_prompt(
        self,
        topic: str,
        profile: dict[str, Any],
        wiki_context: str,
        document_content: str,
    ) -> str:
        parts = [
            "你是 EduAgent 的思维导图助手。",
            "请为以下主题生成一份结构化的思维导图，使用 Mermaid mindmap 语法。",
            f"主题：{topic}",
        ]
        if wiki_context:
            parts.extend(["", wiki_context])
        if document_content:
            parts.extend(["", "上游学习讲义：", document_content])
        parts.extend(
            [
                "",
                f"学生学习目标：{profile.get('learning_goal') or '未提供'}",
                "",
                "输出要求：",
                "1. 使用 Mermaid mindmap 语法，用 ```mermaid 代码块包裹。",
                "2. 层级结构清晰，核心概念为中心，分支为子概念。",
                "3. 每个分支的叶子节点简洁精炼，方便记忆。",
                "4. 在思维导图之后，补充一段简短的文字说明。",
                "5. 全部使用中文。",
            ]
        )
        return "\n".join(parts)

    def _build_ppt_prompt(
        self,
        topic: str,
        profile: dict[str, Any],
        wiki_context: str,
        document_content: str,
    ) -> str:
        parts = [
            "你是 EduAgent 的教学演示助手。",
            "请为以下主题生成一份 PPT 演示大纲，结构清晰，适合课堂教学。",
            f"主题：{topic}",
        ]
        if wiki_context:
            parts.extend(["", wiki_context])
        if document_content:
            parts.extend(["", "上游学习讲义：", document_content])
        parts.extend(
            [
                "",
                f"学生学习目标：{profile.get('learning_goal') or '未提供'}",
                "",
                "输出要求：",
                "1. 按幻灯片页码组织（第1页、第2页...），每页包含标题和要点。",
                "2. 包含封面页、目录页、正文页（5-8页）、总结页。",
                "3. 每页要点控制在 3-5 条，简洁有力。",
                "4. 在大纲之后，可以补充演讲备注建议。",
                "5. 全部使用中文，输出 Markdown 格式。",
            ]
        )
        return "\n".join(parts)

    def _build_animation_prompt(
        self,
        topic: str,
        profile: dict[str, Any],
        wiki_context: str,
        document_content: str,
    ) -> str:
        parts = [
            "你是 EduAgent 的教学动画脚本助手。",
            "请为以下主题生成一份短视频或动画讲解脚本，适合学生自学。",
            f"主题：{topic}",
        ]
        if wiki_context:
            parts.extend(["", wiki_context])
        if document_content:
            parts.extend(["", "上游学习讲义：", document_content[:1200]])
        parts.extend(
            [
                "",
                f"学生学习目标：{profile.get('learning_goal') or '未提供'}",
                "",
                "输出要求：",
                "1. 全部使用中文，输出 Markdown 格式。",
                "2. 包含镜头分镜、旁白、画面元素、关键公式或代码可视化建议。",
                "3. 时长控制在 1-3 分钟，按 5-8 个镜头组织。",
                "4. 每个镜头说明学习目的，避免只写宽泛口号。",
                "5. 内容适合后续接入视频/动画生成工具。",
            ]
        )
        return "\n".join(parts)

    async def _build_wiki_context(
        self, topic: str, course_id: str | None = None
    ) -> tuple[str, bool, float, list[dict[str, Any]]]:
        return await build_wiki_context_with_sources(
            self.wiki_service,
            query=topic,
            top_k=3,
            course_id=course_id,
            logger=logger,
        )

    def _normalize_content(self, topic: str, content: str, label: str) -> str:
        normalized = content.strip()
        if normalized:
            return normalized
        return f"{topic}{label}\n\n暂未生成到有效内容，请稍后重试。"

    def _parse_json(self, raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start : end + 1]

        return parse_json_object(cleaned)
