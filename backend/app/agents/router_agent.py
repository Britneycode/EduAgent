from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.core.llm import BaseLLMClient

logger = logging.getLogger(__name__)

PROFILE_KEYWORDS = (
    "我是",
    "专业",
    "大一",
    "大二",
    "大三",
    "大四",
    "研一",
    "研二",
    "基础",
    "目标",
)

DOCUMENT_KEYWORDS = (
    "复习",
    "讲解",
    "整理",
    "笔记",
    "学习资料",
    "生成",
    "帮我",
)

TUTOR_KEYWORDS = (
    "什么是",
    "为什么",
    "怎么",
    "如何",
    "不理解",
    "不明白",
    "区别",
    "解释",
    "请问",
    "吗？",
    "吗?",
    "呢？",
    "呢?",
)

MINDMAP_KEYWORDS = (
    "思维导图",
    "脑图",
    "知识图谱",
    "知识结构",
)

PPT_KEYWORDS = (
    "PPT",
    "ppt",
    "幻灯片",
    "演示",
    "课件",
)

ANIMATION_KEYWORDS = (
    "动画",
    "视频",
    "可视化演示",
    "动态演示",
)

# 纯出题意图关键词：用户只想做题，不需要文档/代码/导图等其他资源
QUIZ_ONLY_KEYWORDS = (
    "出题",
    "出几道题",
    "出一些题",
    "出点题",
    "出个题",
    "出些题",
    "出练习",
    "出几道练习",
    "练习题",
    "出一组",
    "来个题",
    "来几道题",
    "给几道题",
    "给些题",
    "做题",
    "题目",
    "组题",
    "组卷",
    "刷题",
    "测试一下",
    "测一测",
    "考一考",
    "考考",
    "给我出",
    "我要做题",
    "我要练习",
    "出选择题",
    "出判断题",
    "出简答题",
    "出一套",
)

# 不触发全量资源生成的关键词（只生成用户具体要的）
EXACT_ONLY_KEYWORDS = (
    "ppt",
    "出题",
    "练习题",
    "题目",
    "选择题",
    "判断题",
    "动画",
    "视频",
    "导图",
    "脑图",
    "思维导图",
)

# 需要全量资源的动词
FULL_RESOURCE_VERBS = (
    "讲解",
    "复习",
    "整理",
    "笔记",
    "学习资料",
    "学习路径",
    "帮我梳理",
    "帮我整理",
    "帮我复习",
    "梳理",
)

DEFAULT_RESOURCE_TYPES = ["document", "quiz", "code", "mindmap", "reading"]

TOPIC_PATTERNS = (
    re.compile(r"想(?:复习|讲解|整理)(?P<topic>[一-龥A-Za-z0-9]+)"),
    re.compile(r"(?P<topic>[一-龥A-Za-z0-9]+?)的(?:学习笔记|笔记|讲解|学习资料)"),
    re.compile(r"(?:复习|讲解|整理)(?:一下)?(?P<topic>[一-龥A-Za-z0-9]+)"),
    re.compile(r"目标是(?P<topic>[一-龥A-Za-z0-9]+)"),
    re.compile(r"(?P<topic>[一-龥A-Za-z0-9]+)(?:是什么|为什么|怎么|如何)"),
    re.compile(r"什么是(?P<topic>[一-龥A-Za-z0-9]+)"),
)

TOPIC_PREFIXES = (
    "请帮我",
    "帮我",
    "请",
    "整理一下",
    "讲解一下",
    "复习一下",
    "一下",
)

_ROUTE_PROMPT = """\
你是 EduAgent 学习系统的意图路由器。根据学生的输入，判断意图并输出 JSON。

学生输入：{user_message}

请输出以下 JSON（不要输出其他内容）：
{{
  "update_profile": true/false,
  "is_tutor_question": true/false,
  "generate_document": true/false,
  "topic": "提取的学习主题",
  "resource_types": ["document", "quiz", "code", "mindmap", "reading"],
  "quiz_only": true/false,
  "need_mindmap": true/false,
  "need_ppt": true/false,
  "need_animation": true/false
}}

判断规则：
1. update_profile: 学生提到自己的专业、年级、基础、目标、编程水平、学习风格时为 true
2. is_tutor_question: 学生在提问（什么是/为什么/怎么/区别/不理解等）时为 true
3. generate_document: 学生需要生成学习资料（复习/讲解/整理/笔记/学习资料）时为 true
4. quiz_only: 学生只是想做题/出题（"出几道题""出一组练习题""给些题目""刷题""测试一下"等），不需要完整讲义、代码、思维导图时为 true。此时 generate_document=true 但 resource_types 只保留 ["quiz"]
5. 如果学生既要求讲解又要求出题（如"讲解一下神经网络再出几道题"），quiz_only=false，正常规划所有资源
6. 如果学生只是闲聊打招呼，is_tutor_question=true，topic 设为学生说的内容
7. topic: 从学生输入中提取核心学习主题
8. resource_types: generate_document 为 true 时默认 ["document","quiz","code","mindmap","reading"]；quiz_only 为 true 时只需 ["quiz"]
9. need_mindmap/need_ppt/need_animation: 学生明确要求思维导图、PPT、动画或视频时为 true"""


@dataclass(slots=True)
class RouteDecision:
    update_profile: bool
    generate_document: bool
    is_tutor_question: bool
    topic: str
    resource_types: list[str]
    quiz_only: bool = False  # 纯出题模式：只生成 quiz，不生成文档/代码/导图等


