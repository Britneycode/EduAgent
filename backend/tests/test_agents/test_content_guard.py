from __future__ import annotations

import asyncio

from app.agents.content_guard import (
    audit_model_output,
    audit_user_input,
    filter_content,
    format_source_citations,
)


def test_audit_user_input_passes_content_through() -> None:
    content, warnings, allowed = asyncio.run(
        audit_user_input("帮我学习反向传播", chat_sid="chat-1")
    )

    assert content == "帮我学习反向传播"
    assert warnings == []
    assert allowed is True


def test_audit_model_output_passes_content_through() -> None:
    content, warnings, allowed = asyncio.run(
        audit_model_output("反向传播通过链式法则计算梯度。", chat_sid="chat-1")
    )

    assert content == "反向传播通过链式法则计算梯度。"
    assert warnings == []
    assert allowed is True


def test_filter_content_removes_unsafe_fragments_and_adds_disclaimer() -> None:
    filtered = filter_content("先执行 <script>alert(1)</script> 再讲解概念")

    assert "<script>" not in filtered
    assert "[已过滤]" in filtered
    assert "建议结合教材和课堂内容进行验证" in filtered


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
