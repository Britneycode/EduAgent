---
doc_id: "CN-FACT-027"
title: "DMZ"
doc_type: "fact_card"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "DMZ"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["DMZ", "事实卡", "安全"]
aliases: ["DMZ"]
summary: "DMZ（非军事区）是防火墙保护下的半信任区域，常放置对外服务（如 Web 服务器），位于外部网络和内部网络之间，通过双防火墙或单防火墙多端口实现。"
learning_goals: ["快速召回标准事实", "支持题库与导师 Agent 给出一致表述"]
prerequisites: []
related_docs: []
related_concepts: ["DMZ", "事实卡", "安全"]
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
  embedding_hints: ["DMZ", "事实卡", "安全", "DMZ"]
quality:
  factual_risk: "high"
  hallucination_sensitive: true
  needs_citation: false
  completeness: "expanded"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# DMZ

## 标准表述
DMZ（非军事区）是防火墙保护下的半信任区域，常放置对外服务（如 Web 服务器），位于外部网络和内部网络之间，通过双防火墙或单防火墙多端口实现。

## 适用场景
讲解网络安全架构和防火墙部署。

## 常见误解
误以为 DMZ 是完全安全的区域；DMZ 中的服务器仍可能被攻击，只是限制了对内网的直接访问。

## 可验证依据
- - NIST SP 800-41 Rev. 1 - Guidelines on Firewalls and Firewall Policy，定义 DMZ 架构。
- NIST SP 800-125B - Secure Virtual Network Configuration for Virtual Machine (VM)。
- 谢希仁《计算机网络》（第8版）第7.2节。
- 当前状态：`verified: true`（DMZ 架构与 NIST 指南一致）。

## 关联知识
- [[计算机网络知识库/07_网络安全与无线网络/防火墙]]

## Agent 使用提示
- 题库 Agent：优先从“标准表述”和“常见误解”生成判断题、选择题与错因解析。
- 导师 Agent：用类比解释安全概念，但不得改变协议事实。
- 文档 Agent：补充 RFC/标准引用后更新 verified 与 last_reviewed。
