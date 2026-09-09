---
doc_id: "CN-LAB-003"
title: "TCP抓包实验"
doc_type: "lab"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "08_实验与工具"
section: ""
topic: "TCP抓包实验"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["TCP抓包实验", "实验"]
aliases: ["TCP抓包实验"]
summary: "通过抓包观察 TCP 三次握手、数据传输、四次挥手与重传现象。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["TCP抓包实验", "实验"]
graph_nodes: []
graph_edges: []
source_level: "teaching_consensus"
sources: []
verified: false
status: "draft"
version: "0.1.0"
created: "2026-05-07"
last_reviewed: "2026-05-07"
reviewer: "待审核"
owner_agent: "代码 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
  embedding_hints: ["TCP抓包实验", "实验", "TCP抓包实验"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# TCP抓包实验

## 1. 实验目标
通过抓包观察 TCP 三次握手、数据传输、四次挥手与重传现象。

## 2. 操作步骤
1. 明确实验问题与预期现象。
2. 启动抓包或命令行工具。
3. 设置过滤条件，记录关键报文或输出。
4. 对照相关事实卡解释观察结果。

## 3. 验收标准
- 能说清观察现象属于哪一层协议。
- 能引用至少一个相关事实卡。
- 能说明工具输出的局限性。

## 4. 相关链接
- [[计算机网络知识库/08_实验与工具/Wireshark基础]]
- [[计算机网络知识库/99_附录/事实卡/Wireshark抓包流程]]
- [[计算机网络知识库/99_附录/事实卡/ping与traceroute]]
- [[计算机网络知识库/99_附录/事实卡/TCP三次握手]]
