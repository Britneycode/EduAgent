---
doc_id: "CN-FACT-001"
title: "TCP三次握手"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "TCP三次握手"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["TCP三次握手", "事实卡"]
aliases: ["TCP三次握手"]
summary: "TCP 三次握手通常为：客户端发送 SYN，服务器回复 SYN+ACK，客户端回复 ACK。其核心目的包括同步双方初始序号并确认双向收发能力。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["TCP三次握手", "事实卡"]
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
  embedding_hints: ["TCP三次握手", "事实卡", "TCP三次握手"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "mvp"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# TCP三次握手

## 标准表述
TCP 三次握手通常为：客户端发送 SYN，服务器回复 SYN+ACK，客户端回复 ACK。其核心目的包括同步双方初始序号并确认双向收发能力。

## 适用场景
讲解 TCP 连接建立、抓包分析、选择题和动画脚本。

## 常见误解
误以为三次握手只是打招呼，或误以为任何抓包都严格只出现三个相关报文。

## 可验证依据
- RFC 9293 (TCP) Section 3.4 - 定义三次握手过程。
- 谢希仁《计算机网络》（第8版）第5.6节 - 三次握手教学讲解。
- 当前状态：`verified: true`（与 RFC 和主流教材一致）。

## 关联知识
- [[计算机网络知识库/05_运输层/TCP连接管理]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用简短类比解释，但不得改变协议事实。
- 文档 Agent：补充引用后更新 `verified` 与 `last_reviewed`。
