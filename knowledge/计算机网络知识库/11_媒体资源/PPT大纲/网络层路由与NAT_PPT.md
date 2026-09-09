---
doc_id: "网络层路由与NAT_PPT"
title: "CN-MEDIA-013"
doc_type: "media_resource"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "11_媒体资源"
section: ""
topic: "CN-MEDIA-013"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "hard"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["PPT", "路由", "NAT", "网络层"]
aliases: ["CN-MEDIA-013"]
summary: "面向课堂讲解的网络层路由与 NAT PPT 大纲，涵盖路由算法、NAT 转换与常见误区。"
learning_goals: ["快速召回标准事实", "支持题库与导师 Agent 给出一致表述"]
prerequisites: []
related_docs: []
related_concepts: ["PPT", "路由", "NAT"]
graph_nodes: ["cn_routing", "cn_nat"]
graph_edges: []
source_level: "teaching_consensus"
sources: []
verified: false
status: "draft"
version: "0.1.0"
created: "2026-05-19"
last_reviewed: "2026-05-19"
reviewer: "待审核"
owner_agent: "媒体 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
  embedding_hints: ["PPT", "路由", "NAT", "CN-MEDIA-013"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "expanded"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# CN-MEDIA-013

## 1. 资源目标
面向课堂讲解的网络层路由与 NAT PPT 大纲，涵盖路由 vs 转发、RIP/OSPF/BGP、NAT 转换流程。

## 2. 内容结构
1. 问题引入：为什么数据包能到达目标？NAT 又是怎么"变出"公网地址的？
2. 分层定位：属于网络层，先讲转发与路由的区分。
3. 核心过程：
   - 路由 vs 转发对比表。
   - 距离向量（RIP）vs 链路状态（OSPF）流程示意。
   - NAPT 出站/入站双向改写时间轴。
4. 易错纠偏：RIP 跳数限制、NAT 破坏端到端、最长前缀匹配。
5. 小测：1-2 个检索或判断问题。

## 3. 生成提示词钩子
- 风格：清晰、教学化、少文字、多箭头。
- 约束：不得把教学简化当作绝对事实。
- 必须链接相关事实卡与文档。

## 4. 相关链接
- [[计算机网络知识库/04_网络层/路由算法与协议]]
- [[计算机网络知识库/04_网络层/NAT]]
- [[计算机网络知识库/08_实验与工具/路由表查看与跨网段实验]]
- [[计算机网络知识库/08_实验与工具/NAT抓包实验]]
