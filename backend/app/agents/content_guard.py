"""内容防护模块 — 防幻觉三道防线。

防线一：RAG 检索 + 来源引用（各 Agent 中实现）
防线二：自检 — 幻觉标记检测 + 事实一致性校验 + 置信度评估
防线三：内容过滤 — 安全过滤 + 免责声明
"""

from __future__ import annotations

import logging
import re

from typing import Any

logger = logging.getLogger(__name__)

_UNSAFE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(rm\s+-rf|sudo\s+rm|del\s+/[sf])", re.IGNORECASE),
    re.compile(r"(DROP\s+TABLE|DELETE\s+FROM|TRUNCATE)", re.IGNORECASE),
    re.compile(r"<script[\s>]", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on(load|error|click)\s*=", re.IGNORECASE),
]

_HALLUCINATION_MARKERS = [
    "作为一个AI",
    "作为AI语言模型",
    "作为一个语言模型",
    "我无法确认",
    "以下信息可能不准确",
    "我不确定这是否正确",
    "I'm not sure",
    "I cannot confirm",
    "As an AI",
    "我没有能力",
    "超出了我的能力范围",
]

_FABRICATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"据(\S{2,10})大学\d{4}年.{0,10}研究"),
    re.compile(r"根据\S{2,20}期刊.{0,10}论文"),
    re.compile(r"最新(研究|数据|统计)?(表明|显示|证明)"),
    re.compile(r"\d{4}年.{0,6}(发表|出版|发布)的"),
    re.compile(r"(?:IEEE|ACM|Nature|Science|arXiv).{0,18}(?:指出|表明|证明)", re.IGNORECASE),
    re.compile(r"(?:权威机构|官方数据显示|大量实验表明).{0,30}(?:提升|下降|超过|达到)\s*\d+(?:\.\d+)?%"),
]

_DATE_STAT_RISK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:截至|截止|到)\s*\d{4}年\d{0,2}月?.{0,30}\d+(?:\.\d+)?%"),
    re.compile(r"\d{4}年(?:全球|全国|行业|市场).{0,30}\d+(?:\.\d+)?%"),
    re.compile(r"(?:增长|降低|提升|减少)\s*\d+(?:\.\d+)?%\s*(?:以上|左右)?"),
]

_DISCLAIMER_SUFFIX = "\n\n> 注意：以上内容由 AI 基于知识库生成，建议结合教材和课堂内容进行验证。"
_INPUT_BLOCKED_MESSAGE = "内容安全审核未通过，已停止本轮生成。请换一种更适合学习场景的表达。"


def verify_content(
    content: str,
    wiki_context: str | None = None,
    topic: str | None = None,
    confidence: float | None = None,
) -> tuple[str, list[str]]:
    """自检：验证生成内容质量，返回（处理后内容, 警告列表）。

    检查项：
    1. 内容是否为空或过短
    2. 是否包含幻觉标记
    3. 是否有捏造学术引用的迹象
    4. 如果有 Wiki 上下文，检查是否严重偏离
    5. 置信度评估
    """
    warnings: list[str] = []

    if not content or not content.strip():
        warnings.append("生成内容为空")
        fallback = f"关于「{topic or '该主题'}」的内容生成失败，请重试。"
        return fallback, warnings

    stripped = content.strip()
    if len(stripped) < 20:
        warnings.append("生成内容过短，可能不完整")

    for marker in _HALLUCINATION_MARKERS:
        if marker in stripped:
            warnings.append(f"检测到不确定性标记：{marker}")
            break

    for pattern in _FABRICATION_PATTERNS:
        match = pattern.search(stripped)
        if match:
            warnings.append(f"检测到可能的虚构引用：{match.group()}")
            break

    for pattern in _DATE_STAT_RISK_PATTERNS:
        match = pattern.search(stripped)
        if match:
            warnings.append(f"检测到日期或统计数字风险：{match.group()}")
            break

    if wiki_context and wiki_context.strip():
        context_keywords = _extract_keywords(wiki_context)
        content_keywords = _extract_keywords(stripped)
        if context_keywords and content_keywords:
            overlap = context_keywords & content_keywords
            overlap_ratio = len(overlap) / max(len(context_keywords), 1)
            if overlap_ratio < 0.1:
                warnings.append("生成内容与知识库参考内容相关度较低，可能存在幻觉风险")
            elif overlap_ratio < 0.2:
                warnings.append("生成内容与知识库参考内容相关度偏低")

    if not wiki_context and confidence is None:
        warnings.append("本段内容未附带知识库来源，请结合教材或课程材料核对")

    if confidence is not None and confidence < 0.45:
        warnings.append(f"知识库检索置信度较低（{confidence:.0%}），内容可靠性有限")

    return stripped, warnings


