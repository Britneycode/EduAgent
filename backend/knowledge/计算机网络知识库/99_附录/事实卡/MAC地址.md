---
doc_id: "CN-FACT-017"
title: "MAC地址"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "MAC地址"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["MAC地址", "事实卡"]
aliases: ["MAC地址"]
summary: "MAC 地址是数据链路层地址，常用于局域网内帧转发和接口标识。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["MAC地址", "事实卡"]
graph_nodes: []
graph_edges: []
source_level: "teaching_consensus"
sources: []
verified: true
status: "active"
version: "0.1.0"
created: "2026-05-07"
last_reviewed: "2026-05-07"
reviewer: "标准/教材核验"
owner_agent: "文档 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: false
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "very_high"
  embedding_hints: ["MAC地址", "事实卡", "MAC地址"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "mvp"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# MAC地址

## 标准表述
MAC 地址是数据链路层地址，常用于局域网内帧转发和接口标识。

## 适用场景
以太网、交换机和 ARP 讲解。

## 常见误解
误以为 MAC 地址直接用于跨互联网端到端路由。

## 可验证依据
- IEEE 802 标准 - MAC 地址格式和分配。
- 谢希仁《计算机网络》（第8版）第3.3节。
- 当前状态：`verified: true`（地址格式与 IEEE 标准一致）。

## 关联知识
- [[计算机网络知识库/03_数据链路层/MAC地址与交换机]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用简短类比解释，但不得改变协议事实。
- 文档 Agent：补充引用后更新 `verified` 与 `last_reviewed`。
