from __future__ import annotations

import httpx
import pytest

from app.core.video_search import (
    TavilyVideoSearchClient,
    VideoSearchConfigurationError,
    VideoSearchError,
)


class FakeHTTPClient:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.requests: list[dict] = []

    async def post(self, url: str, **kwargs):
        self.requests.append({"url": url, **kwargs})
        return self.response


def _response(status_code: int, payload: dict) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        request=httpx.Request("POST", "https://api.tavily.com/search"),
    )


@pytest.mark.asyncio
async def test_tavily_video_search_filters_and_deduplicates_bilibili_results() -> None:
    fake_http = FakeHTTPClient(
        _response(
            200,
            {
                "results": [
                    {
                        "title": "反向传播教程",
                        "url": "https://www.bilibili.com/video/BV123/?spm_id=abc",
                        "content": "从链式法则讲反向传播。",
                        "score": 0.91,
                    },
                    {
                        "title": "重复结果",
                        "url": "https://www.bilibili.com/video/BV123/",
                        "content": "重复链接应去重。",
                    },
                    {
                        "title": "非视频页面",
                        "url": "https://www.bilibili.com/read/cv123",
                        "content": "不是视频页。",
                    },
                    {
                        "title": "外站视频",
                        "url": "https://youtube.com/watch?v=abc",
                        "content": "外站结果应过滤。",
                    },
                    {
                        "title": "番剧课程",
                        "url": "https://www.bilibili.com/bangumi/play/ep123",
                        "content": "番剧播放页允许保留。",
                        "score": 0.8,
                    },
                ]
            },
        )
    )
    client = TavilyVideoSearchClient(
        api_key="test-key",
        domains=["bilibili.com"],
        max_results=5,
        http_client=fake_http,  # type: ignore[arg-type]
    )

    results = await client.search("反向传播 教程")

    assert [result.title for result in results] == ["反向传播教程", "番剧课程"]
    assert results[0].url == "https://www.bilibili.com/video/BV123"
    request = fake_http.requests[0]
    assert request["url"] == "https://api.tavily.com/search"
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert request["json"]["include_domains"] == ["bilibili.com"]
    assert request["json"]["search_depth"] == "basic"
    assert request["json"]["include_answer"] is False
    assert request["json"]["include_raw_content"] is False


@pytest.mark.asyncio
async def test_tavily_video_search_requires_api_key() -> None:
    client = TavilyVideoSearchClient(api_key="", domains=["bilibili.com"])

    with pytest.raises(VideoSearchConfigurationError, match="API Key"):
        await client.search("反向传播")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "message"),
    [
        (401, "鉴权失败"),
        (429, "请求过于频繁"),
        (503, "暂时不可用"),
    ],
)
async def test_tavily_video_search_reports_upstream_errors(
    status_code: int,
    message: str,
) -> None:
    client = TavilyVideoSearchClient(
        api_key="test-key",
        domains=["bilibili.com"],
        http_client=FakeHTTPClient(_response(status_code, {"error": "failed"})),  # type: ignore[arg-type]
    )

    with pytest.raises(VideoSearchError, match=message):
        await client.search("反向传播")
