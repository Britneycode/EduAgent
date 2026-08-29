from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.core.config import get_settings
from app.core.llm import (
    BaseLLMClient,
    DeepSeekLLMClient,
    FallbackLLMClient,
    OpenAICompatibleLLMClient,
    get_llm_configuration_warning,
    get_llm_mode,
)


class StaticLLMClient(BaseLLMClient):
    def __init__(self, response: str) -> None:
        self.response = response

    async def generate_text(self, prompt: str) -> str:
        return self.response


class FailingLLMClient(BaseLLMClient):
    async def generate_text(self, prompt: str) -> str:
        raise RuntimeError("primary unavailable")


def test_deepseek_client_sends_openai_compatible_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")
    monkeypatch.setenv("DEEPSEEK_API_BASE_URL", "https://deepseek.test")
    get_settings.cache_clear()
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "备用模型响应"}}]},
        )

    async def run() -> str:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = DeepSeekLLMClient(http_client=http)
            return await client.generate_text("请生成学习讲义")

    try:
        result = asyncio.run(run())
    finally:
        get_settings.cache_clear()

    assert result == "备用模型响应"
    assert captured["url"] == "https://deepseek.test/chat/completions"
    assert captured["authorization"] == "Bearer deepseek-key"
    assert captured["body"] == {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "请生成学习讲义"}],
        "max_tokens": 4096,
        "temperature": 0.7,
        "stream": False,
    }


def test_openai_compatible_client_sends_optional_thinking_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "dashscope-key")
    monkeypatch.setenv(
        "OPENAI_COMPATIBLE_API_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    monkeypatch.setenv("OPENAI_COMPATIBLE_MODEL", "qwen3.6-plus")
    monkeypatch.setenv("OPENAI_COMPATIBLE_ENABLE_THINKING", "false")
    get_settings.cache_clear()
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "百炼模型响应"}}]},
        )

    async def run() -> str:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = OpenAICompatibleLLMClient(http_client=http)
            return await client.generate_text("请生成学习讲义")

    try:
        result = asyncio.run(run())
    finally:
        get_settings.cache_clear()

    assert result == "百炼模型响应"
    assert (
        captured["url"]
        == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    )
    assert captured["authorization"] == "Bearer dashscope-key"
    assert captured["body"] == {
        "model": "qwen3.6-plus",
        "messages": [{"role": "user", "content": "请生成学习讲义"}],
        "max_tokens": 4096,
        "temperature": 0.7,
        "stream": False,
        "enable_thinking": False,
    }


def test_fallback_llm_uses_backup_when_primary_fails() -> None:
    client = FallbackLLMClient(
        primary=FailingLLMClient(),
        fallback=StaticLLMClient("DeepSeek 兜底成功"),
    )

    result = asyncio.run(client.generate_text("请讲解反向传播"))

    assert result == "DeepSeek 兜底成功"


def test_llm_warning_is_suppressed_when_deepseek_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_ENABLED", "true")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    get_settings.cache_clear()

    try:
        assert get_llm_configuration_warning() is None
    finally:
        get_settings.cache_clear()


def test_llm_mode_reports_dev_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_DEV_MODE", "true")
    get_settings.cache_clear()

    try:
        assert get_llm_mode() == "dev"
    finally:
        get_settings.cache_clear()


def test_llm_mode_reports_deepseek_when_deepseek_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_DEV_MODE", "false")
    monkeypatch.setenv("OPENAI_COMPATIBLE_ENABLED", "false")
    monkeypatch.setenv("DEEPSEEK_ENABLED", "true")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    get_settings.cache_clear()

    try:
        assert get_llm_mode() == "deepseek"
    finally:
        get_settings.cache_clear()


def test_llm_mode_reports_openai_compatible_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_DEV_MODE", "false")
    monkeypatch.setenv("DEEPSEEK_ENABLED", "false")
    monkeypatch.setenv("OPENAI_COMPATIBLE_ENABLED", "true")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "compat-key")
    get_settings.cache_clear()

    try:
        assert get_llm_mode() == "openai_compatible"
    finally:
        get_settings.cache_clear()
