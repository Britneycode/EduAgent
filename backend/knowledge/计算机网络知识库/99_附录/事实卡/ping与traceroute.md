---
doc_id: "CN-FACT-020"
title: "ping与traceroute"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "ping与traceroute"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["ping与traceroute", "事实卡"]
aliases: ["ping与traceroute"]
summary: "ping 常用于测试连通性和 RTT；traceroute/tracert 常利用 TTL 变化观察到目的地路径上的逐跳响应。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["ping与traceroute", "事实卡"]
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
  embedding_hints: ["ping与traceroute", "事实卡", "ping与traceroute"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "mvp"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# ping与traceroute

## 标准表述
ping 常用于测试连通性和 RTT；traceroute/tracert 常利用 TTL 变化观察到目的地路径上的逐跳响应。

## 适用场景
网络诊断实验和工具比较题。

## 常见误解
误以为 ping 或 traceroute 结果总能完整反映真实路径。

## 可验证依据
- RFC 792 (ICMP) - ping 使用的 Echo Request/Reply。
- traceroute 原理基于 TTL 和 ICMP 超时报文。
- 当前状态：`verified: true`（基本原理与 RFC 一致）。

## 关联知识
- [[计算机网络知识库/08_实验与工具/ping_traceroute]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用简短类比解释，但不得改变协议事实。
- 文档 Agent：补充引用后更新 `verified` 与 `last_reviewed`。
