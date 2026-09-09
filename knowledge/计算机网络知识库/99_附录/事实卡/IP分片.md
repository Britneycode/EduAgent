---
doc_id: "CN-FACT-008"
title: "IP分片"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "IP分片"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["IP分片", "事实卡"]
aliases: ["IP分片"]
summary: "当 IPv4 数据报长度超过下一跳 MTU 且允许分片时，可被拆成多个片，依靠标识、标志和片偏移重组。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["IP分片", "事实卡"]
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
  embedding_hints: ["IP分片", "事实卡", "IP分片"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "mvp"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# IP分片

## 标准表述
当 IPv4 数据报长度超过下一跳 MTU 且允许分片时，可被拆成多个片，依靠标识、标志和片偏移重组。

## 适用场景
MTU、分片计算和抓包解释。

## 常见误解
误以为每一跳都会立即重组；教学中通常强调目的主机重组。

## 可验证依据
- RFC 791 (IPv4) Section 2.3 - 分片和重组。
- 谢希仁《计算机网络》（第8版）第4.2节。
- 当前状态：`verified: true`（分片机制与 RFC 一致）。

## 关联知识
- [[计算机网络知识库/04_网络层/IP协议]]
- [[计算机网络知识库/10_代码案例/IP分片模拟]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用简短类比解释，但不得改变协议事实。
- 文档 Agent：补充引用后更新 `verified` 与 `last_reviewed`。
