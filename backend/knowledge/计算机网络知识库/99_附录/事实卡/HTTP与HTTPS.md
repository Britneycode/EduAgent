---
doc_id: "CN-FACT-015"
title: "HTTP与HTTPS"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "HTTP与HTTPS"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["HTTP与HTTPS", "事实卡"]
aliases: ["HTTP与HTTPS"]
summary: "HTTPS 通常是在 HTTP 语义之下使用 TLS 加密通道，提供机密性、完整性和服务器身份认证。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["HTTP与HTTPS", "事实卡"]
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
  embedding_hints: ["HTTP与HTTPS", "事实卡", "HTTP与HTTPS"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "mvp"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# HTTP与HTTPS

## 标准表述
HTTPS 通常是在 HTTP 语义之下使用 TLS 加密通道，提供机密性、完整性和服务器身份认证。

## 适用场景
Web 安全入门和协议比较。

## 常见误解
误以为 HTTPS 改变了 HTTP 方法和状态码语义。

## 可验证依据
- RFC 9110 (HTTP Semantics) + RFC 8446 (TLS 1.3)。
- 谢希仁《计算机网络》（第8版）第7.4节。
- 当前状态：`verified: true`（HTTPS = HTTP over TLS 与标准一致）。

## 关联知识
- [[计算机网络知识库/06_应用层/HTTP_HTTPS]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用简短类比解释，但不得改变协议事实。
- 文档 Agent：补充引用后更新 `verified` 与 `last_reviewed`。
