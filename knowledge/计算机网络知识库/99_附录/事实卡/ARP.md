---
doc_id: "CN-FACT-011"
title: "ARP"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "ARP"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["ARP", "事实卡"]
aliases: ["ARP"]
summary: "ARP 在 IPv4 局域网中用于根据目标 IP 地址解析对应 MAC 地址，常以广播请求和单播应答形式出现。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["ARP", "事实卡"]
graph_nodes: []
graph_edges: []
source_level: "teaching_consensus"
sources: []
verified: true
status: "active"
version: "0.1.0"
created: "2026-05-07"
last_reviewed: "2026-05-07"
reviewer: "RFC/教材核验"
owner_agent: "文档 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: false
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "very_high"
  embedding_hints: ["ARP", "事实卡", "ARP"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "mvp"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# ARP

## 标准表述
ARP 在 IPv4 局域网中用于根据目标 IP 地址解析对应 MAC 地址，常以广播请求和单播应答形式出现。

## 适用场景
解释同网段通信和 Wireshark ARP 报文。

## 常见误解
误以为 ARP 用于跨互联网寻找最终目的主机 MAC。

## 可验证依据
- RFC 826 - An Ethernet Address Resolution Protocol。
- 谢希仁《计算机网络》（第8版）第4.5节。
- 当前状态：`verified: true`（基本机制与 RFC 一致）。

## 关联知识
- [[计算机网络知识库/04_网络层/ARP_ICMP_IGMP]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用简短类比解释，但不得改变协议事实。
- 文档 Agent：补充引用后更新 `verified` 与 `last_reviewed`。
