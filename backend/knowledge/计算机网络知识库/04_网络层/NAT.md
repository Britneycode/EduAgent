---
doc_id: "CN-K-025"
title: "NAT网络地址转换"
doc_type: "knowledge"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "04_网络层"
section: ""
topic: "NAT"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "hard"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["NAT", "私有地址", "NAPT", "端口映射"]
aliases: ["NAT", "网络地址转换"]
summary: "说明 NAT 的作用、私有地址空间、NAPT 端口映射机制以及 NAT 的局限。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["NAT", "私有地址", "端口映射"]
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
owner_agent: "文档 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
  embedding_hints: ["NAT", "私有地址", "NAPT", "端口映射", "地址转换"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# NAT网络地址转换

## 1. 学习目标
- 理解为什么需要 NAT（IPv4 地址枯竭与私有地址空间）。
- 掌握静态 NAT、动态 NAT 与 NAPT（端口地址转换）的区别。
- 能够描述 NAT 表的工作流程与典型转发过程。
- 认识 NAT 对端到端通信、P2P 应用的局限。

## 2. 核心概念
NAT（Network Address Translation）在边界路由器上把内部私有地址与外部公网地址之间做映射，使内网主机共享少量公网地址访问互联网。

## 3. 知识讲解

### 3.1 私有地址空间（RFC 1918）
- `10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16` 为私有地址，公网不路由。
- 私网主机要访问公网，必须通过 NAT 或代理。

### 3.2 NAT 的三种形式
- **静态 NAT**：一个私有地址固定映射一个公网地址，常用于对外提供服务的内网服务器。
- **动态 NAT**：私有地址动态占用公网地址池，地址不够时无法同时上网。
- **NAPT（端口地址转换）**：多个私有地址共享一个公网 IP，用**端口号**区分不同的内网会话。家用路由器默认使用 NAPT。

### 3.3 NAPT 工作流程（以内网→公网为例）
1. 内网主机 `192.168.1.10:5000` 向 `203.0.113.8:80` 发起连接。
2. NAT 路由器改写源地址为公网 IP `203.0.113.1`，并分配一个端口（如 `40000`），在 NAT 表记录映射 `(192.168.1.10:5000) ↔ (203.0.113.1:40000)`。
3. 公网服务器回复 `203.0.113.1:40000 → 203.0.113.8:80` 方向的报文。
4. 路由器查 NAT 表，把目的改写回 `192.168.1.10:5000`，转交内网主机。

### 3.4 NAT 的局限
- **破坏端到端原则**：外部无法主动发起对内部主机的连接。
- P2P、FTP 主动模式、IPsec 等需要特殊处理（端口转发、ALG、UDP 打洞等）。
- 会话映射有超时，长期无流量可能被清除。

## 4. 关键事实
- 家用宽带路由器普遍使用 NAPT，实现"一个公网 IP 全家上网"。
- NAT 表同时记录源地址与源端口（五元组部分信息）用于反向改写。
- 动态 NAT 需要地址池；NAPT 只需要一个公网 IP 即可支撑大量内网主机。

## 5. 易混淆点
- 不要把"公网 IP"与"私有 IP"混淆：私网地址不可在公网路由。
- 静态 NAT 不等于端口转发：端口转发通常指把公网特定端口映射到内网特定主机的特定端口。
- NAT 不是安全功能本身，但它隐藏了内网结构，具备一定"屏蔽"效果。

## 6. 相关资源
- 实验：[[计算机网络知识库/08_实验与工具/NAT抓包实验]]
- 代码：[[计算机网络知识库/10_代码案例/NAT表模拟]]
- 媒体：[[计算机网络知识库/11_媒体资源/动画脚本/NAT工作原理动画]]
