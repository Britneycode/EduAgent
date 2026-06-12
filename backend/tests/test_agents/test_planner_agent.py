from __future__ import annotations

import pytest

from app.agents.planner_agent import PlannerAgent
from app.agents.router_agent import RouteDecision
from app.core.llm import BaseLLMClient


class StubLLMClient(BaseLLMClient):
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    async def generate_text(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


class ErrorLLMClient(BaseLLMClient):
    async def generate_text(self, prompt: str) -> str:
        raise RuntimeError("planner unavailable")


def test_planner_agent_returns_route_resource_types() -> None:
    agent = PlannerAgent()

    decision = RouteDecision(
        update_profile=True,
        generate_document=True,
        is_tutor_question=False,
        topic="反向传播",
        resource_types=["document", "quiz", "code"],
    )

    assert agent.plan_resources("反向传播", {"learning_goal": "复习"}, decision) == [
        "document",
        "quiz",
        "code",
        "mindmap",
        "reading",
    ]


@pytest.mark.asyncio
async def test_planner_agent_uses_llm_plan_and_keeps_explicit_route_types() -> None:
    llm = StubLLMClient(
        """
```json
{"resource_types": ["quiz", "mindmap", "ppt"], "reason": "视觉型学习者"}
```
"""
    )
    agent = PlannerAgent(llm_client=llm)
    decision = RouteDecision(
        update_profile=False,
        generate_document=True,
        is_tutor_question=False,
        topic="反向传播",
        resource_types=["animation"],
    )

    plan = await agent.plan_resources_async(
        "反向传播",
        {"cognitive_style": "图文结合", "coding_level": "入门"},
        decision,
    )

    assert plan == ["document", "quiz", "mindmap", "ppt", "animation"]
    assert "学生画像 JSON" in llm.prompts[0]


@pytest.mark.asyncio
async def test_planner_agent_falls_back_when_llm_fails() -> None:
    agent = PlannerAgent(llm_client=ErrorLLMClient())
    decision = RouteDecision(
        update_profile=False,
        generate_document=True,
        is_tutor_question=False,
        topic="反向传播",
        resource_types=["ppt"],
    )

    plan = await agent.plan_resources_async("反向传播", {}, decision)

    assert plan == ["document", "quiz", "code", "mindmap", "reading", "ppt"]


@pytest.mark.asyncio
async def test_planner_agent_keeps_explicit_video_resource_type() -> None:
    agent = PlannerAgent(
        llm_client=StubLLMClient(
            '{"resource_types": ["document", "quiz"], "reason": "需要视频"}'
        )
    )
    decision = RouteDecision(
        update_profile=False,
        generate_document=True,
        is_tutor_question=False,
        topic="反向传播",
        resource_types=["video"],
    )

    plan = await agent.plan_resources_async("反向传播", {}, decision)

    assert plan == ["document", "quiz", "video"]
