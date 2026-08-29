from __future__ import annotations

import asyncio

import httpx
import pytest

from app.agents.doc_agent import DocAgent
from app.core.llm import BaseLLMClient, DeepSeekLLMClient, LLMClientError


class StubLLMClient(BaseLLMClient):
    async def generate_text(self, prompt: str) -> str:
        assert "反向传播" in prompt
        assert "图文结合" in prompt
        assert "复习" in prompt
        return "反向传播学习讲义\n\n一、核心概念\n反向传播用于高效计算梯度，适合图文结合方式复习。"


ASYNC_PROFILE = {
    "major": "计算机专业",
    "grade": "大三",
    "cognitive_style": "图文结合",
    "learning_goal": "复习",
    "knowledge_base": {"机器学习": "一般"},
    "learning_pace": "平稳",
}


def test_doc_agent_generates_personalized_document() -> None:
    agent = DocAgent(llm_client=StubLLMClient())

    document = asyncio.run(agent.generate_document("反向传播", ASYNC_PROFILE))

    assert document.title == "反向传播个性化学习讲义"
    assert document.resource_type == "document"
    assert document.knowledge_point == "反向传播"
    assert document.agent_name == "DocAgent"
    assert "反向传播" in document.content
    assert "图文结合" in document.content


def test_doc_agent_builds_chinese_prompt_with_profile_context() -> None:
    agent = DocAgent(llm_client=StubLLMClient())

    prompt = agent.build_prompt("反向传播", ASYNC_PROFILE)

    assert "请输出一份中文学习讲义" in prompt
    assert "主题：反向传播" in prompt
    assert "认知风格：图文结合" in prompt
    assert "学习目标：复习" in prompt
    assert "知识基础：机器学习（一般）" in prompt
    assert "不要输出英文小节标题" in prompt


def test_deepseek_client_raises_chinese_error_when_credentials_missing() -> None:
    client = DeepSeekLLMClient()
    client.api_key = ""

    with pytest.raises(LLMClientError, match="DEEPSEEK_API_KEY"):
        asyncio.run(client.generate_text("请生成一段中文讲义"))
