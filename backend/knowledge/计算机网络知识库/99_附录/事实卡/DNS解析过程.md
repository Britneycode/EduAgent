---
doc_id: "CN-FACT-013"
title: "DNS解析过程"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "DNS解析过程"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["DNS解析过程", "事实卡"]
aliases: ["DNS解析过程"]
summary: "DNS 解析通常由客户端请求递归解析器，递归解析器再向根、顶级域和权威服务器逐级查询并缓存结果。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["DNS解析过程", "事实卡"]
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
  embedding_hints: ["DNS解析过程", "事实卡", "DNS解析过程"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "mvp"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# DNS解析过程

## 标准表述
DNS 解析通常由客户端请求递归解析器，递归解析器再向根、顶级域和权威服务器逐级查询并缓存结果。

## 适用场景
域名解析动画、DNS 题目和故障排查。

## 常见误解
误以为浏览器总是直接询问根服务器。

## 可验证依据
- RFC 1035 - Domain Names - Implementation and Specification。
- RFC 1034 - Domain Names - Concepts and Facilities。
- 谢希仁《计算机网络》（第8版）第6.3节。
- 当前状态：`verified: true`（基本流程与 RFC 一致）。

## 关联知识
- [[计算机网络知识库/06_应用层/DNS]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用简短类比解释，但不得改变协议事实。
- 文档 Agent：补充引用后更新 `verified` 与 `last_reviewed`。
