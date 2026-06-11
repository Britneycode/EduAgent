from __future__ import annotations

import asyncio
import json
from urllib.parse import parse_qs

import httpx
import pytest

from app.core.config import Settings
from app.core.xunfei_safety import XunfeiSafetyClient, XunfeiSafetyError


def _settings() -> Settings:
    return Settings(
        xunfei_safety_enabled=True,
        xunfei_safety_app_id="app-id",
        xunfei_safety_access_key_id="access-key-id",
        xunfei_safety_access_key_secret="access-key-secret",
        xunfei_safety_api_base_url="http://safety.test",
    )


def test_xunfei_safety_client_sends_signed_input_request() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        captured["path"] = request.url.path
        captured["query"] = parse_qs(request.url.query.decode("utf-8"))
        captured["body"] = body
        captured["trace_id"] = request.headers.get("x-traceid")
        return httpx.Response(
            200,
            json={
                "code": "000000",
                "data": {
                    "action": "fortify_prompt",
                    "action_detail": {"append_prompt": "请保持教学安全边界。"},
                    "sid": "safety-session",
                },
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = XunfeiSafetyClient(settings=_settings(), http_client=http)
            result = await client.audit_input("帮我学习反向传播", chat_sid="chat-1")

        assert result.action == "fortify_prompt"
        assert result.append_prompt == "请保持教学安全边界。"
        assert result.sid == "safety-session"

    asyncio.run(run())

    assert captured["path"] == "/audit/v3/aichat/input"
    query = captured["query"]
    assert query["appId"] == ["app-id"]
    assert query["accessKeyId"] == ["access-key-id"]
    assert query["signature"][0]
    body = captured["body"]
    assert body["content"] == "帮我学习反向传播"
    assert body["chat_sid"] == "chat-1"
    assert captured["trace_id"] == body["trace_id"]


def test_xunfei_safety_client_raises_chinese_error_on_api_failure() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": "100001", "message": "invalid signature"},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = XunfeiSafetyClient(settings=_settings(), http_client=http)
            with pytest.raises(XunfeiSafetyError, match="错误码 100001"):
                await client.audit_output(
                    "模型输出内容",
                    chat_sid="chat-1",
                    pindex=1,
                    is_end=True,
                )

    asyncio.run(run())