class RouterAgent:
    """学习请求路由判定，支持 LLM 智能路由和正则 fallback。"""

    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client

    async def route_async(self, text: str) -> RouteDecision:
        """优先用 LLM 路由，失败时回退正则。"""
        if self.llm_client is None:
            return self.route(text)

        try:
            return await self._llm_route(text)
        except Exception:
            logger.warning("LLM 路由失败，回退正则路由", exc_info=True)
            return self.route(text)

    async def _llm_route(self, text: str) -> RouteDecision:
        prompt = _ROUTE_PROMPT.format(user_message=text)
        raw = await self.llm_client.generate_text(prompt)
        parsed = self._parse_llm_response(raw)

        quiz_only = bool(parsed.get("quiz_only"))
        # 后处理：正则兜底检测单资源意图
        wants_full = self._contains_any(text, FULL_RESOURCE_VERBS)
        has_ppt = "ppt" in text.lower()
        has_quiz = self._contains_any(text, QUIZ_ONLY_KEYWORDS)
        has_mindmap = self._contains_any(text, MINDMAP_KEYWORDS)
        has_animation = self._contains_any(text, ANIMATION_KEYWORDS)

        # 用户明确只想要某个特定资源（没有说"讲解"、"复习"等）
        if not wants_full:
            if has_quiz:
                quiz_only = True
            elif has_ppt or has_mindmap or has_animation:
                quiz_only = True  # 复用 quiz_only 逻辑：不强制加 document

        resource_types: list[str] = []
        if parsed.get("generate_document"):
            if quiz_only:
                if has_ppt:
                    resource_types = ["ppt"]
                elif has_mindmap:
                    resource_types = ["mindmap"]
                elif has_animation:
                    resource_types = ["animation"]
                else:
                    resource_types = ["quiz"]
            else:
                resource_types = list(parsed.get("resource_types") or DEFAULT_RESOURCE_TYPES)
                if parsed.get("need_ppt") and "ppt" not in resource_types:
                    resource_types.append("ppt")
                if parsed.get("need_animation") and "animation" not in resource_types:
                    resource_types.append("animation")

        return RouteDecision(
            update_profile=bool(parsed.get("update_profile")),
            generate_document=bool(parsed.get("generate_document")),
            is_tutor_question=bool(parsed.get("is_tutor_question")),
            topic=str(parsed.get("topic") or text.strip()[:30]),
            resource_types=resource_types,
            quiz_only=quiz_only,
        )

    def _parse_llm_response(self, raw: str) -> dict[str, Any]:
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

        return json.loads(cleaned)

    def route(self, text: str) -> RouteDecision:
        """正则规则路由（同步，用于 dev mode 或 LLM 失败时的 fallback）。"""
        normalized_text = text.strip()
        update_profile = self._contains_any(normalized_text, PROFILE_KEYWORDS)
        is_tutor = self._contains_any(
            normalized_text, TUTOR_KEYWORDS
        ) and not self._contains_any(normalized_text, DOCUMENT_KEYWORDS)

        # 检测用户具体资源需求
        wants_full = self._contains_any(normalized_text, FULL_RESOURCE_VERBS)
        has_ppt = "ppt" in normalized_text.lower()
        has_quiz = self._contains_any(normalized_text, QUIZ_ONLY_KEYWORDS)
        has_mindmap = self._contains_any(normalized_text, MINDMAP_KEYWORDS)
        has_animation = self._contains_any(normalized_text, ANIMATION_KEYWORDS)

        quiz_only = False
        if not wants_full:
            if has_quiz:
                quiz_only = True
            elif has_ppt or has_mindmap or has_animation:
                quiz_only = True

        generate_document = self._contains_any(
            normalized_text,
            DOCUMENT_KEYWORDS,
        ) or (not is_tutor and self._is_learning_request(normalized_text))
        topic = self._extract_topic(normalized_text)

        resource_types: list[str] = []
        if generate_document:
            if quiz_only:
                if has_ppt:
                    resource_types = ["ppt"]
                elif has_mindmap:
                    resource_types = ["mindmap"]
                elif has_animation:
                    resource_types = ["animation"]
                else:
                    resource_types = ["quiz"]
            else:
                resource_types = list(DEFAULT_RESOURCE_TYPES)
                if self._contains_any(normalized_text, PPT_KEYWORDS):
                    resource_types.append("ppt")
                if self._contains_any(normalized_text, ANIMATION_KEYWORDS):
                    resource_types.append("animation")

        return RouteDecision(
            update_profile=update_profile,
            generate_document=generate_document,
            is_tutor_question=is_tutor,
            topic=topic,
            resource_types=resource_types,
            quiz_only=quiz_only or ppt_only,  # 纯出题或纯PPT都不强制加 document
        )

    def _contains_any(self, text: str, keywords: tuple[str, ...]) -> bool:
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)

    def _is_learning_request(self, text: str) -> bool:
        return bool(text) and len(text) > 2

    def _extract_topic(self, text: str) -> str:
        cleaned_text = self._strip_prefixes(text)

        for pattern in TOPIC_PATTERNS:
            match = pattern.search(cleaned_text)
            if match:
                topic = match.group("topic").strip("，。！？、 ")
                if topic:
                    return topic

        fallback = re.split(r"[，。！？?！]", cleaned_text, maxsplit=1)[0].strip()
        return fallback or text.strip()

    def _strip_prefixes(self, text: str) -> str:
        cleaned_text = text
        for prefix in TOPIC_PREFIXES:
            if cleaned_text.startswith(prefix):
                cleaned_text = cleaned_text.removeprefix(prefix).strip()
        return cleaned_text
