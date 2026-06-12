from __future__ import annotations

import logging
from typing import Any, Protocol

from app.agents.resource_types import AgentResource
from app.core.video_search import (
    VideoSearchConfigurationError,
    VideoSearchError,
    VideoSearchResult,
    get_video_search_client,
)

logger = logging.getLogger(__name__)


class VideoSearchClient(Protocol):
    async def search(self, query: str) -> list[VideoSearchResult]:
        ...


class VideoAgent:
    """相关视频 Agent — 联网检索 B站学习视频。"""

    def __init__(self, search_client: VideoSearchClient | None = None) -> None:
        self.search_client = search_client if search_client is not None else get_video_search_client()

    async def generate_videos(
        self,
        topic: str,
        profile: dict[str, Any] | None = None,
        document_content: str | None = None,
        course_id: str | None = None,
    ) -> AgentResource:
        normalized_topic = topic.strip() if topic else "当前学习主题"
        if self.search_client is None:
            return self._unavailable_resource(
                normalized_topic,
                "视频搜索未启用或搜索提供方不可用",
            )

        query = self._build_query(
            normalized_topic,
            profile or {},
            document_content=document_content,
            course_id=course_id,
        )
        try:
            results = await self.search_client.search(query)
        except VideoSearchConfigurationError as exc:
            return self._unavailable_resource(normalized_topic, str(exc))
        except VideoSearchError as exc:
            logger.warning("视频搜索失败: %s", exc)
            return self._unavailable_resource(normalized_topic, str(exc))

        if not results:
            return AgentResource(
                title=f"{normalized_topic}相关视频",
                resource_type="video",
                content=(
                    f"# {normalized_topic}相关视频\n\n"
                    "暂未在 B站检索到足够匹配的公开视频。你可以稍后重试，"
                    "或换一个更具体的知识点关键词。"
                ),
                knowledge_point=normalized_topic,
                agent_name="VideoAgent",
                confidence=0.0,
                metadata={"video_search_status": "empty", "query": query},
            )

        return AgentResource(
            title=f"{normalized_topic}相关视频",
            resource_type="video",
            content=self._format_results(normalized_topic, results),
            knowledge_point=normalized_topic,
            agent_name="VideoAgent",
            confidence=1.0,
            metadata={
                "video_search_status": "success",
                "query": query,
                "result_count": len(results),
            },
        )

    def _build_query(
        self,
        topic: str,
        profile: dict[str, Any],
        *,
        document_content: str | None,
        course_id: str | None,
    ) -> str:
        hints: list[str] = [topic, "教程", "学习", "讲解"]
        learning_goal = profile.get("learning_goal")
        if learning_goal:
            hints.append(str(learning_goal))
        if course_id:
            hints.append(str(course_id))
        if document_content:
            first_line = next(
                (line.strip("# 　\t") for line in document_content.splitlines() if line.strip()),
                "",
            )
            if first_line:
                hints.append(first_line[:40])
        return " ".join(dict.fromkeys(hints))

    def _format_results(
        self,
        topic: str,
        results: list[VideoSearchResult],
    ) -> str:
        lines = [
            f"# {topic}相关视频",
            "",
            "以下结果来自 B站公开搜索结果，适合配合当前知识点继续学习：",
            "",
        ]
        for index, result in enumerate(results, start=1):
            snippet = result.snippet or "该视频标题与当前学习主题相关，可作为补充学习材料。"
            lines.extend(
                [
                    f"{index}. [{result.title}]({result.url})",
                    "   - 平台：B站",
                    f"   - 推荐理由：与「{topic}」的学习需求相关，适合作为补充讲解视频。",
                    f"   - 摘要：{snippet}",
                    "",
                ]
            )
        return "\n".join(lines).strip()

    def _unavailable_resource(self, topic: str, reason: str) -> AgentResource:
        return AgentResource(
            title=f"{topic}相关视频",
            resource_type="video",
            content=(
                f"# {topic}相关视频\n\n"
                "视频搜索暂不可用，暂时无法联网检索 B站学习视频。\n\n"
                f"- 原因：{reason}\n"
                "- 处理建议：配置 Tavily API Key 后重试，或稍后重新生成该资源。"
            ),
            knowledge_point=topic,
            agent_name="VideoAgent",
            confidence=0.0,
            metadata={
                "video_search_status": "error",
                "error": reason,
            },
        )
