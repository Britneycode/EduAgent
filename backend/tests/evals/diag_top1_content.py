"""诊断：过滤元内容后，top-1 检索结果的真实内容质量。

对每条查询打印 top-1 chunk 的章节/标题/正文前 120 字，人工判断
"是否真的能回答这个问题"——验证元内容过滤后检索到的是知识而非脚手架。

复现：cd backend && uv run python tests/evals/diag_top1_content.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from app.wiki.embeddings import DevEmbedding
from app.wiki.ingestion import KnowledgeIngestion
from app.wiki.rag_engine import RAGEngine
from app.wiki.vector_store import VectorStore

from eval_rag_hit_real import CASES, KNOWLEDGE_DIR


async def _run() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "dev"
    if mode == "bge":
        from app.wiki.embeddings import get_embedding_client
        embedding = get_embedding_client(dev_mode=False)
    else:
        embedding = DevEmbedding()

    store = VectorStore(embedding_client=embedding, persist_directory=None)
    await KnowledgeIngestion(store).ingest_course(KNOWLEDGE_DIR, course_id="CN101")
    engine = RAGEngine(store)

    for query, expected in CASES:
        results = await engine.search(query, top_k=1)
        if not results:
            print(f"[{expected}] {query}\n  <无结果>\n")
            continue
        r = results[0]
        content = " ".join(r.content.split())[:120]
        print(f"[预期 {expected} | 命中 {r.chapter}] {query}")
        print(f"  标题: {r.title}")
        print(f"  内容: {content}\n")


if __name__ == "__main__":
    asyncio.run(_run())