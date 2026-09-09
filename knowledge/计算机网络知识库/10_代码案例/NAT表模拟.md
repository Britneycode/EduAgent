---
doc_id: "CN-CODE-012"
title: "NAT表模拟"
doc_type: "code_case"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "10_代码案例"
section: ""
topic: "NAT表模拟"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "hard"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["NAT", "NAPT", "代码案例", "地址转换"]
aliases: ["NAT表模拟"]
summary: "用 Python 模拟 NAPT 的端口映射与地址改写流程。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["NAT", "NAPT", "代码案例"]
graph_nodes: ["cn_nat"]
graph_edges: []
source_level: "teaching_consensus"
sources: []
verified: false
status: "draft"
version: "0.1.0"
created: "2026-05-19"
last_reviewed: "2026-05-19"
reviewer: "待审核"
owner_agent: "代码 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
  embedding_hints: ["NAT", "NAPT", "代码案例", "地址转换"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# NAT表模拟

## 1. 案例目标
用 Python 模拟 NAPT 的地址与端口映射，理解"多内网主机共享一个公网 IP + 端口区分会话"的核心思想。

## 2. 先修知识
- [[计算机网络知识库/04_网络层/NAT]]

## 3. 示例代码 / 伪代码
```python
class NAPTSimulator:
    """极简 NAPT 模拟：内网地址+端口 <-> 公网地址+端口 双向映射。"""

    def __init__(self, public_ip: str):
        self.public_ip = public_ip
        self._table: dict[tuple, tuple] = {}
        self._next_port = 40000

    def outbound(self, src_ip: str, src_port: int, dst_ip: str, dst_port: int):
        """内网->公网：记录映射并返回改写后的 (公网IP, 新端口, 目的)。"""
        key = (src_ip, src_port, dst_ip, dst_port)
        if key not in self._table:
            self._next_port += 1
            self._table[key] = (self.public_ip, self._next_port)
        pub_ip, pub_port = self._table[key]
        print(f"[出站] {src_ip}:{src_port} -> {dst_ip}:{dst_port} "
              f"改写为 {pub_ip}:{pub_port} -> {dst_ip}:{dst_port}")
        return pub_ip, pub_port

    def inbound(self, dst_ip: str, dst_port: int, src_ip: str, src_port: int):
        """公网->内网：反向查表，恢复内网主机地址。"""
        for (sip, sp, dip, dp), (pip, pp) in self._table.items():
            if pip == dst_ip and pp == dst_port and dip == src_ip and dp == src_port:
                print(f"[入站] {src_ip}:{src_port} -> {dst_ip}:{dst_port} "
                      f"恢复为 {src_ip}:{src_port} -> {sip}:{sp}")
                return sip, sp
        print("[入站] 未命中 NAT 表，丢弃")
        return None

# 两个内网主机共享一个公网 IP
nat = NAPTSimulator("203.0.113.1")
nat.outbound("192.168.1.10", 5000, "93.184.216.34", 80)
nat.outbound("192.168.1.20", 5000, "93.184.216.34", 80)
nat.inbound("203.0.113.1", 40001, "93.184.216.34", 80)
nat.inbound("203.0.113.1", 40002, "93.184.216.34", 80)
```

## 4. 运行与观察
- 两个内网主机使用相同源端口，仍被分配不同公网端口，印证 NAPT 端口复用。
- 入站方向靠 NAT 表反向恢复内网地址。
- 思考：若公网主动向 203.0.113.1:40001 发起连接，会命中映射吗？

## 5. 相关链接
- [[计算机网络知识库/04_网络层/NAT]]
- [[计算机网络知识库/08_实验与工具/NAT抓包实验]]
