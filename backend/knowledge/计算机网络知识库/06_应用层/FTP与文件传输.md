---
doc_id: "CN-K-030"
title: "FTP与文件传输"
doc_type: "knowledge"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "06_应用层"
section: ""
topic: "FTP"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["FTP", "控制连接", "数据连接", "主动模式", "被动模式"]
aliases: ["FTP", "文件传输协议"]
summary: "说明 FTP 的双连接模型、主动/被动模式区别以及 FTP 与 HTTP 文件传输的差异。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["FTP", "控制连接", "数据连接"]
graph_nodes: ["cn_ftp"]
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
  embedding_hints: ["FTP", "控制连接", "数据连接", "主动模式", "被动模式"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# FTP与文件传输

## 1. 学习目标
- 理解 FTP 的双连接模型（控制连接 + 数据连接）。
- 区分主动模式与被动模式的工作方式。
- 了解 FTP 与 HTTP 在文件传输上的差异。
- 认识 FTP 的安全问题与替代方案（SFTP/FTPS）。

## 2. 核心概念
FTP（File Transfer Protocol）使用两条 TCP 连接：一条控制连接传输命令与状态，另一条数据连接传输文件内容。

## 3. 知识讲解

### 3.1 双连接模型
- **控制连接**：客户端主动连接服务器 21 端口，全程保持，传输命令（USER/PASS/LIST/RETR/STOR）与响应码。
- **数据连接**：按需建立，传输目录列表或文件内容，传输完即关闭。

### 3.2 主动模式（Active）
1. 客户端在控制连接上告知服务器自己的数据端口（PORT 命令）。
2. 服务器主动从 20 端口连接客户端的该端口。
- 问题：客户端常在 NAT/防火墙后，服务器无法反向连接客户端。

### 3.3 被动模式（Passive）
1. 客户端发送 PASV 命令。
2. 服务器应答一个端口号，客户端主动连接服务器该端口建立数据连接。
- 优点：无需服务器反向连接客户端，适合 NAT 环境（现代客户端默认）。

### 3.4 FTP 与 HTTP 对比
- FTP 有独立控制通道与状态保持（登录、目录切换）；HTTP 是无状态请求-响应。
- FTP 适合大批量文件管理与断点续传；HTTP 更简单、广泛用于 Web 分发。
- HTTP 也可传文件（如 PUT/POST），但缺少 FTP 的目录管理与身份会话。

### 3.5 安全问题与替代
- FTP 明文传输账号与数据，易被窃听。
- 改进方案：**FTPS**（FTP over TLS）、**SFTP**（基于 SSH 的文件传输，非 FTP 协议）、HTTPS 文件接口。

## 4. 关键事实
- FTP 控制连接端口 21，数据连接端口在主动模式为 20、被动模式由服务器动态指定。
- 主动模式数据连接由服务器发起，被动模式由客户端发起。
- SFTP 不是"FTP 加加密"，而是 SSH 协议的一部分，机制完全不同。

## 5. 易混淆点
- 不要把控制连接与数据连接混为一条连接。
- 被动模式解决了服务器无法回连客户端的问题，但服务器需要开放一段被动端口范围。
- 端口 21 是控制端口；文件数据不走 21。

## 6. 相关资源
- 讲解：[[计算机网络知识库/06_应用层/HTTP_HTTPS]]
- 事实卡：[[计算机网络知识库/99_附录/事实卡/HTTP请求响应]]