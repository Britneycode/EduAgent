from __future__ import annotations

import logging
import re
from typing import Any

from app.agents.common import parse_json_object
from app.core.llm import BaseLLMClient
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

_MAJOR_PATTERNS = (
    re.compile(
        r"我是(?P<major>[一-龥A-Za-z]+专业)(?:的)?(?:大一|大二|大三|大四|研一|研二|研三)?学生?"
    ),
    re.compile(r"(?P<major>[一-龥A-Za-z]+专业)"),
)

_GRADE_PATTERNS = (re.compile(r"(?P<grade>大一|大二|大三|大四|研一|研二|研三)"),)

_KNOWLEDGE_PATTERNS = (
    re.compile(
        r"(?P<subject>[一-龥A-Za-z0-9]+)(?:基础|功底)(?P<level>薄弱|较差|很差|一般|还行|较好|不错|扎实)"
    ),
    re.compile(
        r"对(?P<subject>[一-龥A-Za-z0-9]+)(?:了解|掌握)(?P<level>很少|不多|一般|还行|不错|较好)"
    ),
)

_WEEKLY_HOURS_PATTERNS = (
    re.compile(r"每周(?:大概|大约|大致|一般)?能学(?P<hours>\d+)小时"),
    re.compile(r"每周(?:有|能投入|可以投入)(?P<hours>\d+)小时"),
    re.compile(r"一周(?:能学|能投入|可以投入)(?P<hours>\d+)小时"),
)

_GOAL_KEYWORDS = {
    "复习": "复习",
    "预习": "预习",
    "入门": "入门",
    "备考": "备考",
    "考试": "备考",
    "刷题": "刷题",
    "整理": "整理笔记",
    "总结": "整理总结",
}

_STYLE_KEYWORDS = {
    "图文结合": "图文结合",
    "配图讲解": "图文结合",
    "文字为主": "文字为主",
    "例子多一点": "案例驱动",
    "举例": "案例驱动",
    "循序渐进": "循序渐进",
}

_PACE_KEYWORDS = {
    "学得比较慢": "较慢",
    "学得慢": "较慢",
    "慢一点": "较慢",
    "节奏慢": "较慢",
    "学得比较快": "较快",
    "学得快": "较快",
    "节奏快": "较快",
    "循序渐进": "平稳",
}

_CODING_KEYWORDS = {
    "零基础": "零基础",
    "不会编程": "零基础",
    "编程水平初级": "初级",
    "编程基础一般": "初级",
    "编程水平一般": "初级",
    "编程水平中级": "中级",
    "有编程基础": "中级",
    "编程水平高级": "高级",
    "编程经验丰富": "高级",
}

_PROFILE_EXTRACT_PROMPT = """\
你是 EduAgent 的学生画像抽取器。从学生的自然语言描述中提取结构化画像信息。

学生输入：{user_message}

请输出以下 JSON（只输出能从输入中明确推断的字段，无法推断的字段不要包含）：
{{
  "major": "专业名称",
  "grade": "大一/大二/大三/大四/研一/研二/研三",
  "learning_goal": "复习/预习/入门/备考/刷题/整理笔记",
  "cognitive_style": "图文结合/文字为主/案例驱动/循序渐进",
  "learning_pace": "较慢/平稳/较快",
  "coding_level": "零基础/初级/中级/高级",
  "weekly_hours": 10,
  "knowledge_base": {{"科目名": "薄弱/一般/较好"}},
  "weak_points": ["薄弱知识点1", "薄弱知识点2"],
  "interest_areas": ["感兴趣的方向1"]
}}

注意：
1. 只输出 JSON，不要解释
2. "高中学过点 Python 但忘了" → coding_level 为 "初级"
3. "喜欢看视频/动画学" → cognitive_style 为 "图文结合"
4. "数学不太好" → knowledge_base 为 {{"数学": "薄弱"}}
5. 无法推断的字段直接省略，不要猜测"""


