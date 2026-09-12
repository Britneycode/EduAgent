"""思维导图渲染 — 将 Mermaid（mindmap）源码渲染为 PNG data URL。

渲染服务选型（两路均经本机实测支持 mindmap 语法与中文节点）：
1. 主路径 kroki.io：POST 源码原文渲染，无 URL 长度限制（实测约 1.4s）
2. 回退 mermaid.ink：GET 携带 base64 源码的图片 URL，受 URL 长度限制，仅作兜底

对外契约：渲染失败一律返回空字符串，绝不抛异常打断业务。
"""

from __future__ import annotations

import base64
import logging
import re

import httpx

logger = logging.getLogger(__name__)

KROKI_RENDER_URL = "https://kroki.io/mermaid/png"
MERMAID_INK_BASE_URL = "https://mermaid.ink/img"

# 连接 5s / 读 15s（远端渲染耗时较长）/ 写 5s / 连接池 5s
HTTP_TIMEOUT = httpx.Timeout(connect=5, read=15, write=5, pool=5)

# ```mermaid 围栏代码块（非贪婪取第一个，\s 兼容 CRLF）
_MERMAID_FENCE_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)


def extract_mermaid_block(content: str) -> str:
    """从 LLM 输出中提取 mermaid 导图源码；无代码块时接受裸 mindmap 源码。"""
    match = _MERMAID_FENCE_RE.search(content)
    if match:
        return match.group(1).strip()

    # 无围栏时，以 mindmap 关键字开头的裸 Mermaid 也视为合法导图源码
    stripped = content.strip()
    if stripped.startswith("mindmap"):
        return stripped

    return ""


def _to_png_data_url(png_bytes: bytes) -> str:
    """把 PNG 字节编码为可直接放入 image_url 的 data URL。"""
    encoded = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _mermaid_ink_url(mermaid_code: str) -> str:
    """构造 mermaid.ink 回退 URL（urlsafe base64 去 padding，必须带 type=png）。"""
    token = (
        base64.urlsafe_b64encode(mermaid_code.encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    return f"{MERMAID_INK_BASE_URL}/{token}?type=png"


async def render_mindmap_image(
    mermaid_code: str, transport: httpx.AsyncTransport | None = None
) -> str:
    """把 Mermaid 源码渲染为 PNG data URL；任一环节失败返回空字符串。"""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, transport=transport) as client:
        # 主路径：kroki POST 源码原文（无 URL 长度限制）
        try:
            response = await client.post(
                KROKI_RENDER_URL,
                content=mermaid_code.encode("utf-8"),
                headers={"Content-Type": "text/plain"},
            )
        except httpx.HTTPError as exc:
            logger.warning("kroki 渲染网络异常: %s", exc)
        else:
            if response.status_code == 200 and response.content:
                return _to_png_data_url(response.content)
            logger.warning(
                "kroki 渲染失败 (HTTP %d)，尝试回退 mermaid.ink",
                response.status_code,
            )

        # 回退：mermaid.ink GET（该服务默认返回 JPEG，必须显式带 type=png）
        try:
            response = await client.get(_mermaid_ink_url(mermaid_code))
        except httpx.HTTPError as exc:
            logger.warning("mermaid.ink 渲染网络异常: %s", exc)
        else:
            if response.status_code == 200 and response.content:
                return _to_png_data_url(response.content)
            logger.warning("mermaid.ink 渲染失败 (HTTP %d)", response.status_code)

    return ""
