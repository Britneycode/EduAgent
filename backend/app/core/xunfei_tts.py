from __future__ import annotations

import asyncio
import base64
import email.utils
import hashlib
import hmac
import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode, urlparse

from app.core.config import Settings, get_settings

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

_MAX_CHUNK_BYTES = 7600
_MAX_TOTAL_CHARS = 12000


class XunfeiTTSError(RuntimeError):
    """讯飞在线语音合成业务异常。"""


@dataclass(slots=True)
class XunfeiTTSConfig:
    app_id: str
    api_key: str
    api_secret: str
    url: str
    voice: str
    speed: int
    volume: int
    pitch: int


class XunfeiTTSClient:
    """讯飞在线语音合成 WebAPI 客户端。"""

    def __init__(
        self,
        config: XunfeiTTSConfig | None = None,
        *,
        connector: "Callable[[str, dict[str, Any]], Awaitable[bytes]] | None" = None,
    ) -> None:
        self.config = config or _build_tts_config(get_settings())
        self._connector = connector

    async def synthesize(self, text: str) -> bytes:
        clean_text = normalize_tts_text(text)
        if not clean_text:
            raise XunfeiTTSError("语音合成文本为空")

        self._validate_credentials()
        audio_parts: list[bytes] = []
        for chunk in split_text_for_tts(clean_text):
            payload = self._build_payload(chunk)
            signed_url = self._build_signed_url()
            if self._connector is not None:
                audio = await self._connector(signed_url, payload)
            else:
                audio = await self._synthesize_once(signed_url, payload)
            if audio:
                audio_parts.append(audio)

        if not audio_parts:
            raise XunfeiTTSError("讯飞语音合成未返回音频数据")
        return b"".join(audio_parts)

    def _build_payload(self, text: str) -> dict[str, Any]:
        encoded_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        return {
            "common": {"app_id": self.config.app_id},
            "business": {
                "aue": "lame",
                "sfl": 1,
                "auf": "audio/L16;rate=16000",
                "vcn": self.config.voice,
                "speed": _clamp_voice_value(self.config.speed),
                "volume": _clamp_voice_value(self.config.volume),
                "pitch": _clamp_voice_value(self.config.pitch),
                "bgs": 0,
                "tte": "UTF8",
            },
            "data": {
                "status": 2,
                "text": encoded_text,
            },
        }

    def _build_signed_url(self) -> str:
        parsed = urlparse(self.config.url)
        host = parsed.netloc
        path = parsed.path or "/v2/tts"
        date = email.utils.formatdate(usegmt=True)
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        signature_sha = hmac.new(
            self.config.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        authorization_origin = (
            f'api_key="{self.config.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(
            authorization_origin.encode("utf-8")
        ).decode("utf-8")
        query = urlencode(
            {"authorization": authorization, "date": date, "host": host}
        )
        return f"{self.config.url}?{query}"

    async def _synthesize_once(self, signed_url: str, payload: dict[str, Any]) -> bytes:
        try:
            import websockets
        except ImportError as exc:
            raise XunfeiTTSError(
                "缺少 websockets 依赖，请安装后再使用讯飞 TTS"
            ) from exc

        audio = bytearray()
        try:
            async with websockets.connect(signed_url, open_timeout=10) as websocket:
                await websocket.send(json.dumps(payload, ensure_ascii=False))
                while True:
                    raw = await asyncio.wait_for(websocket.recv(), timeout=60)
                    message = json.loads(raw)
                    code = int(message.get("code", 0))
                    if code != 0:
                        raise XunfeiTTSError(
                            f"讯飞语音合成失败（错误码 {code}）："
                            f"{message.get('message', '未知错误')}"
                        )

                    data = message.get("data") or {}
                    chunk = data.get("audio")
                    if chunk:
                        audio.extend(base64.b64decode(chunk))
                    if int(data.get("status", 0)) == 2:
                        break
        except TimeoutError as exc:
            raise XunfeiTTSError("讯飞语音合成请求超时，请稍后重试") from exc
        except OSError as exc:
            raise XunfeiTTSError("讯飞语音合成网络连接失败，请检查网络") from exc
        except json.JSONDecodeError as exc:
            raise XunfeiTTSError("讯飞语音合成返回数据格式异常") from exc

        return bytes(audio)

    def _validate_credentials(self) -> None:
        if not (self.config.app_id and self.config.api_key and self.config.api_secret):
            raise XunfeiTTSError(
                "讯飞 TTS 凭证未配置，请设置 XUNFEI_TTS_APP_ID、"
                "XUNFEI_TTS_API_KEY 和 XUNFEI_TTS_API_SECRET"
            )


def normalize_tts_text(text: str) -> str:
    """把 Markdown/代码内容整理成适合朗读的纯文本。"""
    normalized = text or ""
    normalized = re.sub(r"```[\s\S]*?```", " 代码示例已省略。 ", normalized)
    normalized = re.sub(r"`([^`]+)`", r"\1", normalized)
    normalized = re.sub(r"!\[[^\]]*]\([^)]+\)", "", normalized)
    normalized = re.sub(r"\[([^\]]+)]\([^)]+\)", r"\1", normalized)
    normalized = re.sub(r"^#{1,6}\s*", "", normalized, flags=re.MULTILINE)
    normalized = re.sub(r"^\s*[-*+]\s+", "", normalized, flags=re.MULTILINE)
    normalized = re.sub(r"^\s*\d+[.)]\s+", "", normalized, flags=re.MULTILINE)
    normalized = re.sub(r"[*_~>|-]{2,}", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if len(normalized) > _MAX_TOTAL_CHARS:
        normalized = normalized[:_MAX_TOTAL_CHARS].rstrip() + "。后续内容已省略。"
    return normalized


def prepare_resource_tts_text(
    *,
    title: str,
    content: str,
    resource_type: str,
) -> str:
    type_label = {
        "document": "学习文档",
        "quiz": "练习题",
        "code": "代码实践",
        "mindmap": "思维导图",
        "ppt": "教学演示",
        "animation": "算法动画",
        "reading": "拓展阅读",
    }.get(resource_type, "学习资源")
    return normalize_tts_text(f"{type_label}：{title}。{content}")


def split_text_for_tts(text: str) -> list[str]:
    chunks: list[str] = []
    current = ""
    for piece in re.split(r"([。！？!?；;])", text):
        if not piece:
            continue
        candidate = current + piece
        if len(candidate.encode("utf-8")) <= _MAX_CHUNK_BYTES:
            current = candidate
            continue
        if current:
            chunks.append(current.strip())
            current = ""
        chunks.extend(_split_long_piece(piece))
    if current.strip():
        chunks.append(current.strip())
    return chunks


def get_xunfei_tts_client() -> XunfeiTTSClient | None:
    settings = get_settings()
    if not settings.xunfei_tts_enabled:
        return None
    return XunfeiTTSClient(config=_build_tts_config(settings))


def get_xunfei_tts_configuration_warning() -> str | None:
    settings = get_settings()
    if not settings.xunfei_tts_enabled:
        return "讯飞 TTS 未启用，资源语音朗读接口不可用"
    config = _build_tts_config(settings)
    if not (config.app_id and config.api_key and config.api_secret):
        return "讯飞 TTS 已启用但凭证未配置，资源语音朗读接口不可用"
    return None


def _build_tts_config(settings: Settings) -> XunfeiTTSConfig:
    return XunfeiTTSConfig(
        app_id=settings.xunfei_tts_app_id or settings.spark_app_id,
        api_key=settings.xunfei_tts_api_key or settings.spark_api_key,
        api_secret=settings.xunfei_tts_api_secret or settings.spark_api_secret,
        url=settings.xunfei_tts_url,
        voice=settings.xunfei_tts_voice,
        speed=settings.xunfei_tts_speed,
        volume=settings.xunfei_tts_volume,
        pitch=settings.xunfei_tts_pitch,
    )


def _split_long_piece(piece: str) -> list[str]:
    chunks: list[str] = []
    current = ""
    for char in piece:
        candidate = current + char
        if len(candidate.encode("utf-8")) > _MAX_CHUNK_BYTES:
            if current:
                chunks.append(current.strip())
            current = char
        else:
            current = candidate
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _clamp_voice_value(value: int) -> int:
    return min(100, max(0, int(value)))
