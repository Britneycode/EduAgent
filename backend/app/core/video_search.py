from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from app.core.cache import get_cache_backend, make_cache_key
from app.core.config import get_settings


class VideoSearchError(RuntimeError):
    """视频搜索失败。"""


class VideoSearchConfigurationError(VideoSearchError):
    """视频搜索配置不可用。"""


@dataclass(slots=True)
class VideoSearchResult:
    title: str
    url: str
    snippet: str
    score: float | None = None


class TavilyVideoSearchClient:
    """基于 Tavily 的 B 站视频搜索客户端。"""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_base_url: str | None = None,
        domains: list[str] | None = None,
        max_results: int | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.tavily_api_key
        self.api_base_url = (
            api_base_url if api_base_url is not None else settings.tavily_api_base_url
        )
        self.domains = domains if domains is not None else settings.video_search_domains
        self.max_results = (
            max_results if max_results is not None else settings.video_search_max_results
        )
        self._http_client = http_client

    async def search(self, query: str) -> list[VideoSearchResult]:
        self._validate_configuration()
        cache = get_cache_backend()
        cache_key = make_cache_key(
            "video_search",
            query,
            self.domains,
            self.max_results,
            self.api_base_url,
        )
        try:
            cached = await cache.get(cache_key)
            if cached:
                return [
                    VideoSearchResult(**item)
                    for item in json.loads(cached)
                    if isinstance(item, dict)
                ]
        except Exception:
            pass

        payload = {
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
            "include_domains": self.domains,
            "max_results": self.max_results,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            if self._http_client is not None:
                response = await self._http_client.post(
                    self._search_url(),
                    headers=headers,
                    json=payload,
                    timeout=self._timeout(),
                )
            else:
                async with httpx.AsyncClient(timeout=self._timeout()) as client:
                    response = await client.post(
                        self._search_url(),
                        headers=headers,
                        json=payload,
                    )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise VideoSearchError("视频搜索请求超时，请稍后重试") from exc
        except httpx.HTTPStatusError as exc:
            raise VideoSearchError(self._build_http_error_message(exc)) from exc
        except httpx.HTTPError as exc:
            raise VideoSearchError("视频搜索网络连接失败，请检查网络") from exc

        results = self._parse_results(response.json())
        try:
            await cache.set(
                cache_key,
                json.dumps(
                    [asdict(result) for result in results],
                    ensure_ascii=False,
                ),
                ttl_seconds=get_settings().cache_ttl_seconds,
            )
        except Exception:
            pass
        return results

    def _validate_configuration(self) -> None:
        if not self.api_key:
            raise VideoSearchConfigurationError("Tavily API Key 未配置，无法联网搜索视频")
        if not self.domains:
            raise VideoSearchConfigurationError("视频搜索域名未配置")
        if self.max_results <= 0:
            raise VideoSearchConfigurationError("视频搜索结果数量必须大于 0")

    def _search_url(self) -> str:
        return f"{self.api_base_url.rstrip('/')}/search"

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)

    def _parse_results(self, payload: dict[str, Any]) -> list[VideoSearchResult]:
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            return []

        seen_urls: set[str] = set()
        parsed_results: list[VideoSearchResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            raw_url = str(item.get("url") or "").strip()
            url = _canonical_bilibili_video_url(raw_url)
            if url is None or url in seen_urls:
                continue
            seen_urls.add(url)
            title = str(item.get("title") or "B站相关视频").strip()
            snippet = str(item.get("content") or item.get("snippet") or "").strip()
            score = _safe_float(item.get("score"))
            parsed_results.append(
                VideoSearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    score=score,
                )
            )
            if len(parsed_results) >= self.max_results:
                break

        return parsed_results

    def _build_http_error_message(self, exc: httpx.HTTPStatusError) -> str:
        status_code = exc.response.status_code
        if status_code in {401, 403}:
            return "Tavily 视频搜索鉴权失败，请检查 TAVILY_API_KEY"
        if status_code == 429:
            return "Tavily 视频搜索请求过于频繁或额度不足，请稍后重试"
        if 500 <= status_code < 600:
            return "Tavily 视频搜索服务暂时不可用，请稍后重试"
        return f"Tavily 视频搜索请求失败（HTTP {status_code}）"


def get_video_search_configuration_warning() -> str | None:
    settings = get_settings()
    if not settings.video_search_enabled:
        return "视频搜索未启用，相关视频资源会提示不可用"
    if settings.video_search_provider != "tavily":
        return f"不支持的视频搜索提供方：{settings.video_search_provider}"
    if not settings.tavily_api_key:
        return "TAVILY_API_KEY 未配置，无法联网搜索 B站相关视频"
    if not settings.video_search_domains:
        return "VIDEO_SEARCH_DOMAINS 未配置，无法限定视频搜索来源"
    return None


def get_video_search_client() -> TavilyVideoSearchClient | None:
    settings = get_settings()
    if not settings.video_search_enabled or settings.video_search_provider != "tavily":
        return None
    return TavilyVideoSearchClient()


def _canonical_bilibili_video_url(raw_url: str) -> str | None:
    if not raw_url:
        return None
    parsed = urlparse(raw_url)
    if not parsed.netloc:
        return None
    host = parsed.netloc.lower()
    if ":" in host:
        host = host.split(":", 1)[0]
    if host != "bilibili.com" and not host.endswith(".bilibili.com"):
        return None
    path = parsed.path.rstrip("/")
    if not (path.startswith("/video/") or path.startswith("/bangumi/play/")):
        return None
    scheme = parsed.scheme or "https"
    canonical_netloc = parsed.netloc.lower()
    return urlunparse((scheme, canonical_netloc, path, "", "", ""))


def _safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if numeric == numeric else None
