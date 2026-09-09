---
doc_id: "CN-LAB-010"
title: "DHCP抓包实验"
doc_type: "lab"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "08_实验与工具"
section: ""
topic: "DHCP抓包实验"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["DHCP", "抓包", "实验"]
aliases: ["DHCP抓包实验"]
summary: "通过抓包观察 DHCP 的 DISCOVER、OFFER、REQUEST、ACK 四步交互与租约流程。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["DHCP", "抓包", "实验"]
graph_nodes: ["cn_dhcp"]
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
  embedding_hints: ["DHCP", "抓包", "实验", "DORA"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# DHCP抓包实验

## 1. 实验目标
通过抓包观察 DHCP 四步交互（DISCOVER/OFFER/REQUEST/ACK）以及租约续租过程，理解动态地址分配机制。

## 2. 操作步骤
1. 准备环境：一台 DHCP 服务器（或家用路由器）与一台待接入的客户端。
2. 在客户端侧开启 Wireshark，过滤 `udp.port == 67 || udp.port == 68` 或 `bootp`。
3. 客户端执行"释放并重新获取"地址（Windows: `ipconfig /release` 与 `ipconfig /renew`；Linux: `dhclient -r` 与 `dhclient`）。
4. 观察并记录四步报文：源/目的 IP、源/目的端口、DHCP 消息类型（Option 53）。
5. 可等待租期过半观察续租（单播 Request）或在服务器侧查看租约表。

## 3. 观察要点
- DISCOVER 使用广播（源 0.0.0.0，目的 255.255.255.255，UDP 68→67）。
- OFFER 由服务器发回，携带建议 IP 与租期（Option 51）。
- REQUEST 广播选择服务器；ACK 确认租约。
- 续租阶段（T1 时刻）客户端单播 Request 至服务器。

## 4. 验收标准
- 能说出四步报文的类型与关键字段。
- 能区分 OFFER 与 ACK 的作用。
- 能解释为什么 DISCOVER 是广播。

## 5. 相关链接
- [[计算机网络知识库/04_网络层/DHCP]]
- [[计算机网络知识库/08_实验与工具/Wireshark基础]]
- [[计算机网络知识库/99_附录/事实卡/Wireshark抓包流程]]