class ProfileAgent:
    """学生画像增量抽取 Agent，支持 LLM 智能抽取和正则 fallback。"""

    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client

    async def extract_profile_update_async(self, text: str) -> dict[str, Any]:
        """优先用 LLM 抽取，失败时回退正则。"""
        if self.llm_client is None:
            return self.extract_profile_update(text)

        try:
            return await self._llm_extract(text)
        except Exception:
            logger.warning("LLM 画像抽取失败，回退正则", exc_info=True)
            return self.extract_profile_update(text)

    async def _llm_extract(self, text: str) -> dict[str, Any]:
        prompt = _PROFILE_EXTRACT_PROMPT.format(user_message=text)
        raw = await self.llm_client.generate_text(prompt)
        parsed = self._parse_json(raw)

        result: dict[str, Any] = {}
        for key in (
            "major",
            "grade",
            "learning_goal",
            "cognitive_style",
            "learning_pace",
            "coding_level",
        ):
            if key in parsed and parsed[key]:
                result[key] = str(parsed[key]).strip()

        if "weekly_hours" in parsed:
            try:
                hours = int(parsed["weekly_hours"])
                if hours > 0:
                    result["weekly_hours"] = hours
            except (ValueError, TypeError):
                logger.debug(
                    "weekly_hours 解析失败，已忽略: %r",
                    parsed.get("weekly_hours"),
                )

        if "knowledge_base" in parsed and isinstance(parsed["knowledge_base"], dict):
            result["knowledge_base"] = parsed["knowledge_base"]

        if "weak_points" in parsed and isinstance(parsed["weak_points"], list):
            result["weak_points"] = [str(p) for p in parsed["weak_points"] if p]

        if "interest_areas" in parsed and isinstance(parsed["interest_areas"], list):
            result["interest_areas"] = [str(a) for a in parsed["interest_areas"] if a]

        return ProfileService(session=None).sanitize_profile_update(result)

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

    def extract_profile_update(self, text: str) -> dict[str, Any]:
        """正则规则抽取（同步 fallback）。"""
        normalized_text = text.strip()
        if not normalized_text:
            return {}

        update: dict[str, Any] = {}

        major = self._extract_by_patterns(normalized_text, _MAJOR_PATTERNS, "major")
        if major:
            update["major"] = major

        grade = self._extract_by_patterns(normalized_text, _GRADE_PATTERNS, "grade")
        if grade:
            update["grade"] = grade

        learning_goal = self._extract_keyword_value(normalized_text, _GOAL_KEYWORDS)
        if learning_goal:
            update["learning_goal"] = learning_goal

        cognitive_style = self._extract_keyword_value(normalized_text, _STYLE_KEYWORDS)
        if cognitive_style:
            update["cognitive_style"] = cognitive_style

        knowledge_base = self._extract_knowledge_base(normalized_text)
        if knowledge_base:
            update["knowledge_base"] = knowledge_base

        learning_pace = self._extract_keyword_value(normalized_text, _PACE_KEYWORDS)
        if learning_pace:
            update["learning_pace"] = learning_pace

        coding_level = self._extract_keyword_value(normalized_text, _CODING_KEYWORDS)
        if coding_level:
            update["coding_level"] = coding_level

        weekly_hours = self._extract_weekly_hours(normalized_text)
        if weekly_hours is not None:
            update["weekly_hours"] = weekly_hours

        return ProfileService(session=None).sanitize_profile_update(update)

    def _extract_by_patterns(
        self,
        text: str,
        patterns: tuple[re.Pattern[str], ...],
        group_name: str,
    ) -> str | None:
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                value = match.group(group_name).strip("，。！？、 ")
                if value:
                    return value
        return None

    def _extract_keyword_value(self, text: str, mapping: dict[str, str]) -> str | None:
        for keyword, value in mapping.items():
            if keyword in text:
                return value
        return None

    def _extract_knowledge_base(self, text: str) -> dict[str, str]:
        for pattern in _KNOWLEDGE_PATTERNS:
            match = pattern.search(text)
            if match:
                subject = match.group("subject").strip("，。！？、 ")
                level = match.group("level").strip("，。！？、 ")
                if subject and level:
                    return {subject: self._normalize_knowledge_level(level)}
        return {}

    def _normalize_knowledge_level(self, level: str) -> str:
        if level in {"薄弱", "较差", "很差"}:
            return "薄弱"
        if level in {"较好", "不错", "扎实"}:
            return "较好"
        return "一般"

    def _extract_weekly_hours(self, text: str) -> int | None:
        for pattern in _WEEKLY_HOURS_PATTERNS:
            match = pattern.search(text)
            if match:
                return int(match.group("hours"))
        return None
