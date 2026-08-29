---
doc_id: "CN-K-028"
title: "虚拟局域网VLAN"
doc_type: "knowledge"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "03_数据链路层"
section: ""
topic: "VLAN"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["VLAN", "广播域", "802.1Q", "Trunk"]
aliases: ["VLAN", "虚拟局域网"]
summary: "说明 VLAN 的作用、广播域划分、802.1Q 标签与 Trunk 链路的基本原理。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["VLAN", "广播域", "802.1Q"]
graph_nodes: ["cn_vlan"]
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
  embedding_hints: ["VLAN", "广播域", "802.1Q", "Trunk"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# 虚拟局域网VLAN

## 1. 学习目标
- 理解 VLAN 解决什么问题（广播域过大、安全隔离、管理）。
- 掌握 VLAN 的工作原理与端口类型（Access / Trunk）。
- 了解 802.1Q 标签格式与跨交换机通信方式。

## 2. 核心概念
VLAN（Virtual Local Area Network）在物理局域网内按逻辑划分多个相互隔离的广播域，属于同一 VLAN 的端口即使物理上分散也可二层互通。

## 3. 知识讲解

### 3.1 为什么需要 VLAN
- 二层网络默认是一个广播域，主机越多广播风暴越严重。
- 部门隔离、安全策略需要把不同用户组分开。
- 物理隔离成本高，VLAN 用软件方式实现逻辑隔离。

### 3.2 VLAN 基本原理
- 交换机按端口所属 VLAN 隔离帧的转发。
- 同 VLAN 内帧正常二层转发；跨 VLAN 通信需要三层设备（路由器或三层交换机）参与路由。

### 3.3 端口类型
- **Access 端口**：属于单个 VLAN，连接终端设备，进出帧不带标签。
- **Trunk 端口**：连接交换机之间（或交换机到路由器），承载多个 VLAN 的帧，帧带 VLAN 标签。
- **Hybrid 端口**：部分帧带标签、部分不带，常用于特殊场景。

### 3.4 802.1Q 标签
- 在以太网帧源 MAC 之后插入 4 字节 VLAN 标签。
- 关键字段：**VID（12 bit，1–4094）**，标识所属 VLAN；还有 Priority 与 TCI。
- Trunk 链路上不同 VLAN 的帧靠 VID 区分。

### 3.5 跨 VLAN 通信
- 主机 A（VLAN10）访问主机 B（VLAN20）：A → 交换机 → 三层网关 → 交换机 → B。
- 常见做法：交换机接口子接口（Router-on-a-Stick）或三层交换机 VLAN 接口。

## 4. 关键事实
- VLAN 标识号范围 1–4094（0 与 4095 保留）。
- Access 端口通常只属于一个 VLAN；Trunk 可承载多个 VLAN。
- 默认 VLAN（通常 VLAN1）往往承载控制与管理流量，建议修改默认 VLAN 提升安全性。

## 5. 易混淆点
- VLAN 是二层隔离，不是三层安全边界；跨 VLAN 流量仍需防火墙/ACL 管控。
- 加了 802.1Q 标签的帧只在 Trunk 链路存在，Access 端口进出的帧是普通以太网帧。
- 不要以为两台交换机物理相连的端口都能通所有 VLAN——Trunk 需显式放行相应 VLAN。

## 6. 相关资源
- 讲解：[[计算机网络知识库/03_数据链路层/MAC地址与交换机]]
- 事实卡：[[计算机网络知识库/99_附录/事实卡/MAC地址]] / [[计算机网络知识库/99_附录/事实卡/交换机转发]]
