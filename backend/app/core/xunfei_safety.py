from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from dataclasses import dataclass, field
from datetime import timezone, datetime
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import Settings, get_settings


class XunfeiSafetyError(RuntimeError):
    """讯飞安全护栏客户端业务异常。"""


@dataclass(slots=True)
class SafetyAuditResult:
    """讯飞安全护栏审核结果。"""

    action: str = "none"
    rewrite_prompt: str | None = None
    append_prompt: str | None = None
    ctx_control: str | None = None
    sid: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        return self.action == "discontinue"

    @property
    def fortified(self) -> bool:
        return self.action == "fortify_prompt"

    def apply_to_prompt(self, content: str) -> str:
        if self.rewrite_prompt:
            return self.rewrite_prompt
        if self.append_prompt:
            return f"{content.rstrip()}\n\n{self.append_prompt.strip()}"
        return content


class XunfeiSafetyClient:
    """讯飞星火大模型安全护栏客户端。"""

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.app_id = self.settings.xunfei_safety_app_id
        self.access_key_id = self.settings.xunfei_safety_access_key_id
        self.access_key_secret = self.settings.xunfei_safety_access_key_secret
        self.api_base_url = self.settings.xunfei_safety_api_base_url.rstrip("/")
        self.template_id = self.settings.xunfei_safety_template_id
        self._http_client = http_client

    async def audit_input(
        self,
        content: str,
        *,
        chat_sid: str,
        context_list: list[dict[str, str]] | None = None,
        intention: str = "dialog",
    ) -> SafetyAuditResult:
        body: dict[str, Any] = {
            "content": content,
            "chat_sid": chat_sid,
            "trace_id": _new_trace_id(),
            "intention": intention,
        }
        if context_list:
            body["context_list"] = context_list
        if self.template_id:
            body["template_id"] = self.template_id
        return await self._post("/audit/v3/aichat/input", body)

    async def audit_output(
        self,
        content: str,
        *,
        chat_sid: str,
        pindex: int,
        is_end: bool,
    ) -> SafetyAuditResult:
        body: dict[str, Any] = {
            "content": content,
            "chat_sid": chat_sid,
            "trace_id": _new_trace_id(),
            "pindex": pindex,
            "is_end": is_end,
        }
        if self.template_id:
            body["template_id"] = self.template_id
        return await self._post("/audit/v3/aichat/output", body)

    async def _post(self, path: str, body: dict[str, Any]) -> SafetyAuditResult:
        self._validate_credentials()
        params = self._build_signed_params()
        url = f"{self.api_base_url}{path}"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "x-traceid": str(body["trace_id"]),
        }

        try:
            if self._http_client is not None:
                response = await self._http_client.post(
                    url,
                    params=params,
                    json=body,
                    headers=headers,
                )
            else:
                timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        url,
                        params=params,
                        json=body,
                        headers=headers,
                    )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise XunfeiSafetyError("讯飞安全护栏请求超时，请稍后重试") from exc
        except httpx.HTTPStatusError as exc:
            raise XunfeiSafetyError(
                f"讯飞安全护栏请求失败（HTTP {exc.response.status_code}）"
            ) from exc
        except httpx.HTTPError as exc:
            raise XunfeiSafetyError("讯飞安全护栏网络连接失败，请检查网络") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise XunfeiSafetyError("讯飞安全护栏返回数据格式异常") from exc

        code = str(payload.get("code", "")).strip()
        if code and code != "000000":
            message = payload.get("message") or payload.get("desc") or "未知错误"
            raise XunfeiSafetyError(
                f"讯飞安全护栏请求失败（错误码 {code}）：{message}"
            )

        data = payload.get("data")
        if not isinstance(data, dict):
            data = payload
        return _parse_audit_result(data, raw=payload)

    def _validate_credentials(self) -> None:
        if not self.app_id or not self.access_key_id or not self.access_key_secret:
            raise XunfeiSafetyError(
                "讯飞安全护栏凭证未配置，请设置 XUNFEI_SAFETY_APP_ID、"
                "XUNFEI_SAFETY_ACCESS_KEY_ID 和 XUNFEI_SAFETY_ACCESS_KEY_SECRET"
            )

    def _build_signed_params(self) -> dict[str, str]:
        params = {
            "appId": self.app_id,
            "accessKeyId": self.access_key_id,
            "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z"),
            "uuid": uuid.uuid4().hex,
        }
        params["signature"] = _sign_params(params, self.access_key_secret)
        return params


def _parse_audit_result(data: dict[str, Any], *, raw: dict[str, Any]) -> SafetyAuditResult:
    details = data.get("action_detail")
    if not isinstance(details, dict):
        details = {}

    action = str(data.get("action") or "none").strip() or "none"
    return SafetyAuditResult(
        action=action,
        rewrite_prompt=_optional_str(details.get("rewrite_prompt")),
        append_prompt=_optional_str(details.get("append_prompt")),
        ctx_control=_optional_str(details.get("ctx_control")),
        sid=_optional_str(data.get("sid")),
        raw=raw,
    )


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _sign_params(params: dict[str, str], access_key_secret: str) -> str:
    query = "&".join(
        f"{key}={quote(str(params[key]), safe='')}" for key in sorted(params)
    )
    digest = hmac.new(
        access_key_secret.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _new_trace_id() -> str:
    return uuid.uuid4().hex


def get_xunfei_safety_client() -> XunfeiSafetyClient | None:
    settings = get_settings()
    if not settings.xunfei_safety_enabled:
        return None
    return XunfeiSafetyClient(settings=settings)


def get_xunfei_safety_configuration_warning() -> str | None:
    settings = get_settings()
    if not settings.xunfei_safety_enabled:
        return "讯飞安全护栏未启用，内容审核仅使用本地规则"
    if not (
        settings.xunfei_safety_app_id
        and settings.xunfei_safety_access_key_id
        and settings.xunfei_safety_access_key_secret
    ):
        return "讯飞安全护栏已启用但凭证未配置，内容审核会回退到本地规则"
    return None
