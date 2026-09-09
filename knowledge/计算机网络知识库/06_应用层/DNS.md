---
doc_id: "CN-K-018"
title: "DNS"
doc_type: "knowledge"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "06_应用层"
section: ""
topic: "DNS"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["DNS", "域名解析", "递归查询", "缓存"]
aliases: ["DNS"]
summary: "说明 DNS 的域名解析、资源记录、递归/迭代查询和缓存。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["DNS", "域名解析", "递归查询", "缓存"]
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
  embedding_hints: ["DNS", "域名解析", "递归查询", "缓存", "DNS"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# DNS

## 1. 学习目标
- 理解DNS的基本定义、作用范围和所在层次。
- 能够用分层模型解释DNS与相邻知识点的关系。
- 能够基于事实卡、实验或题目验证关键结论。

## 2. 核心概念
DNS 是分布式、层次化命名系统，把域名映射到 IP 地址等资源记录。

## 3. 知识讲解
DNS 常见资源记录类型：

| 类型 | 说明 | 示例 |
|---|---|---|
| A | 域名 → IPv4 地址 | example.com → 93.184.216.34 |
| AAAA | 域名 → IPv6 地址 | example.com → 2606:2800:220:1:... |
| CNAME | 域名别名 → 另一域名 | www.example.com → example.com |
| MX | 邮件交换记录 | example.com → mail.example.com (优先级 10) |
| NS | 域名服务器记录 | example.com → ns1.example.com |
| TXT | 文本记录 | 用于 SPF、DKIM 等验证 |
| SOA | 起始授权记录 | 区域的管理信息和刷新参数 |

**递归查询 vs 迭代查询：** 客户端到递归解析器通常是递归查询（解析器负责完成全部解析）。递归解析器到各级域名服务器通常是迭代查询（每一步返回下一级服务器地址，由解析器继续查询）。

**DNS 缓存机制：** 每条资源记录有 TTL（生存时间），缓存项在 TTL 过期后需要重新查询。浏览器、操作系统和递归解析器都可能维护缓存。TTL 过长会导致域名变更后长时间不生效；过短会增加查询延迟和服务器负载。

**DNS 安全问题：** DNS 缓存投毒（Cache Poisoning）通过伪造响应污染缓存，将用户重定向到恶意网站。DNSSEC 通过数字签名验证 DNS 响应的真实性和完整性。


## 4. 关键事实
- 本主题应与课程分层模型一起理解，避免脱离上下文记忆术语。
- 未经来源核验的事实保持 `verified: false`，正式教学或考试生成前需要补充教材、RFC 或标准来源。
- 题库 Agent 生成题目时应同时引用章节文档和高优先级事实卡。

## 5. 易混淆点
- 不要把教学简化描述当成所有工程环境下的绝对行为。
- 注意区分协议规范、操作系统实现、抓包观察和应用层表现。


## 6. 导师 Agent 教学提示
- 学生常见困惑：以为浏览器直接问根服务器。
- 诊断建议：问"你在浏览器输入 URL 后，第一个 DNS 查询发给谁？"
- 个性化策略：用"查字典"类比——先查桌面小字典（缓存），没有再去图书馆（递归解析器），图书馆帮你逐级查找。

## 7. 例题与解析
**例题：** 请说明DNS解决的核心问题。
**解析：** 从层次定位、输入输出、关键机制、常见限制四方面作答。

## 8. 实验 / 代码 / 媒体生成钩子
- 实验：可设计 Wireshark 抓包、命令行诊断或协议过程模拟。
- 代码：可生成伪代码、socket 示例或报文字段解析。
- 媒体：可生成流程图、状态图、PPT 大纲或动画脚本。

## 9. 相关链接
- [[计算机网络知识库/00_课程总纲/知识地图]]

## 10. 参考来源
- 待补充：教材章节、RFC、IEEE/IETF 标准、实验截图。
