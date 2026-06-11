---
doc_id: "CN-FACT-021"
title: "TLS握手过程"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "TLS握手过程"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["TLS握手过程", "事实卡", "安全"]
aliases: ["TLS握手过程"]
summary: "TLS 握手通常包括：客户端发送 ClientHello（支持的密码套件和随机数）；服务器回复 ServerHello（选定套件、证书和随机数）；双方通过密钥交换算法协商预主密钥；最终生成对称会话密钥。TLS 1.3 将握手简化为 1-RTT。"
learning_goals: ["快速召回标准事实", "支持题库与导师 Agent 给出一致表述"]
prerequisites: []
related_docs: []
related_concepts: ["TLS握手过程", "事实卡", "安全"]
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
  embedding_hints: ["TLS握手过程", "事实卡", "安全", "TLS握手过程"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "expanded"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# TLS握手过程

## 标准表述
TLS 握手通常包括：客户端发送 ClientHello（支持的密码套件和随机数）；服务器回复 ServerHello（选定套件、证书和随机数）；双方通过密钥交换算法协商预主密钥；最终生成对称会话密钥。TLS 1.3 将握手简化为 1-RTT。

## 适用场景
讲解 HTTPS 安全机制、TLS 抓包实验和 Web 安全选择题。

## 常见误解
误以为 TLS 握手和 TCP 握手是同一个过程；误以为 TLS 1.3 握手与 TLS 1.2 完全相同。

## 可验证依据
- - RFC 8446 - The Transport Layer Security (TLS) Protocol Version 1.3，定义 TLS 1.3 握手流程。
- RFC 5246 - The Transport Layer Security (TLS) Protocol Version 1.2，定义 TLS 1.2 握手流程。
- 谢希仁《计算机网络》（第8版）第7.4节 - HTTPS 与 TLS 教学讲解。
- 当前状态：`verified: true`（核心握手流程与 RFC 一致）。

## 关联知识
- [[计算机网络知识库/07_网络安全与无线网络/TLS_SSL]]
- [[计算机网络知识库/06_应用层/HTTP_HTTPS]]
- [[计算机网络知识库/08_实验与工具/TLS握手抓包实验]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用类比解释安全概念，但不得改变协议事实。
- 文档 Agent：补充 RFC/标准引用后更新 verified 与 last_reviewed。
