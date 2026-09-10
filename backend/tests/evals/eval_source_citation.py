"""来源标注准确率评测（真实知识库 + 真实 LLM，需联网）。

验证防幻觉第三条防线在真实模型下的表现：生成内容里标注的 `[来源：章节>小节]`
是否都能溯源到检索注入的知识上下文，是否存在"幻觉引用"（引用了一个检索结果里
并不存在的来源）。

方法：
  对每条查询，用真实知识库检索上下文（含来源标签）→ 调真实 LLM 生成讲义
  （要求只依据注入片段作答并标注来源）→ 提取生成里的来源引用 → 核对可溯源比例。

口径：
  - 来源标注准确率 = 可溯源引用数 / 提取到的引用总数（越高越好）
  - 幻觉引用 = 生成里出现的、但在注入 sources 中找不到的来源（越低越好）

复现：
  cd backend
  uv run python tests/evals/eval_source_citation.py          # 默认 10 条查询
  uv run python tests/evals/eval_source_citation.py 5        # 仅前 5 条（省钱）

注意：本脚本会真实调用 LLM（DeepSeek 主 / 阿里云百炼备），消耗 API 额度；
需在可联网环境运行。
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from app.core.llm import get_llm_client
from app.wiki.embeddings import get_embedding_client
from app.wiki.ingestion import KnowledgeIngestion
from app.wiki.rag_engine import RAGEngine
from app.wiki.vector_store import VectorStore

KNOWLEDGE_DIR = (
    Path(__file__).resolve().parents[3] / "knowledge" / "计算机网络知识库"
)

QUERIES: list[tuple[str, str]] = [
    ("TCP 为什么要三次握手", "cn05"),
    ("UDP 和 TCP 的区别是什么", "cn05"),
    ("子网掩码是怎么算的", "cn04"),
    ("DNS 域名是怎么解析成 IP 的", "cn06"),
    ("HTTPS 和 HTTP 的区别是什么", "cn06"),
    ("防火墙是干什么的", "cn07"),
    ("对称加密和非对称加密有什么区别", "cn07"),
    ("MAC 地址是干什么用的", "cn03"),
    ("OSI 参考模型都有哪七层", "cn01"),
    ("NAT 为什么需要做地址转换", "cn04"),
]

_SOURCE_RE = re.compile(r"\[来源[：:]([^\]]+)\]")
_CLEAN_RE = re.compile(r"[\s>＞|｜·•]+")


def _normalize(source_text: str) -> str:
    return _CLEAN_RE.sub("", source_text).strip()


def _extract_sources(text: str) -> list[str]:
    return [_normalize(m.group(1)) for m in _SOURCE_RE.findall(text)]


def _build_source_keys(sources) -> set[str]:
    keys: set[str] = set()
    for s in sources:
        chapter = (s.chapter or "").strip()
        section = (s.section or "").strip()
        title = (s.title or "").strip()
        keys.add(_normalize(f"{chapter}{section}"))
        keys.add(_normalize(f"{chapter}"))
        keys.add(_normalize(title))
        if section:
            keys.add(_normalize(section))
    return {k for k in keys if k}


async def _run(limit: int) -> None:
    embedding = get_embedding_client(dev_mode=False)
    store = VectorStore(embedding_client=embedding, persist_directory=None)
    await KnowledgeIngestion(store).ingest_course(KNOWLEDGE_DIR, course_id="CN101")
    engine = RAGEngine(store)
    llm = get_llm_client()

    queries = QUERIES[:limit]
    total_refs = 0
    traceable = 0
    hallucinated = 0

    print(f"{'查询':<30} {'引用数':<6} {'可溯源':<6} {'幻觉':<6}")
    print("-" * 90)

    for query, _expected in queries:
        ctx = await engine.build_context_with_sources(query, top_k=3)
        source_keys = _build_source_keys(ctx.sources)
        if not ctx.context:
            print(f"{query:<30} 未检索到上下文，跳过")
            continue

        prompt = (
            "你是 EduAgent 的文档 Agent，为学生整理一份中文讲义。\n"
            "严格规则：只依据下面的参考知识作答，不得编造参考知识中没有的内容；"
            "每个知识点的末尾必须用 `[来源：章节>小节]` 标注出处，"
            "出处必须来自下面的【参考】中出现的来源。\n\n"
            f"{ctx.context}\n\n"
            f"请针对「{query}」生成讲义（含来源标注）。"
        )
        answer = await llm.generate_text(prompt)

        refs = _extract_sources(answer)
        total_refs += len(refs)

        ok = 0
        bad = 0
        for ref in refs:
            normalized = _normalize(ref)
            matched = any(
                normalized in key or key in normalized
                for key in source_keys
                if key
            )
            if matched:
                ok += 1
            else:
                bad += 1
                hallucinated += 1

        traceable += ok
        print(f"{query:<30} {len(refs):<6} {ok:<6} {bad:<6}")

    print("-" * 90)
    print(f"\n=== 来源标注准确率（{len(queries)} 条查询）===")
    if total_refs == 0:
        print("未提取到任何来源引用（检查 prompt 输出是否含 `[来源：...]`）")
    else:
        print(f"来源标注可溯源率：{traceable}/{total_refs} = {traceable / total_refs:.1%}")
        print(f"幻觉引用数：{hallucinated}")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    asyncio.run(_run(limit))