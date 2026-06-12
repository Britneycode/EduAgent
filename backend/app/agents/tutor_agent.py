from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from app.agents.common import build_plain_wiki_context, build_profile_lines
from app.core.llm import BaseLLMClient, get_llm_client

if TYPE_CHECKING:
    from app.wiki.wiki_service import WikiService

logger = logging.getLogger(__name__)


class TutorAgent:
    """智能辅导 Agent — 即时答疑 + 苏格拉底式引导。"""

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        wiki_service: WikiService | None = None,
    ) -> None:
        self.llm_client = llm_client or get_llm_client()
        self.wiki_service = wiki_service

    async def answer(
        self,
        question: str,
        profile: dict[str, Any] | None,
        *,
        history: list[dict[str, str]] | None = None,
        study_mode: bool = False,
        course_id: str | None = None,
    ) -> str:
        normalized = question.strip() if question else ""
        if not normalized:
            return "请告诉我你的问题，我来帮你解答。"

        wiki_context = await self._build_wiki_context(normalized, course_id=course_id)
        prompt = self._build_prompt(
            normalized,
            profile or {},
            wiki_context,
            history or [],
            study_mode=study_mode,
        )
        return await self.llm_client.generate_text(prompt)

    async def answer_stream(
        self,
        question: str,
        profile: dict[str, Any] | None,
        *,
        history: list[dict[str, str]] | None = None,
        study_mode: bool = False,
        course_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        normalized = question.strip() if question else ""
        if not normalized:
            yield "请告诉我你的问题，我来帮你解答。"
            return

        wiki_context = await self._build_wiki_context(normalized, course_id=course_id)
        prompt = self._build_prompt(
            normalized,
            profile or {},
            wiki_context,
            history or [],
            study_mode=study_mode,
        )
        async for token in self.llm_client.generate_stream(prompt):
            yield token

    async def _build_wiki_context(
        self, query: str, course_id: str | None = None
    ) -> str:
        return await build_plain_wiki_context(
            self.wiki_service,
            query=query,
            course_id=course_id,
            logger=logger,
        )

    def _build_prompt(
        self,
        question: str,
        profile: dict[str, Any],
        wiki_context: str,
        history: list[dict[str, str]],
        *,
        study_mode: bool = False,
    ) -> str:
        parts = [
            "你是 EduAgent 的智能辅导助手，擅长围绕学生当前学习内容答疑。",
            "请用中文、友好亲切的语气回答学生的问题。",
        ]
        if study_mode:
            parts.extend(
                [
                    "当前启用 Study Mode：你要像学习教练一样分步辅导，而不是直接给完整答案。",
                    "请按“诊断目标 → 分步提示 → 理解检查 → 小结”的顺序组织回复。",
                ]
            )

        if history:
            parts.extend(["", "对话历史（从旧到新）："])
            for msg in history[-8:]:
                role_label = "学生" if msg["role"] == "user" else "助手"
                content_preview = msg["content"][:200]
                parts.append(f"[{role_label}] {content_preview}")

        parts.extend(["", f"学生问题：{question}"])

        if wiki_context:
            parts.extend(["", "参考知识：", wiki_context])

        profile_lines = self._build_profile_lines(profile)
        if any(line.split("：", 1)[-1].strip() != "未提供" for line in profile_lines):
            parts.extend(["", "学生画像：", *profile_lines])

        parts.extend(
            [
                "",
                "回答要求：",
                *self._build_answer_requirements(study_mode),
            ]
        )

        return "\n".join(parts)

    def _build_profile_lines(self, profile: dict[str, Any]) -> list[str]:
        return build_profile_lines(
            profile,
            ("learning_goal", "cognitive_style", "learning_pace", "coding_level"),
        )

    def _build_answer_requirements(self, study_mode: bool) -> list[str]:
        if study_mode:
            return [
                "1. 先诊断学生的目标、当前理解和可能卡点；信息不足时先提出一个聚焦问题。",
                "2. 用 2-3 个逐步提示引导学生自己推理，避免一开始直接给最终答案。",
                "3. 每一步都要有一个小的理解检查问题，便于学生回应。",
                "4. 如果学生明显需要结论，最后给出简短总结和下一步练习建议。",
                "5. 如有参考知识，基于参考知识回答并注明出处章节。",
                "6. 输出使用 Markdown 格式，结构要清晰、短段落优先。",
            ]
        return [
            "1. 优先使用苏格拉底式引导：先问一个小问题帮学生回忆，再给出解答。",
            "2. 如果问题简单明确，直接给出清晰解答即可。",
            "3. 适当使用类比和生活例子帮助理解。",
            "4. 如有参考知识，基于参考知识回答并注明出处章节。",
            "5. 如果参考知识不足以回答，可以适当补充但需说明。",
            "6. 输出使用 Markdown 格式，可包含代码块、列表、公式等。",
        ]
