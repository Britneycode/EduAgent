---
doc_id: "CN-CODE-006"
title: "ARP表查询"
doc_type: "code_case"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "10_代码案例"
section: ""
topic: "ARP表查询"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["ARP表查询", "代码案例"]
aliases: ["ARP表查询"]
summary: "展示如何使用命令行查看和管理 ARP 缓存表。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["ARP表查询", "代码案例"]
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
owner_agent: "代码 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
  embedding_hints: ["ARP表查询", "代码案例", "ARP表查询"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# ARP表查询

## 1. 案例目标
展示如何使用命令行查看和管理 ARP 缓存表。

## 2. 先修知识
- [[计算机网络知识库/01_基础理论/分层体系结构]]

## 3. 示例代码 / 伪代码
```bash
# 查看 ARP 缓存
arp -a
# Linux 查看
ip neigh show
# Windows 清除 ARP 缓存
arp -d *
# Linux 清除
sudo ip neigh flush all
```

## 4. 运行与观察
- 记录输入、输出和异常。
- 对照协议层次说明代码对应的网络行为。

## 5. 易错点
- 示例代码用于教学，不代表生产级安全与健壮性。
- 网络代码需处理超时、异常、编码和资源释放。

## 6. 相关链接
- [[计算机网络知识库/99_附录/事实卡/ARP]]
- [[计算机网络知识库/04_网络层/ARP_ICMP_IGMP]]
