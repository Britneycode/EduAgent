---
doc_id: "CN-K-021"
title: "TLS_SSL"
doc_type: "knowledge"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "07_网络安全与无线网络"
section: ""
topic: "TLS_SSL"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["TLS", "SSL", "HTTPS", "证书", "握手", "加密"]
aliases: ["TLS_SSL"]
summary: "介绍 TLS/SSL 协议栈、握手过程、证书体系和 HTTPS 的安全增强。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["TLS", "SSL", "HTTPS", "证书", "握手", "加密"]
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
owner_agent: "文档 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
  embedding_hints: ["TLS", "SSL", "HTTPS", "证书", "握手", "加密", "TLS_SSL"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# TLS_SSL

## 1. 学习目标
- 理解TLS_SSL的基本定义、作用范围和所在层次。
- 能够解释TLS_SSL的关键机制和典型应用场景。
- 能够识别TLS_SSL相关的常见误解。

## 2. 核心概念
TLS（Transport Layer Security）是为 TCP 连接提供机密性、完整性和身份认证的安全协议。SSL 是其前身，TLS 1.2 和 TLS 1.3 是当前主流版本。

## 3. 知识讲解
TLS 握手过程通常包括：客户端发送支持的密码套件列表和随机数；服务器选择密码套件并发送证书和随机数；双方通过密钥交换算法协商预主密钥（TLS 1.3 使用更简化的握手）；最终生成对称会话密钥用于加密应用数据。数字证书由 CA（证书颁发机构）签发，将公钥与域名绑定。

## 4. 关键事实
- TLS 1.3 简化了握手为 1-RTT，支持 0-RTT 恢复，移除了不安全的密码套件。
- 证书信任链从根 CA → 中间 CA → 终端实体证书。
- 对称加密用于数据传输（性能），非对称加密用于密钥协商和身份认证。

## 5. 易混淆点
- HTTPS = HTTP over TLS，不是全新的协议。
- 证书过期、自签名证书或证书链不完整会导致浏览器警告。
- TLS 可保护传输安全，但不能防止应用层漏洞（如 SQL 注入）。


## 6. 导师 Agent 教学提示
- 学生常见困惑：混淆 TLS 握手和 TCP 握手。
- 诊断建议：问"TLS 握手在 TCP 握手之前还是之后？"
- 个性化策略：先建立 TCP 连接（三次握手），再建立 TLS 安全通道（TLS 握手），最后传输 HTTP 数据。

## 7. 例题与解析
**例题：** 描述 TLS 1.3 相比 TLS 1.2 的主要改进。

## 8. 实验 / 代码 / 媒体生成钩子
- 实验：可设计抓包、命令行或模拟实验。
- 代码：可生成协议实现或安全配置示例。
- 媒体：可生成威胁模型图、加密流程图或状态转换图。

## 9. 相关链接
解析：TLS 1.3 将握手简化为 1-RTT，移除了 RSA 密钥交换和静态 DH，强制使用前向安全的密钥交换，移除了不安全的密码套件。

## 10. 参考来源
- 待补充：教材章节、RFC、NIST/IEEE 标准、OWASP 指南。
