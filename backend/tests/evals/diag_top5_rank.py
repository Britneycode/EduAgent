"""诊断：剩余「章节未命中」查询的 top-5 完整排序，看清授课讲解排在哪。

复现：cd backend && uv run python tests/evals/diag_top5_rank.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from app.wiki.embeddings import get_embedding_client
from app.wiki.ingestion import KnowledgeIngestion
from app.wiki.rag_engine import RAGEngine
from app.wiki.vector_store import VectorStore

from eval_rag_hit_real import CASES, KNOWLEDGE_DIR

# 只诊断这几条已知的章节 miss 查询
FOCUS = {
    "什么是协议栈",
    "ARP 协议是干什么的",
    "TCP 为什么要三次握手",
    "UDP 和 TCP 的区别是什么",
    "拥塞控制是怎么一回事",
    "滑动窗口在可靠传输里起什么作用",
}


async def _run() -> None:
    embedding = get_embedding_client(dev_mode=False)
    store = VectorStore(embedding_client=embedding, persist_directory=None)
    await KnowledgeIngestion(store).ingest_course(KNOWLEDGE_DIR, course_id="CN101")
    engine = RAGEngine(store)

    for query, expected, _keywords in CASES:
        if query not in FOCUS:
            continue
        results = await engine.search(query, top_k=5)
        print(f"\n[{expected}] {query}")
        for i, r in enumerate(results, 1):
            dt = r.metadata.get("doc_type", "?")
            print(f"  {i}. {r.chapter} [{dt}] {r.title}  score={r.score:.3f}")


if __name__ == "__main__":
    asyncio.run(_run())