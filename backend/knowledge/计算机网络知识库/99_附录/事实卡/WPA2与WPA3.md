---
doc_id: "CN-FACT-025"
title: "WPA2与WPA3"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "WPA2与WPA3"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["WPA2与WPA3", "事实卡", "安全"]
aliases: ["WPA2与WPA3"]
summary: "WPA2 使用 AES-CCMP 加密；WPA3 引入 SAE 替代 PSK 四次握手，提供前向保密和更强暴力破解防护。WPA3-Enterprise 使用 192 位安全套件。"
learning_goals: ["快速召回标准事实", "支持题库与导师 Agent 给出一致表述"]
prerequisites: []
related_docs: []
related_concepts: ["WPA2与WPA3", "事实卡", "安全"]
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
  embedding_hints: ["WPA2与WPA3", "事实卡", "安全", "WPA2与WPA3"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "expanded"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# WPA2与WPA3

## 标准表述
WPA2 使用 AES-CCMP 加密；WPA3 引入 SAE 替代 PSK 四次握手，提供前向保密和更强暴力破解防护。WPA3-Enterprise 使用 192 位安全套件。

## 适用场景
讲解无线安全演进、安全配置选择和网络安全选择题。

## 常见误解
误以为设置密码就等于安全（弱密码、WPS 漏洞仍可被利用）。误以为 WPA2 和 WPA3 使用相同握手协议。

## 可验证依据
- - IEEE 802.11i-2004 - WPA2 (RSNA) 标准，定义 AES-CCMP 和四次握手。
- IEEE 802.11-2020 - WPA3 引入 SAE (Simultaneous Authentication of Equals) 和 192-bit 安全套件。
- Wi-Fi Alliance WPA3 Specification v3.2。
- 当前状态：`verified: true`（安全机制与 IEEE 标准一致）。

## 关联知识
- [[计算机网络知识库/07_网络安全与无线网络/无线网络安全]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用类比解释安全概念，但不得改变协议事实。
- 文档 Agent：补充 RFC/标准引用后更新 verified 与 last_reviewed。
