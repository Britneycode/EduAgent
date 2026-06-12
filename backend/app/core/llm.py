from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

import json

import httpx
import tenacity

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_UNSET = object()


class LLMClientError(RuntimeError):
    """LLM 客户端业务异常。"""


class BaseLLMClient(ABC):
    """统一的 LLM 文本生成接口。"""

    @abstractmethod
    async def generate_text(self, prompt: str) -> str:
        """生成文本结果。"""

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """逐 token 流式生成。默认回退到 generate_text 整体返回。"""
        text = await self.generate_text(prompt)
        yield text


class SparkLLMClient(BaseLLMClient):
    """讯飞星火大模型客户端。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.app_id = settings.spark_app_id
        self.api_key = settings.spark_api_key
        self.api_secret = settings.spark_api_secret
        self.api_password = settings.spark_api_password or settings.spark_api_key
        self.api_url = f"{settings.spark_api_base_url.rstrip('/')}/chat/completions"
        self.model = settings.spark_model

    async def generate_text(self, prompt: str) -> str:
        self._validate_credentials()
        headers, payload = self._build_request(prompt)

        try:
            parts: list[str] = []
            async for token in self._iter_stream_tokens(headers, payload):
                parts.append(token)
            content = "".join(parts)
        except httpx.TimeoutException:
            raise LLMClientError("讯飞星火请求超时，请稍后重试")
        except httpx.HTTPStatusError as exc:
            raise LLMClientError(self._build_http_error_message(exc))
        except httpx.HTTPError:
            raise LLMClientError("讯飞星火网络连接失败，请检查网络")

        if not content.strip():
            raise LLMClientError("讯飞星火返回数据格式异常")

        return content.strip()

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        self._validate_credentials()
        headers, payload = self._build_request(prompt)

        try:
            async for token in self._iter_stream_tokens(headers, payload):
                yield token
        except httpx.TimeoutException:
            raise LLMClientError("讯飞星火请求超时，请稍后重试")
        except httpx.HTTPStatusError as exc:
            raise LLMClientError(self._build_http_error_message(exc))
        except httpx.HTTPError:
            raise LLMClientError("讯飞星火网络连接失败，请检查网络")

    def _build_request(self, prompt: str) -> tuple[dict[str, str], dict]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_password}",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.7,
            "stream": True,
        }
        return headers, payload

    @tenacity.retry(
        retry=tenacity.retry_if_exception_type(httpx.TimeoutException),
        stop=tenacity.stop_after_attempt(2),
        wait=tenacity.wait_fixed(1),
        reraise=True,
    )
    async def _iter_stream_tokens(
        self, headers: dict[str, str], payload: dict
    ) -> AsyncGenerator[str, None]:
        timeout = httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                self.api_url,
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[len("data: ") :]
                    if raw.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    error_code = chunk.get("code")
                    if error_code and error_code != 0:
                        error_msg = chunk.get("message", "")
                        if str(error_code) == "11200" or "AppIdNoAuthError" in str(
                            error_msg
                        ):
                            raise LLMClientError(
                                f"讯飞星火鉴权失败：当前 AppID 未开通 {self.model} 模型权限，"
                                "请在控制台检查配置。"
                            )
                        raise LLMClientError(
                            f"讯飞星火请求失败（错误码 {error_code}）：{error_msg}"
                        )
                    try:
                        delta = chunk["choices"][0]["delta"]
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except (KeyError, IndexError):
                        continue

    def _validate_credentials(self) -> None:
        if not self.app_id or not self.api_password:
            raise LLMClientError(
                "讯飞星火凭证未配置，请设置 SPARK_APP_ID 和 SPARK_API_PASSWORD"
            )

    def _build_http_error_message(self, exc: httpx.HTTPStatusError) -> str:
        status_code = exc.response.status_code
        try:
            error_data = exc.response.json().get("error", {})
        except ValueError:
            error_data = {}

        error_code = str(error_data.get("code", "")).strip()
        error_message = str(error_data.get("message", "")).strip()

        if error_code == "11200" or "AppIdNoAuthError" in error_message:
            return (
                f"讯飞星火鉴权失败：当前 AppID 未开通 {self.model} 模型权限，"
                "或 AppID 与 APIPassword 不匹配，请在控制台检查配置。"
            )

        if status_code == 401:
            return "讯飞星火鉴权失败，请检查 APIPassword 是否正确"

        if error_message:
            return f"讯飞星火请求失败（HTTP {status_code}）：{error_message}"

        return f"讯飞星火请求失败（HTTP {status_code}），请稍后重试"


class OpenAICompatibleLLMClient(BaseLLMClient):
    """通用 OpenAI 兼容 Chat Completions 客户端。"""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_base_url: str | None = None,
        model: str | None = None,
        provider_name: str | None = None,
        api_key_setting_name: str = "OPENAI_COMPATIBLE_API_KEY",
        enable_thinking: bool | None | object = _UNSET,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.provider_name = provider_name or settings.openai_compatible_provider
        self.api_key_setting_name = api_key_setting_name
        self.api_key = api_key if api_key is not None else settings.openai_compatible_api_key
        base_url = api_base_url or settings.openai_compatible_api_base_url
        self.api_url = f"{base_url.rstrip('/')}/chat/completions"
        self.model = model or settings.openai_compatible_model
        self.enable_thinking = (
            settings.openai_compatible_enable_thinking
            if enable_thinking is _UNSET
            else enable_thinking
        )
        self._http_client = http_client

    async def generate_text(self, prompt: str) -> str:
        self._validate_credentials()
        headers, payload = self._build_request(prompt, stream=False)

        try:
            if self._http_client is not None:
                response = await self._http_client.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=self._timeout(),
                )
            else:
                async with httpx.AsyncClient(timeout=self._timeout()) as client:
                    response = await client.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                    )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMClientError(f"{self.provider_name} 请求超时，请稍后重试") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMClientError(self._build_http_error_message(exc)) from exc
        except httpx.HTTPError as exc:
            raise LLMClientError(f"{self.provider_name} 网络连接失败，请检查网络") from exc

        try:
            data = response.json()
            content = data["choices"][0]["message"].get("content", "")
        except (ValueError, KeyError, IndexError, AttributeError) as exc:
            raise LLMClientError(f"{self.provider_name} 返回数据格式异常") from exc

        if not content.strip():
            raise LLMClientError(f"{self.provider_name} 返回内容为空")
        return content.strip()

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        self._validate_credentials()
        headers, payload = self._build_request(prompt, stream=True)

        try:
            if self._http_client is not None:
                async with self._http_client.stream(
                    "POST",
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=self._timeout(),
                ) as response:
                    response.raise_for_status()
                    async for token in self._iter_sse_tokens(response):
                        yield token
                return

            async with httpx.AsyncClient(timeout=self._timeout()) as client:
                async with client.stream(
                    "POST",
                    self.api_url,
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for token in self._iter_sse_tokens(response):
                        yield token
        except httpx.TimeoutException as exc:
            raise LLMClientError(f"{self.provider_name} 请求超时，请稍后重试") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMClientError(self._build_http_error_message(exc)) from exc
        except httpx.HTTPError as exc:
            raise LLMClientError(f"{self.provider_name} 网络连接失败，请检查网络") from exc

    def _build_request(self, prompt: str, *, stream: bool) -> tuple[dict[str, str], dict]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.7,
            "stream": stream,
        }
        if self.enable_thinking is not None:
            payload["enable_thinking"] = self.enable_thinking
        return headers, payload

    async def _iter_sse_tokens(
        self, response: httpx.Response
    ) -> AsyncGenerator[str, None]:
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            raw = line[len("data: ") :]
            if raw.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(raw)
            except json.JSONDecodeError:
                continue
            try:
                delta = chunk["choices"][0].get("delta", {})
                token = delta.get("content", "")
            except (KeyError, IndexError, AttributeError):
                continue
            if token:
                yield token

    def _validate_credentials(self) -> None:
        if not self.api_key:
            raise LLMClientError(
                f"{self.provider_name} API Key 未配置，请设置 {self.api_key_setting_name}"
            )

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0)

    def _build_http_error_message(self, exc: httpx.HTTPStatusError) -> str:
        status_code = exc.response.status_code
        try:
            error_data = exc.response.json().get("error", {})
        except ValueError:
            error_data = {}

        message = str(error_data.get("message", "")).strip()
        if status_code == 401:
            return (
                f"{self.provider_name} 鉴权失败，"
                f"请检查 {self.api_key_setting_name} 是否正确"
            )
        if message:
            return f"{self.provider_name} 请求失败（HTTP {status_code}）：{message}"
        return f"{self.provider_name} 请求失败（HTTP {status_code}），请稍后重试"


class DeepSeekLLMClient(OpenAICompatibleLLMClient):
    """DeepSeek OpenAI 兼容 Chat Completions 客户端。"""

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        settings = get_settings()
        super().__init__(
            api_key=settings.deepseek_api_key,
            api_base_url=settings.deepseek_api_base_url,
            model=settings.deepseek_model,
            provider_name="DeepSeek",
            api_key_setting_name="DEEPSEEK_API_KEY",
            enable_thinking=None,
            http_client=http_client,
        )


class FallbackLLMClient(BaseLLMClient):
    """主模型失败时自动切换备用模型。"""

    def __init__(self, primary: BaseLLMClient, fallback: BaseLLMClient) -> None:
        self.primary = primary
        self.fallback = fallback

    async def generate_text(self, prompt: str) -> str:
        try:
            return await self.primary.generate_text(prompt)
        except Exception:
            logger.warning("主 LLM 调用失败，切换备用 LLM", exc_info=True)
            return await self.fallback.generate_text(prompt)

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        emitted = False
        try:
            async for token in self.primary.generate_stream(prompt):
                emitted = True
                yield token
            return
        except Exception:
            if emitted:
                raise
            logger.warning("主 LLM 流式调用失败，切换备用 LLM", exc_info=True)

        async for token in self.fallback.generate_stream(prompt):
            yield token


class DevLLMClient(BaseLLMClient):
    """开发模式 LLM 客户端，返回模拟内容。

    仅在 SPARK_DEV_MODE=true 时使用。
    """

    async def generate_text(self, prompt: str) -> str:
        logger.warning("⚠️ 当前为开发模式，LLM 响应为模拟内容")
        return (
            "[开发模式] 这是一份模拟的学习讲义内容。\n\n"
            "一、主题概览\n"
            "本讲义将帮助你系统地理解相关知识点的核心概念和应用场景。\n\n"
            "二、核心概念\n"
            "在学习过程中，需要重点关注以下几个方面的内容。\n\n"
            "三、学习步骤\n"
            "建议按照从基础到进阶的顺序逐步掌握。\n\n"
            "四、常见误区\n"
            "初学者容易混淆相似概念，需要注意区分。\n\n"
            "五、复习建议\n"
            "定期回顾关键概念，通过实践加深理解。"
        )


def get_llm_configuration_warning() -> str | None:
    settings = get_settings()
    has_credentials = bool(
        settings.spark_app_id
        and (settings.spark_api_password or settings.spark_api_key)
    )
    has_deepseek = bool(settings.deepseek_enabled and settings.deepseek_api_key)
    has_openai_compatible = bool(
        settings.openai_compatible_enabled and settings.openai_compatible_api_key
    )
    if has_credentials or settings.spark_dev_mode or has_deepseek or has_openai_compatible:
        return None
    return (
        "讯飞星火未配置，当前为真实调用模式，聊天时会失败。"
        "请设置 SPARK_APP_ID、SPARK_API_PASSWORD，"
        "或启用 SPARK_DEV_MODE=true / DEEPSEEK_ENABLED=true / "
        "OPENAI_COMPATIBLE_ENABLED=true。"
    )


def get_llm_mode() -> str:
    settings = get_settings()
    has_spark_credentials = bool(
        settings.spark_app_id
        and (settings.spark_api_password or settings.spark_api_key)
    )
    has_deepseek = bool(settings.deepseek_enabled and settings.deepseek_api_key)
    has_openai_compatible = bool(
        settings.openai_compatible_enabled and settings.openai_compatible_api_key
    )

    if settings.spark_dev_mode:
        return "dev"
    if has_openai_compatible:
        return "openai_compatible"
    if has_spark_credentials:
        return "spark"
    if has_deepseek:
        return "deepseek"
    return "unconfigured"


def get_llm_client() -> BaseLLMClient:
    """根据配置返回合适的 LLM 客户端。"""
    settings = get_settings()
    if settings.spark_dev_mode:
        logger.warning("⚠️ 当前为开发模式，LLM 响应为模拟内容")
        return DevLLMClient()

    has_spark_credentials = bool(
        settings.spark_app_id
        and (settings.spark_api_password or settings.spark_api_key)
    )
    has_deepseek = bool(settings.deepseek_enabled and settings.deepseek_api_key)
    has_openai_compatible = bool(
        settings.openai_compatible_enabled and settings.openai_compatible_api_key
    )

    if has_openai_compatible:
        return OpenAICompatibleLLMClient()

    if has_spark_credentials and has_deepseek:
        return FallbackLLMClient(SparkLLMClient(), DeepSeekLLMClient())
    if has_deepseek:
        return DeepSeekLLMClient()
    return SparkLLMClient()
