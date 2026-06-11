from __future__ import annotations

import asyncio

from app.agents.code_agent import CodeAgent
from app.core.llm import BaseLLMClient


class StubLLMClient(BaseLLMClient):
    async def generate_text(self, prompt: str) -> str:
        assert "反向传播" in prompt
        assert "图文结合" in prompt
        assert "复习" in prompt
        assert "上游学习讲义：" in prompt
        assert "上游练习题：" in prompt
        return "一、代码目标\n使用 Python 演示梯度计算。"


PROFILE = {
    "cognitive_style": "图文结合",
    "learning_goal": "复习",
    "coding_level": "一般",
    "knowledge_base": {"subject": "机器学习", "level": "一般"},
}


def test_code_agent_generates_code_resource() -> None:
    agent = CodeAgent(llm_client=StubLLMClient())

    resource = asyncio.run(
        agent.generate_code(
            "反向传播",
            PROFILE,
            document_content="这是上游讲义正文。",
            quiz_content="这是上游练习题。",
        )
    )

    assert resource.title == "反向传播代码实践"
    assert resource.resource_type == "code"
    assert resource.knowledge_point == "反向传播"
    assert resource.agent_name == "CodeAgent"
    assert "代码目标" in resource.content


def test_code_agent_builds_prompt_with_upstream_context() -> None:
    agent = CodeAgent(llm_client=StubLLMClient())

    prompt = agent.build_prompt(
        "反向传播",
        PROFILE,
        document_content="这是上游讲义正文。",
        quiz_content="这是上游练习题。",
    )

    assert "请围绕学习主题输出中文代码实践内容" in prompt
    assert "主题：反向传播" in prompt
    assert "上游学习讲义：" in prompt
    assert "上游练习题：" in prompt
    assert "图文结合" in prompt
    assert "复习" in prompt
