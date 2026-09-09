---
doc_id: "CN-K-026"
title: "DHCP动态主机配置"
doc_type: "knowledge"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "04_网络层"
section: ""
topic: "DHCP"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["DHCP", "地址分配", "租约", "广播"]
aliases: ["DHCP", "动态主机配置协议"]
summary: "说明 DHCP 的作用、四步交互流程、租约机制以及常见的地址分配方式。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["DHCP", "租约", "地址分配"]
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
owner_agent: "文档 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
  embedding_hints: ["DHCP", "地址分配", "租约", "DISCOVER", "OFFER"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# DHCP动态主机配置

## 1. 学习目标
- 理解 DHCP 的作用与适用场景。
- 掌握 DHCP 四步交互流程（DISCOVER/OFFER/REQUEST/ACK）。
- 理解租约（lease）与续租机制。
- 了解 DHCP 与静态配置的取舍。

## 2. 核心概念
DHCP（Dynamic Host Configuration Protocol）自动为网络中的主机分配 IP 地址、子网掩码、默认网关和 DNS 等配置，减少手工配置与地址冲突。

## 3. 知识讲解

### 3.1 为什么需要 DHCP
- 大规模网络中手工配置易出错、难管理。
- 主机频繁接入/离开（如 Wi-Fi、访客网络）需要动态分配。
- 集中管理地址池，避免地址冲突。

### 3.2 四步交互流程（DORA）
1. **DHCP Discover**：客户端以 `0.0.0.0:68 → 255.255.255.255:67` 广播，寻找 DHCP 服务器。
2. **DHCP Offer**：服务器以广播（或单播）回复提议，给出可用 IP 与租期。
3. **DHCP Request**：客户端广播选择该服务器与地址（告知其他服务器"我不选你"）。
4. **DHCP ACK**：服务器确认，租约生效，客户端应用配置。

### 3.3 租约与续租
- 每个地址有租期（如 24 小时）。
- 到达租期约 50% 时客户端单播 Request 请求续租；服务器可 ACK 续约或拒绝。
- 未续租成功则重新走完整 DORA 流程。

### 3.4 分配方式
- **动态分配**：地址池按需分配，可回收复用（最常见）。
- **自动分配**：首次分配后长期固定。
- **静态绑定**：按 MAC 地址固定分配同一 IP（常用于服务器、打印机）。

### 3.5 DHCP 与中继
- DHCP 依赖广播，默认只在同一广播域内工作。
- 跨网段需要 **DHCP Relay（中继代理）** 把广播报文转发给远端服务器。

## 4. 关键事实
- DHCP 使用 UDP 67（服务器）/ 68（客户端）端口。
- 首次接入的客户端在取得地址前，源地址为 `0.0.0.0`。
- 客户端"忘了"地址只需释放租约或重启网卡；服务器端回收依赖租期。

## 5. 易混淆点
- DHCP 不是 ARP：ARP 解析同网段 IP→MAC，DHCP 分配 IP 地址。
- DHCP Offer 与 ACK 都来自服务器，但含义不同（提议 vs 确认）。
- 未配置 DHCP 中继时，DHCP 无法跨子网工作。

## 6. 相关资源
- 实验：[[计算机网络知识库/08_实验与工具/DHCP抓包实验]]
- 代码：[[计算机网络知识库/10_代码案例/DHCP客户端模拟]]
