from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from app.agents.common import (
    AnchoredContext,
    build_anchored_context,
    build_profile_lines,
)
from app.core.llm import BaseLLMClient, get_llm_client

if TYPE_CHECKING:
    from app.wiki.wiki_service import WikiService

logger = logging.getLogger(__name__)


class TutorAgent:
    """智能辅导 Agent — 即时答疑 + 苏格拉底式引导。

    知识来源按「课程知识库 → 会话学习材料 → 无覆盖」三级兜底：
    知识库置信度不足时切到学生上传的会话材料，两者都没有则如实说明，不编造。
    """

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
        session_id: int | None = None,
    ) -> str:
        normalized = question.strip() if question else ""
        if not normalized:
            return "请告诉我你的问题，我来帮你解答。"

        anchored = await self._build_anchored_context(
            normalized, course_id=course_id, session_id=session_id
        )
        prompt = self._build_prompt(
            normalized,
            profile or {},
            anchored,
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
        session_id: int | None = None,
    ) -> AsyncGenerator[str, None]:
        normalized = question.strip() if question else ""
        if not normalized:
            yield "请告诉我你的问题，我来帮你解答。"
            return

        anchored = await self._build_anchored_context(
            normalized, course_id=course_id, session_id=session_id
        )
        prompt = self._build_prompt(
            normalized,
            profile or {},
            anchored,
            history or [],
            study_mode=study_mode,
        )
        async for token in self.llm_client.generate_stream(prompt):
            yield token

    async def _build_anchored_context(
        self,
        query: str,
        course_id: str | None = None,
        session_id: int | None = None,
    ) -> AnchoredContext:
        return await build_anchored_context(
            self.wiki_service,
            query=query,
            course_id=course_id,
            session_id=session_id,
            logger=logger,
        )

    def _build_prompt(
        self,
        question: str,
        profile: dict[str, Any],
        anchored: AnchoredContext,
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

        if anchored.context:
            if anchored.kind == "material":
                parts.extend(
                    [
                        "",
                        "学生上传的学习材料（以下为检索到的相关片段）：",
                        anchored.context,
                    ]
                )
            else:
                parts.extend(["", "参考知识：", anchored.context])

        profile_lines = self._build_profile_lines(profile)
        if any(line.split("：", 1)[-1].strip() != "未提供" for line in profile_lines):
            parts.extend(["", "学生画像：", *profile_lines])

        parts.extend(
            [
                "",
                "回答要求：",
                *self._build_answer_requirements(anchored, study_mode),
            ]
        )

        return "\n".join(parts)

    def _build_profile_lines(self, profile: dict[str, Any]) -> list[str]:
        return build_profile_lines(
            profile,
            ("learning_goal", "cognitive_style", "learning_pace", "coding_level"),
        )

    def _build_answer_requirements(
        self, anchored: AnchoredContext, study_mode: bool
    ) -> list[str]:
        base_rules = []
        if study_mode:
            base_rules = [
                "1. 先诊断学生的目标、当前理解和可能卡点；信息不足时先提出一个聚焦问题。",
                "2. 用 2-3 个逐步提示引导学生自己推理，避免一开始直接给最终答案。",
                "3. 每一步都要有一个小的理解检查问题，便于学生回应。",
                "4. 如果学生明显需要结论，最后给出简短总结和下一步练习建议。",
                "5. 输出使用 Markdown 格式，结构要清晰、短段落优先。",
            ]
        else:
            base_rules = [
                "1. 优先使用苏格拉底式引导：先问一个小问题帮学生回忆，再给出解答。",
                "2. 如果问题简单明确，直接给出清晰解答即可。",
                "3. 适当使用类比和生活例子帮助理解。",
                "4. 输出使用 Markdown 格式，可包含代码块、列表、公式等。",
            ]

        if anchored.kind == "knowledge":
            base_rules.append("5. 基于参考知识回答并注明出处章节；知识不足时如实说明。")
        elif anchored.kind == "material":
            material_label = "、".join(anchored.material_titles) or "已上传材料"
            base_rules.extend(
                [
                    "5. 本回答必须仅依据学生上传的学习材料生成，不要引入材料之外的事实。",
                    f"6. 回答中标注材料来源：📎 {material_label}；材料未覆盖的问题如实说明。",
                ]
            )
        else:
            base_rules.extend(
                [
                    "5. 课程知识库与学生已上传材料均未覆盖该问题：先明确告知学生这一点，"
                    "再给出通用学习方法/查阅建议，并建议上传相关学习材料以获得更准确的辅导。",
                    "6. 不要编造具体事实、数据或教材内容。",
                ]
            )

        return base_rules
