from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from app.agents.common import (
    build_profile_lines,
    build_wiki_context_with_sources,
    parse_json_object,
)
from app.agents.resource_types import AgentResource
from app.core.llm import BaseLLMClient, get_llm_client

if TYPE_CHECKING:
    from app.wiki.wiki_service import WikiService

logger = logging.getLogger(__name__)

_STRUCTURED_QUIZ_PROMPT = """\
你是 EduAgent 的练习题助手。请围绕学习主题生成结构化练习题。

主题：{topic}
{wiki_section}
{doc_section}

学生画像：
{profile_lines}

请输出以下 JSON 格式（不要输出其他内容）：
{{
  "settings": {{
    "mode": "training",
    "question_count": 10,
    "question_types": ["choice", "judge", "short_answer"],
    "difficulty": "all",
    "time_limit_sec": 600,
    "chapter_mix": true
  }},
  "questions": [
    {{
      "id": 1,
      "type": "choice",
      "difficulty": "easy",
      "knowledge_point": "知识点名称",
      "chapter": "章节名称",
      "question": "题目内容",
      "options": ["A. 选项一", "B. 选项二", "C. 选项三", "D. 选项四"],
      "answer": "A",
      "explanation": "解析说明"
    }},
    {{
      "id": 2,
      "type": "judge",
      "difficulty": "medium",
      "knowledge_point": "知识点名称",
      "chapter": "章节名称",
      "question": "判断题题目内容",
      "options": ["A. 正确", "B. 错误"],
      "answer": "B",
      "explanation": "解析说明"
    }},
    {{
      "id": 3,
      "type": "short_answer",
      "difficulty": "hard",
      "knowledge_point": "知识点名称",
      "chapter": "章节名称",
      "question": "简答题题目",
      "options": [],
      "answer": "参考答案",
      "explanation": "解析说明"
    }}
  ]
}}

出题要求：
1. 默认生成 10 道题，至少包含选择题、判断题、简答题
2. 覆盖基础理解、概念辨析、应用思考和易错点
3. 每题标注 difficulty：easy / medium / hard
4. 每题标注 knowledge_point；如参考知识含多个章节，chapter_mix 设为 true 并混合章节
5. 难度与学生画像匹配，全部使用中文"""


class QuizAgent:
    """练习题生成 Agent，支持结构化 JSON 和 Markdown 两种输出。"""

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        wiki_service: WikiService | None = None,
    ) -> None:
        self.llm_client = llm_client or get_llm_client()
        self.wiki_service = wiki_service

    async def generate_quiz(
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

        structured = await self._try_structured_quiz(
            normalized_topic,
            profile or {},
            wiki_context,
            document_content or "",
        )

        if structured:
            content = json.dumps(structured, ensure_ascii=False)
            return AgentResource(
                title=f"{normalized_topic}练习题",
                resource_type="quiz",
                content=content,
                knowledge_point=normalized_topic,
                agent_name="QuizAgent",
                wiki_fallback=wiki_fallback,
                wiki_context=wiki_context,
                confidence=confidence,
                sources=sources,
            )

        prompt = self.build_prompt(
            normalized_topic,
            profile or {},
            wiki_context=wiki_context,
            document_content=document_content or "",
        )
        content = await self.llm_client.generate_text(prompt)
        return AgentResource(
            title=f"{normalized_topic}练习题",
            resource_type="quiz",
            content=self._normalize_content(normalized_topic, content),
            knowledge_point=normalized_topic,
            agent_name="QuizAgent",
            wiki_fallback=wiki_fallback,
            wiki_context=wiki_context,
            confidence=confidence,
            sources=sources,
        )

    async def _try_structured_quiz(
        self,
        topic: str,
        profile: dict[str, Any],
        wiki_context: str,
        document_content: str,
    ) -> dict[str, Any] | None:
        try:
            wiki_section = f"\n参考知识：\n{wiki_context}" if wiki_context else ""
            doc_section = (
                f"\n上游学习讲义：\n{document_content[:1000]}"
                if document_content
                else ""
            )
            profile_lines = "\n".join(self._build_profile_lines(profile))

            prompt = _STRUCTURED_QUIZ_PROMPT.format(
                topic=topic,
                wiki_section=wiki_section,
                doc_section=doc_section,
                profile_lines=profile_lines,
            )
            raw = await self.llm_client.generate_text(prompt)
            parsed = self._parse_json(raw)

            if "questions" in parsed and isinstance(parsed["questions"], list):
                return self._normalize_structured_quiz(parsed, topic)
        except Exception:
            logger.warning("结构化练习题生成失败，回退 Markdown 模式", exc_info=True)
        return None

    def _normalize_structured_quiz(
        self, parsed: dict[str, Any], topic: str
    ) -> dict[str, Any]:
        questions: list[dict[str, Any]] = []
        for index, raw_question in enumerate(parsed.get("questions", []), start=1):
            if not isinstance(raw_question, dict):
                continue
            question = dict(raw_question)
            question["id"] = int(question.get("id") or index)
            options = question.get("options")
            if not isinstance(options, list):
                options = []
            question["options"] = options
            question_type = str(question.get("type") or "").strip()
            if question_type not in {"choice", "judge", "short_answer"}:
                question_type = "short_answer" if not options else "choice"
            question["type"] = question_type
            if question.get("difficulty") not in {"easy", "medium", "hard"}:
                question["difficulty"] = _default_difficulty(index)
            if not str(question.get("knowledge_point") or "").strip():
                question["knowledge_point"] = topic
            question["chapter"] = str(question.get("chapter") or "").strip()
            questions.append(question)

        settings = parsed.get("settings") if isinstance(parsed.get("settings"), dict) else {}
        question_types = sorted({str(q["type"]) for q in questions})
        normalized_settings = {
            "mode": str(settings.get("mode") or "training"),
            "question_count": int(settings.get("question_count") or min(len(questions), 10)),
            "question_types": settings.get("question_types") or question_types,
            "difficulty": str(settings.get("difficulty") or "all"),
            "time_limit_sec": int(settings.get("time_limit_sec") or 600),
            "chapter_mix": bool(settings.get("chapter_mix", True)),
        }
        return {"settings": normalized_settings, "questions": questions}

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

    def build_prompt(
        self,
        topic: str,
        profile: dict[str, Any],
        *,
        wiki_context: str = "",
        document_content: str = "",
    ) -> str:
        profile_lines = self._build_profile_lines(profile)
        parts = [
            "你是 EduAgent 的练习题助手。",
            "请围绕学习主题输出中文练习题，适合高校学生自测。",
            f"主题：{topic}",
        ]

        if wiki_context:
            parts.extend(["", wiki_context])

        if document_content:
            parts.extend(["", "上游学习讲义：", document_content])

        parts.extend(
            [
                "",
                "学生画像：",
                *profile_lines,
                "出题要求：",
                "1. 只输出中文内容。",
                "2. 至少包含三道题，覆盖基础理解、概念辨析和应用思考。",
                "3. 每道题都附参考答案或解析。",
                "4. 难度要与学生画像匹配，适合复习场景。",
                "5. 内容适合直接展示在学习资料卡片中，不要输出系统提示语。",
            ]
        )
        return "\n".join(parts)

    def _build_profile_lines(self, profile: dict[str, Any]) -> list[str]:
        return build_profile_lines(
            profile,
            ("learning_goal", "cognitive_style", "learning_pace", "coding_level"),
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
        return f"{topic}练习题\n\n1. 基础理解题\n请稍后重试。"


def _default_difficulty(index: int) -> str:
    if index <= 4:
        return "easy"
    if index <= 8:
        return "medium"
    return "hard"
