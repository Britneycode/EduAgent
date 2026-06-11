from __future__ import annotations

import asyncio

from app.agents.content_guard import (
    audit_model_output,
    audit_user_input,
    format_source_citations,
)
from app.core.xunfei_safety import SafetyAuditResult


class BlockingInputClient:
    async def audit_input(self, *args, **kwargs) -> SafetyAuditResult:
        return SafetyAuditResult(action="discontinue")


class FortifyInputClient:
    async def audit_input(self, *args, **kwargs) -> SafetyAuditResult:
        return SafetyAuditResult(
            action="fortify_prompt",
            append_prompt="请用安全的学习场景回答。",
        )


class RecordingOutputClient:
    def __init__(self, action: str = "none") -> None:
        self.action = action
        self.calls: list[dict[str, object]] = []

    async def audit_output(self, content: str, **kwargs) -> SafetyAuditResult:
        self.calls.append({"content": content, **kwargs})
        return SafetyAuditResult(action=self.action)


def test_audit_user_input_blocks_high_risk_prompt() -> None:
    content, warnings, allowed = asyncio.run(
        audit_user_input(
            "高风险输入",
            chat_sid="chat-1",
            client=BlockingInputClient(),
        )
    )

    assert content == "高风险输入"
    assert allowed is False
    assert "高风险" in warnings[0]


def test_audit_user_input_applies_fortified_prompt() -> None:
    content, warnings, allowed = asyncio.run(
        audit_user_input(
            "帮我学习反向传播",
            chat_sid="chat-1",
            client=FortifyInputClient(),
        )
    )

    assert allowed is True
    assert "帮我学习反向传播" in content
    assert "请用安全的学习场景回答" in content
    assert "增强" in warnings[0]


def test_audit_model_output_chunks_long_content() -> None:
    client = RecordingOutputClient()

    content, warnings, allowed = asyncio.run(
        audit_model_output("a" * 9500, chat_sid="chat-1", client=client)
    )

    assert allowed is True
    assert warnings == []
    assert content == "a" * 9500
    assert len(client.calls) == 2
    assert client.calls[0]["pindex"] == 1
    assert client.calls[0]["is_end"] is False
    assert client.calls[1]["pindex"] == 2
    assert client.calls[1]["is_end"] is True


def test_audit_model_output_blocks_high_risk_response() -> None:
    client = RecordingOutputClient(action="discontinue")

    content, warnings, allowed = asyncio.run(
        audit_model_output("高风险输出", chat_sid="chat-1", client=client)
    )

    assert allowed is False
    assert "审核未通过" in content
    assert "高风险" in warnings[0]


def test_format_source_citations_includes_confidence_and_snippets() -> None:
    markdown = format_source_citations(
        [
            {
                "chapter": "ch5",
                "section": "ch5_s1",
                "title": "反向传播",
                "score": 0.82,
                "chunk_id": "ch5_反向传播",
                "snippet": "反向传播通过链式法则高效计算梯度。",
            }
        ],
        confidence=0.25,
    )

    assert "来源覆盖率：25%" in markdown
    assert "置信度较低" in markdown
    assert "片段 ch5_反向传播" in markdown
    assert "链式法则" in markdown
