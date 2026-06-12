from __future__ import annotations

import pytest

from app.agents.video_agent import VideoAgent
from app.core.video_search import (
    VideoSearchConfigurationError,
    VideoSearchError,
    VideoSearchResult,
)


class StubVideoSearchClient:
    def __init__(
        self,
        results: list[VideoSearchResult] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.results = results or []
        self.error = error
        self.queries: list[str] = []

    async def search(self, query: str) -> list[VideoSearchResult]:
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return self.results


@pytest.mark.asyncio
async def test_video_agent_formats_bilibili_results() -> None:
    search_client = StubVideoSearchClient(
        [
            VideoSearchResult(
                title="反向传播从零讲解",
                url="https://www.bilibili.com/video/BV123",
                snippet="链式法则和梯度计算入门。",
                score=0.9,
            )
        ]
    )
    agent = VideoAgent(search_client=search_client)

    resource = await agent.generate_videos("反向传播", {"learning_goal": "期末复习"})

    assert resource.resource_type == "video"
    assert resource.agent_name == "VideoAgent"
    assert "反向传播从零讲解" in resource.content
    assert "https://www.bilibili.com/video/BV123" in resource.content
    assert "平台：B站" in resource.content
    assert resource.metadata["video_search_status"] == "success"
    assert "期末复习" in search_client.queries[0]


@pytest.mark.asyncio
async def test_video_agent_returns_empty_result_card() -> None:
    agent = VideoAgent(search_client=StubVideoSearchClient([]))

    resource = await agent.generate_videos("卷积神经网络")

    assert resource.resource_type == "video"
    assert "暂未在 B站检索到" in resource.content
    assert resource.metadata["video_search_status"] == "empty"


@pytest.mark.asyncio
async def test_video_agent_returns_unavailable_card_for_missing_configuration() -> None:
    agent = VideoAgent(
        search_client=StubVideoSearchClient(
            error=VideoSearchConfigurationError("Tavily API Key 未配置")
        )
    )

    resource = await agent.generate_videos("反向传播")

    assert "视频搜索暂不可用" in resource.content
    assert "Tavily API Key 未配置" in resource.content
    assert resource.metadata["video_search_status"] == "error"


@pytest.mark.asyncio
async def test_video_agent_returns_unavailable_card_for_upstream_error() -> None:
    agent = VideoAgent(
        search_client=StubVideoSearchClient(error=VideoSearchError("请求过于频繁"))
    )

    resource = await agent.generate_videos("反向传播")

    assert "视频搜索暂不可用" in resource.content
    assert "请求过于频繁" in resource.content
    assert resource.metadata["video_search_status"] == "error"
