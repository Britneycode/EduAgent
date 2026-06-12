"""语音识别客户端 — 基于阿里百炼 DashScope Paraformer 实时语音识别。"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SpeechRecognitionError(RuntimeError):
    """语音识别业务异常。"""


class SpeechRecognitionClient:
    """DashScope Paraformer 语音识别客户端。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.dashscope_api_key
        self.api_url = (
            "https://dashscope.aliyuncs.com/api/v1/services/audio/"
            "asr/paraformer-realtime-v2"
        )

    async def recognize(self, audio_data: bytes, audio_format: str = "wav") -> str:
        """将音频数据转为文字。"""
        self._validate()

        files = {"audio": ("recording.wav", audio_data, f"audio/{audio_format}")}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        timeout = httpx.Timeout(connect=10, read=60, write=30, pool=10)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    self.api_url, headers=headers, files=files
                )
            except httpx.TimeoutException as exc:
                raise SpeechRecognitionError("语音识别请求超时") from exc
            except httpx.HTTPError as exc:
                raise SpeechRecognitionError(f"语音识别网络异常: {exc}") from exc

        if response.status_code != 200:
            error_msg = self._safe_error(response)
            raise SpeechRecognitionError(
                f"语音识别失败 (HTTP {response.status_code}): {error_msg}"
            )

        data = response.json()
        output = data.get("output", {})
        text = output.get("text", "") or "".join(
            s.get("text", "")
            for s in output.get("sentences", [])
        )
        if not text.strip():
            raise SpeechRecognitionError("语音识别未返回有效文字，请重试")
        return text.strip()

    def _validate(self) -> None:
        if not self.api_key:
            raise SpeechRecognitionError("未配置 DASHSCOPE_API_KEY，无法进行语音识别")

    @staticmethod
    def _safe_error(response: httpx.Response) -> str:
        try:
            return response.json().get("message", response.text[:200])
        except ValueError:
            return response.text[:200]
