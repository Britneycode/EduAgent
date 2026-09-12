"""mindmap_render 单元测试 — 全部通过 MockTransport 注入，禁止真实网络。"""

from __future__ import annotations

import base64

import httpx
import pytest

from app.core.mindmap_render import extract_mermaid_block, render_mindmap_image

FAKE_PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-png-content"

SAMPLE_MERMAID = "mindmap\n  root((计算机网络))\n    OSI七层模型\n    TCP与UDP"

DATA_URL_PREFIX = "data:image/png;base64,"


def _decode_data_url(data_url: str) -> bytes:
    """断言 data URL 前缀并解码出原始 PNG 字节。"""
    assert data_url.startswith(DATA_URL_PREFIX)
    return base64.b64decode(data_url[len(DATA_URL_PREFIX) :])


def test_extract_mermaid_block_from_fenced_block() -> None:
    content = f"开头说明\n\n```mermaid\n{SAMPLE_MERMAID}\n```\n\n结尾说明"

    assert extract_mermaid_block(content) == SAMPLE_MERMAID


def test_extract_mermaid_block_accepts_bare_mindmap_source() -> None:
    content = f"\n  {SAMPLE_MERMAID}\n"

    assert extract_mermaid_block(content) == SAMPLE_MERMAID


def test_extract_mermaid_block_returns_empty_without_mermaid() -> None:
    assert extract_mermaid_block("普通文字回答，不含任何导图") == ""
    assert extract_mermaid_block("```python\nprint('hello')\n```") == ""


def test_extract_mermaid_block_returns_first_of_multiple_blocks() -> None:
    content = (
        "```mermaid\nmindmap\n  第一张图\n```\n中间文本\n"
        "```mermaid\nmindmap\n  第二张图\n```"
    )

    assert extract_mermaid_block(content) == "mindmap\n  第一张图"


@pytest.mark.asyncio
async def test_render_prefers_kroki_post_and_returns_data_url() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = request.content
        captured["content_type"] = request.headers.get("Content-Type")
        return httpx.Response(200, content=FAKE_PNG_BYTES)

    result = await render_mindmap_image(
        SAMPLE_MERMAID, transport=httpx.MockTransport(handler)
    )

    assert _decode_data_url(result) == FAKE_PNG_BYTES
    assert captured["method"] == "POST"
    assert captured["url"] == "https://kroki.io/mermaid/png"
    assert captured["body"] == SAMPLE_MERMAID.encode("utf-8")
    assert captured["content_type"] == "text/plain"


@pytest.mark.asyncio
async def test_render_falls_back_to_mermaid_ink_when_kroki_fails() -> None:
    kroki_requests: list[httpx.Request] = []
    ink_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            kroki_requests.append(request)
            return httpx.Response(500, text="kroki unavailable")
        ink_requests.append(request)
        return httpx.Response(200, content=FAKE_PNG_BYTES)

    result = await render_mindmap_image(
        SAMPLE_MERMAID, transport=httpx.MockTransport(handler)
    )

    assert _decode_data_url(result) == FAKE_PNG_BYTES
    assert len(kroki_requests) == 1
    assert len(ink_requests) == 1
    ink_request = ink_requests[0]
    expected_token = (
        base64.urlsafe_b64encode(SAMPLE_MERMAID.encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    assert ink_request.method == "GET"
    assert str(ink_request.url) == (
        f"https://mermaid.ink/img/{expected_token}?type=png"
    )


@pytest.mark.asyncio
async def test_render_returns_empty_when_both_services_fail() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(500, text="service unavailable")

    result = await render_mindmap_image(
        SAMPLE_MERMAID, transport=httpx.MockTransport(handler)
    )

    assert result == ""
    assert [request.method for request in requests] == ["POST", "GET"]


@pytest.mark.asyncio
async def test_render_treats_empty_png_body_as_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"")

    result = await render_mindmap_image(
        SAMPLE_MERMAID, transport=httpx.MockTransport(handler)
    )

    assert result == ""


@pytest.mark.asyncio
async def test_render_swallows_network_errors_without_raising() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("连接被拒绝")

    result = await render_mindmap_image(
        SAMPLE_MERMAID, transport=httpx.MockTransport(handler)
    )

    assert result == ""
