"""RAG 命中率评测（真实知识库，含向量/词法双模式 + 双口径）。

用真实课程知识库（计算机网络 CN101）做端到端检索评测：
- 导入知识库 → 构造学生式查询集 → 检索 → 统计命中率。

两种模式对比：
  1. dev  ：DevEmbedding（零向量）→ 混合检索退化为纯 BM25 词法召回，代表「词法下限」；
  2. bge  ：BAAI/bge-small-zh-v1.5 真实向量 + BM25 混合，代表「生产形态」。

两个口径（诚实并陈）：
  A. 授课章节命中（严格）：top-k 是否命中预期授课章节（cn01~cn07）。
     局限：知识库存在「授课讲解 vs 习题 cn09 vs 事实卡 cn99」的内容重叠，
     命中习题/事实卡也是命中了正确知识，但在本口径下记为未命中。
  B. 内容相关性命中（宽松）：top-k 是否有 chunk 的标题或正文包含该查询的核心
     知识点关键词。更贴近产品目标——E4 生成是把 top-k 注入 prompt，只要检索到
     相关知识即可支撑生成，不纠结落在哪个章节。

复现：
    cd backend
    uv run python tests/evals/eval_rag_hit_real.py          # 双模式对比
    uv run python tests/evals/eval_rag_hit_real.py dev      # 仅词法下限（快）
    uv run python tests/evals/eval_rag_hit_real.py bge      # 仅真实混合

首次 bge 模式会从本地 HuggingFace 缓存加载模型，离线可用，无需联网。
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# 强制离线加载本地 BGE 模型缓存，避免在无网环境卡在 Hub 检查
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from app.wiki.embeddings import DevEmbedding, get_embedding_client
from app.wiki.ingestion import KnowledgeIngestion
from app.wiki.rag_engine import RAGEngine
from app.wiki.vector_store import VectorStore

# 学生式查询 → (预期授课章节 chapter_id, 核心知识点关键词)
CASES: list[tuple[str, str, tuple[str, ...]]] = [
    # —— cn01 基础理论 ——
    ("网络为什么要分层，分层有什么好处", "cn01", ("分层", "体系结构", "OSI", "协议")),
    ("OSI 参考模型都有哪七层", "cn01", ("OSI", "七层", "物理层", "应用层")),
    ("什么是协议栈", "cn01", ("协议栈", "协议")),
    # —— cn02 物理层 ——
    ("双绞线和光纤有什么区别", "cn02", ("双绞线", "光纤", "传输介质", "介质")),
    ("什么是调制和解调", "cn02", ("调制", "解调", "编码")),
    ("信道的带宽是不是越大传输越快", "cn02", ("带宽", "信道", "传输速率", "速率")),
    # —— cn03 数据链路层 ——
    ("MAC 地址是干什么用的", "cn03", ("MAC", "物理地址", "硬件地址")),
    ("交换机和集线器有什么不一样", "cn03", ("交换机", "集线器", "hub")),
    ("CRC 校验是怎么检测出错的", "cn03", ("CRC", "循环冗余", "校验", "检错")),
    ("VLAN 有什么作用", "cn03", ("VLAN", "虚拟局域网", "广播域")),
    # —— cn04 网络层 ——
    ("子网掩码是怎么算的", "cn04", ("子网掩码", "网络前缀", "主机号", "子网")),
    ("CIDR 地址聚合是什么意思", "cn04", ("CIDR", "地址聚合", "前缀")),
    ("ARP 协议是干什么的", "cn04", ("ARP", "地址解析")),
    ("NAT 为什么需要做地址转换", "cn04", ("NAT", "地址转换")),
    # —— cn05 运输层 ——
    ("TCP 为什么要三次握手", "cn05", ("三次握手", "SYN", "ACK")),
    ("UDP 和 TCP 的区别是什么", "cn05", ("UDP", "TCP", "面向连接", "无连接")),
    ("拥塞控制是怎么一回事", "cn05", ("拥塞控制", "拥塞窗口", "cwnd", "慢启动")),
    ("滑动窗口在可靠传输里起什么作用", "cn05", ("滑动窗口", "可靠传输", "确认", "重传")),
    # —— cn06 应用层 ——
    ("DNS 域名是怎么解析成 IP 的", "cn06", ("DNS", "域名解析", "域名")),
    ("HTTPS 和 HTTP 的区别是什么", "cn06", ("HTTPS", "HTTP", "TLS", "加密")),
    ("电子邮件是怎么从发件人送到收件人的", "cn06", ("电子邮件", "SMTP", "POP3", "邮件")),
    # —— cn07 网络安全 ——
    ("防火墙是干什么的", "cn07", ("防火墙", "包过滤", "过滤")),
    ("对称加密和非对称加密有什么区别", "cn07", ("对称加密", "非对称加密", "公钥", "私钥")),
    ("TLS 握手是怎么建立安全连接的", "cn07", ("TLS", "SSL", "握手", "加密")),
]

KNOWLEDGE_DIR = (
    Path(__file__).resolve().parents[3] / "knowledge" / "计算机网络知识库"
)


def _content_matches(results, keywords: tuple[str, ...]) -> bool:
    """判定 top-k 结果里是否有 chunk 的标题或正文包含任一核心知识点关键词。"""
    for r in results:
        haystack = f"{r.title}\n{r.content}"
        if any(kw.lower() in haystack.lower() for kw in keywords):
            return True
    return False


async def run_mode(mode: str) -> tuple[dict[str, object], list[str]]:
    if mode == "bge":
        embedding = get_embedding_client(dev_mode=False)
        label = "BGE 向量 + BM25 混合（生产形态）"
    else:
        embedding = DevEmbedding()
        label = "纯 BM25 词法（零向量下限）"

    store = VectorStore(embedding_client=embedding, persist_directory=None)
    ingestion = KnowledgeIngestion(store)
    chunk_count = await ingestion.ingest_course(KNOWLEDGE_DIR, course_id="CN101")
    engine = RAGEngine(store)

    total = len(CASES)
    chap_1 = 0
    chap_3 = 0
    content_1 = 0
    content_3 = 0
    rows: list[str] = []

    for query, expected, keywords in CASES:
        results = await engine.search(query, top_k=5)
        top1_chapter = results[0].chapter if results else "-"
        chapters3 = [r.chapter for r in results[:3]]

        ok_chap_1 = top1_chapter == expected
        ok_chap_3 = expected in chapters3
        ok_content_1 = _content_matches(results[:1], keywords)
        ok_content_3 = _content_matches(results[:3], keywords)

        chap_1 += int(ok_chap_1)
        chap_3 += int(ok_chap_3)
        content_1 += int(ok_content_1)
        content_3 += int(ok_content_3)

        rows.append(
            f"{query:<30} 章节{expected} {'✓' if ok_chap_3 else '✗'}  "
            f"内容{'✓' if ok_content_3 else '✗'}  top1={top1_chapter}:{results[0].title[:14] if results else '-'}"
        )

    summary = {
        "mode": mode,
        "label": label,
        "chunk_count": chunk_count,
        "total": total,
        "chap_1": chap_1,
        "chap_3": chap_3,
        "content_1": content_1,
        "content_3": content_3,
    }
    return summary, rows


async def _run() -> None:
    modes = sys.argv[1:] or ["dev", "bge"]

    all_summaries: list[dict[str, object]] = []
    for mode in modes:
        if mode not in {"dev", "bge"}:
            print(f"未知模式: {mode}（可选 dev / bge）")
            continue
        print(f"\n=== 运行模式：{mode} ===\n")
        summary, rows = await run_mode(mode)
        all_summaries.append(summary)

        for row in rows:
            print(row)

    print("\n" + "=" * 64)
    print("=== 结果汇总（24 条学生式查询，真实知识库）===")
    for s in all_summaries:
        label = s["label"]
        total = s["total"]
        assert isinstance(total, int)
        c1, c3 = int(s["chap_1"]), int(s["chap_3"])
        k1, k3 = int(s["content_1"]), int(s["content_3"])
        print(f"\n[{label}]  chunk 数 = {s['chunk_count']}")
        print(f"  口径A 授课章节命中  top-1 {c1}/{total}={c1/total:.1%}  top-3 {c3}/{total}={c3/total:.1%}")
        print(f"  口径B 内容相关命中  top-1 {k1}/{total}={k1/total:.1%}  top-3 {k3}/{total}={k3/total:.1%}")


if __name__ == "__main__":
    asyncio.run(_run())