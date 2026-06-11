---
doc_id: "CN-GOV-RAG-TEST"
title: "RAG检索测试集"
doc_type: "rag_test_set"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "99_附录"
section: ""
topic: "RAG检索测试集"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["RAG", "检索测试", "验收"]
aliases: ["RAG检索测试集"]
summary: "用于初始验收知识库是否能召回关键事实、章节和多媒体资源。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["RAG", "检索测试", "验收"]
graph_nodes: []
graph_edges: []
source_level: "teaching_consensus"
sources: []
verified: true
status: "active"
version: "0.1.0"
created: "2026-05-07"
last_reviewed: "2026-05-07"
reviewer: "待审核"
owner_agent: "文档 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
  embedding_hints: ["RAG", "检索测试", "验收", "RAG检索测试集"]
quality:
  factual_risk: "low"
  hallucination_sensitive: false
  needs_citation: false
  completeness: "mvp"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# RAG检索测试集

## 1. 检索验收问题
| 编号 | 用户问题 | 期望召回 | 评价要点 |
|---|---|---|---|
| RAG-001 | TCP 为什么需要三次握手？ | [[计算机网络知识库/99_附录/事实卡/TCP三次握手]]、[[计算机网络知识库/05_运输层/TCP连接管理]] | 能说明同步序号和双向通信能力 |
| RAG-002 | 流量控制和拥塞控制有什么区别？ | [[计算机网络知识库/05_运输层/流量控制与拥塞控制]]、[[计算机网络知识库/99_附录/事实卡/流量控制]]、[[计算机网络知识库/99_附录/事实卡/拥塞控制]] | 能区分接收方与网络路径 |
| RAG-003 | 如何计算一个子网的网络地址？ | [[计算机网络知识库/04_网络层/子网划分]]、[[计算机网络知识库/09_习题与解析/计算题/子网划分题]] | 能提到 IP 与掩码按位与 |
| RAG-004 | DNS 查询经过哪些服务器？ | [[计算机网络知识库/06_应用层/DNS]]、[[计算机网络知识库/99_附录/事实卡/DNS解析过程]] | 能区分递归解析器和权威服务器 |
| RAG-005 | Wireshark 怎么观察 TCP 握手？ | [[计算机网络知识库/08_实验与工具/TCP抓包实验]]、[[计算机网络知识库/99_附录/事实卡/Wireshark抓包流程]] | 能给出过滤与标志位观察方法 |

## 2. 评分规则
- 2 分：召回事实卡与章节文档，回答准确并带链接。
- 1 分：只召回部分文档或解释不完整。
- 0 分：未召回关键文档或出现事实错误。

## 3. 缺口记录
将失败问题追加到 [[计算机网络知识库/99_附录/质量检查清单/知识缺口记录]]。
