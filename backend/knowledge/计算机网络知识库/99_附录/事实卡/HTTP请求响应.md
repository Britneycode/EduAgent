---
doc_id: "CN-FACT-014"
title: "HTTP请求响应"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "HTTP请求响应"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["HTTP请求响应", "事实卡"]
aliases: ["HTTP请求响应"]
summary: "HTTP 采用请求-响应模型，请求包含方法、路径、版本、首部和可选消息体，响应包含状态码、首部和响应体。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["HTTP请求响应", "事实卡"]
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
  embedding_hints: ["HTTP请求响应", "事实卡", "HTTP请求响应"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "mvp"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# HTTP请求响应

## 标准表述
HTTP 采用请求-响应模型，请求包含方法、路径、版本、首部和可选消息体，响应包含状态码、首部和响应体。

## 适用场景
HTTP 报文解析和代码案例。

## 常见误解
误以为 HTTP 状态码能完全代表业务成功。

## 可验证依据
- RFC 9110 - HTTP Semantics。RFC 9112 - HTTP/1.1。
- 谢希仁《计算机网络》（第8版）第6.4节。
- 当前状态：`verified: true`（报文结构与 RFC 一致）。

## 关联知识
- [[计算机网络知识库/06_应用层/HTTP_HTTPS]]
- [[计算机网络知识库/10_代码案例/HTTP请求解析示例]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用简短类比解释，但不得改变协议事实。
- 文档 Agent：补充引用后更新 `verified` 与 `last_reviewed`。
