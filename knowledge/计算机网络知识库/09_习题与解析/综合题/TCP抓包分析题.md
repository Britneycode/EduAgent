---
doc_id: "CN-Q-CASE-001"
title: "TCP抓包分析题"
doc_type: "exercise_set"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "09_习题与解析"
section: ""
topic: "TCP抓包分析题"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["综合题", "TCP抓包", "分析", "解析"]
aliases: ["TCP抓包分析题"]
summary: "结合 TCP 抓包现象分析连接建立、释放、重传和窗口变化。"
learning_goals: ["掌握题目涉及的核心概念", "能够区分正确与错误表述", "能够解释答案的理论依据"]
prerequisites: []
related_docs: []
related_concepts: ["综合题", "TCP抓包", "分析", "解析"]
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
owner_agent: "题库 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
  embedding_hints: ["综合题", "TCP抓包", "分析", "解析", "TCP抓包分析题"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "expanded"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG", "题库"]
---

# TCP抓包分析题

## 题集定位
结合 TCP 抓包实际现象设计的综合分析题，培养协议分析和故障定位能力。

## 题目 1：三次握手分析
**题干：** 在 Wireshark 中观察到以下 TCP 报文序列：

| 编号 | 源 | 目的 | 标志 | Seq | Ack |
|---|---|---|---|---|---|
| 1 | 192.168.1.10 | 10.0.0.1 | SYN | 0 | 0 |
| 2 | 10.0.0.1 | 192.168.1.10 | SYN,ACK | 0 | 1 |
| 3 | 192.168.1.10 | 10.0.0.1 | ACK | 1 | 1 |

请回答：这次连接建立过程是否正常？每个报文的作用是什么？

**解析：**
- 报文 1：客户端发送 SYN，请求建立连接，初始序号 0。
- 报文 2：服务器回复 SYN+ACK，确认客户端序号，同时发送自己的初始序号 0。
- 报文 3：客户端发送 ACK，确认服务器序号。连接进入 ESTABLISHED 状态。
- 过程正常，是标准三次握手。见 [[计算机网络知识库/99_附录/事实卡/TCP三次握手]]。

## 题目 2：四次挥手分析
**题干：** 观察到以下 TCP 报文序列：

| 编号 | 源 | 目的 | 标志 | 说明 |
|---|---|---|---|---|
| 1 | 客户端 | 服务器 | FIN,ACK | 请求关闭 |
| 2 | 服务器 | 客户端 | ACK | 确认关闭 |
| 3 | 服务器 | 客户端 | FIN,ACK | 服务器也关闭 |
| 4 | 客户端 | 服务器 | ACK | 最终确认 |

请问：哪一方进入 TIME_WAIT 状态？为什么？

**解析：**
主动关闭方（客户端）进入 TIME_WAIT 状态。TIME_WAIT 的作用是：(1) 确保最后一个 ACK 能到达服务器；(2) 等待网络中残余报文过期。见 [[计算机网络知识库/05_运输层/TCP连接管理]] 和 [[计算机网络知识库/99_附录/事实卡/TCP四次挥手]]。

## 题目 3：重传与窗口
**题干：** 在抓包中发现客户端连续发送了序号为 1000、2000、3000 的三个数据段，但只收到对序号 1000 的确认。随后客户端重新发送了序号 2000 的数据段。请解释发生了什么。

**解析：**
服务器可能只成功接收了序号 1000 的数据段，序号 2000 和 3000 的数据段丢失或校验错误。客户端在超时后重传序号 2000 的数据段（快重传还可能由 3 个重复 ACK 触发）。这体现了 TCP 的可靠传输机制。见 [[计算机网络知识库/05_运输层/TCP]] 和 [[计算机网络知识库/99_附录/事实卡/TCP可靠传输]]。
