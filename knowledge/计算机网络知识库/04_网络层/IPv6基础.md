---
doc_id: "CN-K-027"
title: "IPv6基础"
doc_type: "knowledge"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "04_网络层"
section: ""
topic: "IPv6"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "hard"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["IPv6", "128位地址", "冒号十六进制", "IPv4兼容"]
aliases: ["IPv6", "IPv6基础"]
summary: "说明 IPv6 的地址表示、128 位地址空间、地址类型以及 IPv4 到 IPv6 的差异与过渡。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["IPv6", "地址", "过渡技术"]
graph_nodes: ["cn_ipv6"]
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
  embedding_hints: ["IPv6", "128位地址", "地址表示", "过渡"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# IPv6基础

## 1. 学习目标
- 理解 IPv6 的设计动机与 IPv4 地址枯竭背景。
- 掌握 IPv6 的冒号十六进制表示与压缩规则。
- 认识 IPv6 的主要地址类型（单播、组播、任播）。
- 了解 IPv6 与 IPv4 在报文头与工作机制上的差异。

## 2. 核心概念
IPv6 使用 128 位地址，从根本上扩大地址空间，并简化报文头、内置安全与自动配置能力。

## 3. 知识讲解

### 3.1 为什么需要 IPv6
- IPv4 只有约 43 亿个地址，配合 NAT 只能缓解不能根治。
- 移动设备、物联网（IoT）等需要大量全球唯一地址。

### 3.2 地址表示与压缩
- 128 位写成 8 组 4 位十六进制，组间用冒号分隔，如 `2001:0db8:0000:0000:0000:ff00:0042:8329`。
- **压缩规则**：每组前导零可省；连续的全零组可用 `::` 代替一次。
  - 上面地址压缩为 `2001:db8::ff00:42:8329`。
- 前缀长度写法：`2001:db8::/32`，类似 IPv4 的 CIDR。

### 3.3 地址类型
- **单播（Unicast）**：点对点通信。
  - 链路本地地址 `fe80::/10`，仅用于同一链路，自动配置。
  - 全球单播地址 `2000::/3`。
- **组播（Multicast）**：`ff00::/8`，一对多，替代 IPv4 广播。
- **任播（Anycast）**：多个接口共享地址，路由到"最近"的一个。

### 3.4 IPv6 与 IPv4 的主要差异
- 报文头固定 40 字节，去掉了校验和、无选项字段（扩展头机制）。
- 不再有广播地址，用组播替代。
- 支持无状态地址自动配置（SLAAC），主机可自生成地址。
- 协议字段：IPv4 的"协议"改为"下一个头"。

### 3.5 过渡技术
- **双栈（Dual Stack）**：节点同时运行 IPv4 与 IPv6。
- **隧道（Tunneling）**：IPv6 报文封装在 IPv4 中穿越 IPv4 网络。
- **翻译（Translation）**：NAT64 等实现两种地址族互访。

## 4. 关键事实
- IPv6 地址长度是 IPv4 的 4 倍（128 bit vs 32 bit）。
- `::1` 是 IPv6 环回地址，相当于 IPv4 的 `127.0.0.1`。
- IPv6 移除了首部校验和，依赖下层（链路层）与上层（传输层）保证完整性。

## 5. 易混淆点
- 不要把 IPv6 的 `::` 用在多个位置，压缩规则只允许出现一次。
- IPv6 没有 NAT 的必要，但实际网络中仍可能使用 NAT66/ULAs 做策略隔离。
- 链路本地地址 `fe80::` 不可在路由器间转发。

## 6. 相关资源
- 讲解：[[计算机网络知识库/04_网络层/IP协议]]
- 事实卡：[[计算机网络知识库/99_附录/事实卡/IP协议]]
