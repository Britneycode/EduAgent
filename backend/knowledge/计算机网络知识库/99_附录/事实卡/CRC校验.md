---
doc_id: "CN-FACT-016"
title: "CRC校验"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "CRC校验"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["CRC校验", "事实卡"]
aliases: ["CRC校验"]
summary: "CRC 使用生成多项式和模 2 除法生成校验余数，用于检测传输差错。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["CRC校验", "事实卡"]
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
  embedding_hints: ["CRC校验", "事实卡", "CRC校验"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "mvp"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# CRC校验

## 标准表述
CRC 使用生成多项式和模 2 除法生成校验余数，用于检测传输差错。

## 适用场景
CRC 计算题和链路层检错讲解。

## 常见误解
误以为 CRC 可以保证发现所有错误或负责纠错。

## 可验证依据
- ISO/IEC 13239 - CRC 标准。IEEE 802.3 以太网帧使用 CRC-32。
- 谢希仁《计算机网络》（第8版）第3.3节。
- 当前状态：`verified: true`（CRC 基本原理与标准一致）。

## 关联知识
- [[计算机网络知识库/03_数据链路层/CRC校验]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用简短类比解释，但不得改变协议事实。
- 文档 Agent：补充引用后更新 `verified` 与 `last_reviewed`。
