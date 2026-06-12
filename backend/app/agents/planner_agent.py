from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.common import parse_json_object
from app.agents.resource_types import DEFAULT_RESOURCE_TYPES, SUPPORTED_RESOURCE_TYPES
from app.core.llm import BaseLLMClient
from app.agents.router_agent import RouteDecision

logger = logging.getLogger(__name__)

_PLANNER_PROMPT = """\
你是 EduAgent 的学习资源规划智能体。请根据路由结果、学习主题和学生画像，规划本轮要生成的资源类型。

学习主题：{topic}
路由建议资源：{route_resource_types}
是否纯出题模式：{quiz_only}
学生画像 JSON：{profile_json}

可选资源类型：
- document：系统讲义
- quiz：练习题
- code：代码实践
- mindmap：思维导图
- reading：拓展阅读
- ppt：教学演示
- animation：动画分镜
- video：相关视频

请只输出 JSON，不要输出其他内容：
{{
  "resource_types": ["quiz"],
  "reason": "简短说明规划依据"
}}

规划规则：
1. 如果纯出题模式（quiz_only=true），只输出 ["quiz"]，不要加 document。
2. 如果需要生成学习资料（quiz_only=false），document 必须保留。
3. 练习复习类请求通常保留 quiz、mindmap、reading。
4. 编程水平或代码实践相关画像明显时保留 code。
5. 图文结合、视觉型学习者可加入 ppt；明确要求动画脚本时加入 animation。
6. 明确要求找、搜、推荐、观看相关学习视频或 B站教程时加入 video。
7. 只能使用可选资源类型，最多 8 个。"""


class PlannerAgent:
    """学习资源规划 Agent。"""

    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client

    async def plan_resources_async(
        self,
        topic: str,
        profile: dict[str, Any] | None,
        route_decision: RouteDecision,
    ) -> list[str]:
        """优先使用 LLM 做资源规划，失败时回退确定性规则。"""
        if not route_decision.generate_document:
            return []
        # 单资源模式：直接返回路由决定，不调 LLM
        if route_decision.quiz_only:
            return self.plan_resources(topic, profile, route_decision)
        if self.llm_client is None:
            return self.plan_resources(topic, profile, route_decision)

        try:
            prompt = self._build_prompt(topic, profile or {}, route_decision)
            raw = await self.llm_client.generate_text(prompt)
            parsed = self._parse_llm_response(raw)
            planned = self._normalize_plan(
                parsed.get("resource_types"),
                route_decision=route_decision,
            )
            if planned:
                return planned
        except Exception:
            logger.warning("LLM 资源规划失败，回退规则规划", exc_info=True)

        return self.plan_resources(topic, profile, route_decision)

    def plan_resources(
        self,
        _topic: str,
        _profile: dict[str, Any] | None,
        route_decision: RouteDecision,
    ) -> list[str]:
        if not route_decision.generate_document:
            return []

        # 纯出题/纯PPT模式：按路由决定生成
        if route_decision.quiz_only:
            return list(route_decision.resource_types) if route_decision.resource_types else ["quiz"]

        planned: list[str] = []
        for resource_type in (*DEFAULT_RESOURCE_TYPES, *route_decision.resource_types):
            if resource_type not in SUPPORTED_RESOURCE_TYPES:
                continue
            if resource_type not in planned:
                planned.append(resource_type)
        return planned

    def _build_prompt(
        self,
        topic: str,
        profile: dict[str, Any],
        route_decision: RouteDecision,
    ) -> str:
        compact_profile = {
            key: value
            for key, value in profile.items()
            if value not in (None, "", [], {})
        }
        return _PLANNER_PROMPT.format(
            topic=topic or route_decision.topic,
            route_resource_types=json.dumps(
                route_decision.resource_types, ensure_ascii=False
            ),
            quiz_only="true" if route_decision.quiz_only else "false",
            profile_json=json.dumps(compact_profile, ensure_ascii=False),
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

        return parse_json_object(cleaned)

    def _normalize_plan(
        self,
        raw_resource_types: Any,
        *,
        route_decision: RouteDecision,
    ) -> list[str]:
        if not isinstance(raw_resource_types, list):
            return []

        planned: list[str] = []
        for resource_type in raw_resource_types:
            if not isinstance(resource_type, str):
                continue
            normalized = resource_type.strip()
            if normalized not in SUPPORTED_RESOURCE_TYPES:
                continue
            if normalized not in planned:
                planned.append(normalized)

        # 非纯出题模式才强制插入 document
        if not route_decision.quiz_only and "document" not in planned:
            planned.insert(0, "document")

        for explicit_type in route_decision.resource_types:
            if explicit_type in DEFAULT_RESOURCE_TYPES:
                continue
            if (
                explicit_type in SUPPORTED_RESOURCE_TYPES
                and explicit_type not in planned
            ):
                planned.append(explicit_type)

        return planned[: len(SUPPORTED_RESOURCE_TYPES)]