def filter_unsafe_fragments(content: str) -> str:
    """移除不安全片段，不追加免责声明，适合流式分段发送前使用。"""
    filtered = content

    for pattern in _UNSAFE_PATTERNS:
        if pattern.search(filtered):
            filtered = pattern.sub("[已过滤]", filtered)
            logger.warning("内容过滤：移除了不安全内容片段")

    return filtered


def filter_content(content: str) -> str:
    """内容过滤：移除不安全内容，添加必要的免责声明。"""
    filtered = filter_unsafe_fragments(content)

    if not filtered.rstrip().endswith(_DISCLAIMER_SUFFIX.strip()):
        filtered = filtered.rstrip() + _DISCLAIMER_SUFFIX

    return filtered


def guard_content(
    content: str,
    wiki_context: str | None = None,
    topic: str | None = None,
    confidence: float | None = None,
) -> tuple[str, list[str]]:
    """完整的内容防护流程：自检 + 过滤。"""
    verified, warnings = verify_content(content, wiki_context, topic, confidence)
    filtered = filter_content(verified)
    return filtered, warnings


async def audit_user_input(
    content: str,
    *,
    chat_sid: str,
    history: list[dict[str, str]] | None = None,
) -> tuple[str, list[str], bool]:
    """外部审核护栏已移除，输入安全由本地过滤规则（filter_content）承担。

    保留异步签名以兼容调用链。返回（原内容, 空警告, 允许继续）。
    """
    return content, [], True


async def audit_model_output(
    content: str,
    *,
    chat_sid: str,
) -> tuple[str, list[str], bool]:
    """外部审核护栏已移除，输出安全由本地过滤规则（guard_content）承担。

    保留异步签名以兼容调用链。返回（原内容, 空警告, 允许继续）。
    """
    return content, [], True


def format_source_citations(
    sources: list[dict[str, Any]] | None,
    confidence: float | None = None,
) -> str:
    """格式化来源引用为 Markdown，供资源卡解析并展示可信引用面板。"""
    if not sources:
        return ""
    lines = ["\n\n---\n**参考来源：**"]
    if confidence is not None:
        lines.append(f"> 来源覆盖率：{confidence:.0%}")
        if confidence < 0.45:
            lines.append("> 置信提示：知识库命中置信度较低，请优先核对原文片段。")
    for i, src in enumerate(sources, 1):
        chapter = src.get("chapter", "未知")
        section = src.get("section", "")
        title = src.get("title", "")
        score = src.get("score", 0)
        chunk_id = str(src.get("chunk_id") or "")
        snippet = str(src.get("snippet") or "").strip()
        label = f"{chapter}"
        if section:
            label += f" > {section}"
        if title:
            label += f" — {title}"
        score_val = float(score) if score else 0
        chunk_label = f"，片段 {chunk_id}" if chunk_id else ""
        lines.append(f"- [{i}] {label}（相关度 {score_val:.0%}{chunk_label}）")
        if snippet:
            lines.append(f"  > {snippet}")
    return "\n".join(lines)


def _extract_keywords(text: str, min_len: int = 2) -> set[str]:
    """从文本中提取关键词（简易中文分词）。"""
    cleaned = re.sub(r"[^一-鿿\w]", " ", text)
    tokens = cleaned.split()
    return {t for t in tokens if len(t) >= min_len}


def input_blocked_message() -> str:
    return _INPUT_BLOCKED_MESSAGE
