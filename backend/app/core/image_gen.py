"""图片生成客户端 — 基于阿里百炼 DashScope 异步文生图 API。"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# PPT 风格图片的系统提示词后缀
PPT_STYLE_SUFFIX = """请根据上述知识点内容，生成一张横版 16:9 的专业 PPT 风格知识总结图片。请准确提炼文字中的核心知识点，并以清晰的层级结构呈现，包括主标题、核心观点、关键要点、逻辑关系和总结模块。PPT 主题风格指定为「蓝白科技商务风」：以白色和浅灰色为背景，搭配深蓝、科技蓝作为主色，辅以少量青色高光，整体简洁、理性、专业。页面采用现代商务 PPT 排版，可使用标题栏、卡片式模块、分栏布局、流程图、信息图标、细线条、几何光效和数据化装饰元素。文字需清晰易读，重点内容用色块、加粗或图标突出，避免拥挤杂乱。图片中必须准确包含主要知识点，不要编造无关内容。整体效果应像一页完成度高、可直接用于商务汇报、课程讲解或知识分享的专业 PPT 页面。"""


class ImageGenError(RuntimeError):
    """图片生成业务异常。"""


class ImageGenClient:
    """DashScope 异步文生图客户端。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.dashscope_api_key
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
        self.model = "qwen-image-plus"
        self.max_poll_seconds = 120
        self.poll_interval_seconds = 2

    async def generate_image(
        self, prompt: str, size: str = "1664*928"
    ) -> dict[str, Any]:
        """生成一张图片，返回包含 url 的字典。"""
        self._validate()

        final_prompt = f"{prompt}\n\n{PPT_STYLE_SUFFIX}"

        task_id = await self._create_task(final_prompt, size)
        result = await self._poll_task(task_id)
        return result

    async def generate_images(
        self, prompts: list[str], size: str = "1664*928"
    ) -> list[dict[str, Any]]:
        """顺序生成多张图片（带重试和限流控制）。"""
        if not prompts:
            return []

        images: list[dict[str, Any]] = []
        for i, prompt in enumerate(prompts):
            if i > 0:
                # 请求间隔 3 秒避免限流
                await asyncio.sleep(3)
            # 最多重试 2 次
            for attempt in range(3):
                try:
                    result = await self.generate_image(prompt, size)
                    images.append({"index": i, **result})
                    break
                except ImageGenError as exc:
                    if "429" in str(exc) and attempt < 2:
                        wait = (attempt + 1) * 10
                        logger.warning(
                            "第 %d 张图片遇到限流，%d 秒后重试 (第 %d 次)",
                            i + 1, wait, attempt + 1,
                        )
                        await asyncio.sleep(wait)
                    else:
                        logger.warning("第 %d 张图片生成失败: %s", i + 1, exc)
                        images.append({"index": i, "error": str(exc)})
                        break
        return images

    async def _create_task(self, prompt: str, size: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-DashScope-Async": "enable",
        }
        payload = {
            "model": self.model,
            "input": {"prompt": prompt},
            "parameters": {"size": size, "n": 1},
        }

        timeout = httpx.Timeout(connect=10, read=30, write=10, pool=10)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    self.base_url, headers=headers, json=payload
                )
            except httpx.TimeoutException as exc:
                raise ImageGenError("图片生成请求超时，请稍后重试") from exc
            except httpx.HTTPError as exc:
                raise ImageGenError(f"图片生成网络异常: {exc}") from exc

        if response.status_code != 200:
            error_data = self._safe_json(response)
            raise ImageGenError(
                f"图片生成请求失败 (HTTP {response.status_code}): "
                f"{error_data.get('message', response.text[:200])}"
            )

        data = response.json()
        task_id = data.get("output", {}).get("task_id", "")
        if not task_id:
            raise ImageGenError(f"未获取到任务 ID: {data}")

        return task_id

    async def _poll_task(self, task_id: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        deadline = time.perf_counter() + self.max_poll_seconds

        timeout = httpx.Timeout(connect=10, read=15, write=10, pool=10)
        async with httpx.AsyncClient(timeout=timeout) as client:
            while time.perf_counter() < deadline:
                await asyncio.sleep(self.poll_interval_seconds)

                try:
                    response = await client.get(
                        f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
                        headers=headers,
                    )
                except httpx.HTTPError as exc:
                    logger.warning("轮询任务 %s 网络异常: %s", task_id, exc)
                    continue

                if response.status_code != 200:
                    continue

                data = response.json()
                output = data.get("output", {})
                status = output.get("task_status", "")

                if status == "SUCCEEDED":
                    results = output.get("results", [])
                    if results:
                        return {
                            "url": results[0].get("url", ""),
                            "task_id": task_id,
                        }
                    raise ImageGenError("图片生成成功但未返回图片 URL")

                if status == "FAILED":
                    raise ImageGenError(
                        f"图片生成任务失败: {output.get('message', '未知错误')}"
                    )

        raise ImageGenError(f"图片生成任务 {task_id} 超时未完成")

    def _validate(self) -> None:
        if not self.api_key:
            raise ImageGenError("未配置 DASHSCOPE_API_KEY，无法生成图片")

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict[str, Any]:
        try:
            return response.json()
        except ValueError:
            return {}
