from __future__ import annotations

import asyncio

import httpx
import pytest

from app.agents.doc_agent import DocAgent
from app.core.llm import BaseLLMClient, LLMClientError, SparkLLMClient


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


def test_spark_client_raises_chinese_error_when_credentials_missing() -> None:
    client = SparkLLMClient()
    client.app_id = None
    client.api_key = None
    client.api_secret = None
    client.api_password = None

    with pytest.raises(LLMClientError, match="讯飞星火凭证未配置"):
        asyncio.run(client.generate_text("请生成一段中文讲义"))


def test_spark_client_reports_appid_auth_error_clearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = SparkLLMClient()
    client.app_id = "test-app-id"
    client.api_key = "test-api-key"
    client.api_secret = "test-api-secret"
    client.api_password = "test-api-password"

    async def fake_stream(*args: object, **kwargs: object):
        raise httpx.HTTPStatusError(
            "Server Error",
            request=httpx.Request("POST", client.api_url),
            response=httpx.Response(
                status_code=500,
                request=httpx.Request("POST", client.api_url),
                json={
                    "error": {
                        "message": "AppIdNoAuthError",
                        "code": "11200",
                    }
                },
            ),
        )
        yield  # noqa: B018

    monkeypatch.setattr(client, "_iter_stream_tokens", fake_stream)

    with pytest.raises(LLMClientError, match="AppID"):
        asyncio.run(client.generate_text("请生成一段中文讲义"))


def test_spark_client_uses_api_password_header_and_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = SparkLLMClient()
    client.app_id = "test-app-id"
    client.api_key = "test-api-key"
    client.api_secret = "unused-secret"
    client.api_password = "test-api-password"
    client.model = "lite"

    captured: dict[str, object] = {}

    async def fake_stream(headers: dict[str, str], payload: dict):
        captured["headers"] = headers
        captured["payload"] = payload
        yield "测试成功"

    monkeypatch.setattr(client, "_iter_stream_tokens", fake_stream)

    result = asyncio.run(client.generate_text("请生成一段中文讲义"))

    assert result == "测试成功"
    assert captured["headers"] == {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-api-password",
    }
    payload = captured["payload"]
    assert payload["model"] == "lite"
    assert payload["stream"] is True
    assert payload["messages"] == [{"role": "user", "content": "请生成一段中文讲义"}]
