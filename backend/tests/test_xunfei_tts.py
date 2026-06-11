from __future__ import annotations

import asyncio
import base64

from app.core.xunfei_tts import (
    XunfeiTTSClient,
    XunfeiTTSConfig,
    normalize_tts_text,
    prepare_resource_tts_text,
    split_text_for_tts,
)


def _config() -> XunfeiTTSConfig:
    return XunfeiTTSConfig(
        app_id="app-id",
        api_key="api-key",
        api_secret="api-secret",
        url="wss://tts-api.xfyun.cn/v2/tts",
        voice="xiaoyan",
        speed=50,
        volume=50,
        pitch=50,
    )


def test_xunfei_tts_client_builds_signed_url_and_payload() -> None:
    captured: dict[str, object] = {}

    async def connector(signed_url: str, payload: dict) -> bytes:
        captured["signed_url"] = signed_url
        captured["payload"] = payload
        return b"audio-bytes"

    async def run() -> bytes:
        client = XunfeiTTSClient(config=_config(), connector=connector)
        return await client.synthesize("反向传播学习讲义")

    result = asyncio.run(run())

    assert result == b"audio-bytes"
    assert "authorization=" in captured["signed_url"]
    assert "host=tts-api.xfyun.cn" in captured["signed_url"]
    payload = captured["payload"]
    assert payload["common"] == {"app_id": "app-id"}
    assert payload["business"]["aue"] == "lame"
    assert payload["business"]["vcn"] == "xiaoyan"
    decoded = base64.b64decode(payload["data"]["text"]).decode("utf-8")
    assert decoded == "反向传播学习讲义"


def test_normalize_tts_text_strips_markdown_and_code_blocks() -> None:
    text = normalize_tts_text(
        "# 标题\n\n这是 **重点**。\n\n```python\nprint('hi')\n```\n\n[参考](https://example.com)"
    )

    assert "标题" in text
    assert "重点" in text
    assert "代码示例已省略" in text
    assert "https://example.com" not in text
    assert "```" not in text


def test_prepare_resource_tts_text_adds_resource_context() -> None:
    text = prepare_resource_tts_text(
        title="反向传播个性化学习讲义",
        content="正文内容",
        resource_type="document",
    )

    assert text.startswith("学习文档：反向传播个性化学习讲义")
    assert "正文内容" in text


def test_split_text_for_tts_respects_byte_limit() -> None:
    chunks = split_text_for_tts("知" * 4000)

    assert len(chunks) > 1
    assert all(len(chunk.encode("utf-8")) <= 7600 for chunk in chunks)
