---
doc_id: "CN-FACT-019"
title: "Wireshark抓包流程"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "Wireshark抓包流程"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["Wireshark抓包流程", "事实卡"]
aliases: ["Wireshark抓包流程"]
summary: "抓包流程包括选择网卡、开始捕获、复现实验流量、使用显示过滤器定位报文、保存证据并解释字段。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["Wireshark抓包流程", "事实卡"]
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
  embedding_hints: ["Wireshark抓包流程", "事实卡", "Wireshark抓包流程"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "mvp"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# Wireshark抓包流程

## 标准表述
抓包流程包括选择网卡、开始捕获、复现实验流量、使用显示过滤器定位报文、保存证据并解释字段。

## 适用场景
实验指导和报告评价。

## 常见误解
误以为显示过滤器会改变已经捕获的数据。

## 可验证依据
- Wireshark 官方文档 (https://www.wireshark.org/docs/)。
- 当前状态：`verified: true`（操作流程与工具文档一致）。

## 关联知识
- [[计算机网络知识库/08_实验与工具/Wireshark基础]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用简短类比解释，但不得改变协议事实。
- 文档 Agent：补充引用后更新 `verified` 与 `last_reviewed`。
