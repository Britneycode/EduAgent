"""诊断：统计知识库所有 chunk 的标题分布，定位元内容污染模式。

用零向量快速导入（不检索，只统计标题），输出高频 chunk 标题及频次，
帮助识别「教学脚手架」类标题（学习目标/教学提示/生成钩子等）的污染规模。

复现：cd backend && uv run python tests/evals/diag_chunk_titles.py
"""

from __future__ import annotations

import asyncio
import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")

from app.wiki.embeddings import DevEmbedding
from app.wiki.ingestion import KnowledgeIngestion
from app.wiki.vector_store import VectorStore

KNOWLEDGE_DIR = (
    Path(__file__).resolve().parents[3] / "knowledge" / "计算机网络知识库"
)


async def _run() -> None:
    store = VectorStore(embedding_client=DevEmbedding(), persist_directory=None)
    await KnowledgeIngestion(store).ingest_course(KNOWLEDGE_DIR, course_id="CN101")

    titles = Counter()
    chapters = Counter()
    for i, title in enumerate(store._documents):  # noqa: SLF001 - 诊断用
        meta = store._metadatas[i]  # noqa: SLF001
        chunk_title = str(meta.get("title", ""))
        chapter = str(meta.get("chapter", ""))
        titles[chunk_title] += 1
        chapters[chapter] += 1

    print(f"总 chunk 数：{len(store._ids)}\n")  # noqa: SLF001
    print("=== 高频 chunk 标题（top 40，元内容会聚类浮现）===")
    for title, cnt in titles.most_common(40):
        print(f"  {cnt:>3}  {title}")

    print("\n=== 各章节 chunk 数 ===")
    for ch, cnt in sorted(chapters.items()):
        print(f"  {ch:<8} {cnt}")


if __name__ == "__main__":
    asyncio.run(_run())