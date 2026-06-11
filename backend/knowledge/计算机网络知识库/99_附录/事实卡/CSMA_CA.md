---
doc_id: "CN-FACT-024"
title: "CSMA_CA"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "CSMA_CA"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["CSMA_CA", "事实卡", "安全"]
aliases: ["CSMA_CA"]
summary: "无线局域网使用 CSMA/CA（带冲突避免的载波侦听多路访问）而非 CSMA/CD，因为无线信道难以在发送时检测冲突。CSMA/CA 通过 RTS/CTS 和随机退避减少冲突。"
learning_goals: ["快速召回标准事实", "支持题库与导师 Agent 给出一致表述"]
prerequisites: []
related_docs: []
related_concepts: ["CSMA_CA", "事实卡", "安全"]
graph_nodes: []
graph_edges: []
source_level: "teaching_consensus"
sources: []
verified: true
status: "active"
version: "0.1.0"
created: "2026-05-07"
last_reviewed: "2026-05-07"
reviewer: "RFC/标准核验"
owner_agent: "文档 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: false
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "very_high"
  embedding_hints: ["CSMA_CA", "事实卡", "安全", "CSMA_CA"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "expanded"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# CSMA_CA

## 标准表述
无线局域网使用 CSMA/CA（带冲突避免的载波侦听多路访问）而非 CSMA/CD，因为无线信道难以在发送时检测冲突。CSMA/CA 通过 RTS/CTS 和随机退避减少冲突。

## 适用场景
讲解无线网络原理、比较题和协议差异。

## 常见误解
误以为无线网络使用 CSMA/CD；误以为 CSMA/CA 完全消除冲突。

## 可验证依据
- - IEEE 802.11-2020 - IEEE Standard for Information Technology -- Telecommunications and Information Exchange Between Systems -- Local and Metropolitan Area Networks，定义 CSMA/CA 和 RTS/CTS 机制。
- 谢希仁《计算机网络》（第8版）第3.5节。
- 当前状态：`verified: true`（CSMA/CA 机制与 IEEE 802.11 一致）。

## 关联知识
- [[计算机网络知识库/07_网络安全与无线网络/无线局域网基础]]
- [[计算机网络知识库/03_数据链路层/以太网]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用类比解释安全概念，但不得改变协议事实。
- 文档 Agent：补充 RFC/标准引用后更新 verified 与 last_reviewed。
