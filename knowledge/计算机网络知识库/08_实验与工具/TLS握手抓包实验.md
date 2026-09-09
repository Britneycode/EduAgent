---
doc_id: "CN-LAB-007"
title: "TLS握手抓包实验"
doc_type: "lab"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "08_实验与工具"
section: ""
topic: "TLS握手抓包实验"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["TLS握手抓包实验", "实验"]
aliases: ["TLS握手抓包实验"]
summary: "通过 Wireshark 观察 TLS 握手过程中的 ClientHello、ServerHello 和密钥交换。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["TLS握手抓包实验", "实验"]
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
  embedding_hints: ["TLS握手抓包实验", "实验", "TLS握手抓包实验"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# TLS握手抓包实验

## 1. 实验目标
通过 Wireshark 观察 TLS 握手过程中的 ClientHello、ServerHello 和密钥交换。

## 2. 实验环境
- 操作系统：Windows / macOS / Linux 均可。
- 工具：Wireshark、命令行终端。
- 数据记录：保存命令输出、截图、pcap 文件名与观察时间。

## 3. 操作步骤
1. 启动 Wireshark，设置过滤器 `tls` 或 `ssl`。
2. 用浏览器访问一个 HTTPS 网站。
3. 观察 TLS ClientHello（支持的密码套件、SNI）和 ServerHello（选定的密码套件、证书）。
4. 记录 TLS 版本、密码套件、证书颁发者。
5. 对比 TLS 1.2 和 TLS 1.3 握手流程差异（如有条件）。

## 4. 数据记录模板
| 时间 | 操作 | 观察结果 | 对应知识点 | 证据文件 |
|---|---|---|---|---|
| 待填 | 待填 | 待填 | 待填 | 待填 |

## 5. 验收标准
- 能说清观察现象属于哪一层协议。
- 能引用至少一个相关事实卡。
- 能说明工具输出的局限性。

## 6. 相关链接
- [[计算机网络知识库/08_实验与工具/Wireshark基础]]
- [[计算机网络知识库/99_附录/事实卡/Wireshark抓包流程]]
