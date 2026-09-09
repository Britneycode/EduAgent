---
doc_id: "CN-LAB-009"
title: "NAT抓包实验"
doc_type: "lab"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "08_实验与工具"
section: ""
topic: "NAT抓包实验"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "hard"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["NAT", "抓包", "实验"]
aliases: ["NAT抓包实验"]
summary: "通过在路由器出口抓包，观察内网私网地址经 NAT 转换后访问公网的过程。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["NAT", "抓包", "实验"]
graph_nodes: ["cn_nat"]
graph_edges: []
source_level: "teaching_consensus"
sources: []
verified: false
status: "draft"
version: "0.1.0"
created: "2026-05-19"
last_reviewed: "2026-05-19"
reviewer: "待审核"
owner_agent: "代码 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
  embedding_hints: ["NAT", "抓包", "实验", "地址转换"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# NAT抓包实验

## 1. 实验目标
通过在内网出口路由器外侧抓包，观察内网主机使用私网地址访问公网时，源地址被改写为公网 IP 的过程，理解 NAPT 的端口映射。

## 2. 操作步骤
1. 确认实验环境：内网主机（如 192.168.1.10）、NAT 路由器（出口为 203.0.113.1）、公网服务器。
2. 在路由器公网侧接口开启抓包（或使用镜像口/日志），设置过滤 `host 203.0.113.8`。
3. 内网主机访问公网服务器的 HTTP 服务，同时观察路由器 NAT 表变化。
4. 抓取若干会话，记录公网侧报文中的源 IP 与源端口。
5. 对照私网侧抓包（若可在内网侧同时抓）比对源地址的差异。

## 3. 观察要点
- 公网侧报文源地址是公网 IP，而非内网私网地址。
- 多个内网主机并发访问时，靠不同源端口区分，印证 NAPT 端口复用。
- 回包方向目的地址为公网 IP+端口，由 NAT 表反向改写。

## 4. 验收标准
- 能说清 NAT 改写的是源还是目的地址。
- 能解释 NAPT 与静态 NAT 的差别。
- 能引用至少一个相关事实卡或文档。

## 5. 相关链接
- [[计算机网络知识库/04_网络层/NAT]]
- [[计算机网络知识库/08_实验与工具/Wireshark基础]]
- [[计算机网络知识库/99_附录/事实卡/Wireshark抓包流程]]
