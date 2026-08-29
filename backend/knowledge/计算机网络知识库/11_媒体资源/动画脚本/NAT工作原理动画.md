---
doc_id: "NAT工作原理动画"
title: "CN-MEDIA-014"
doc_type: "media_resource"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "11_媒体资源"
section: ""
topic: "CN-MEDIA-014"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["动画", "NAT", "NAPT", "地址转换"]
aliases: ["CN-MEDIA-014"]
summary: "展示 NAPT 在内网与公网之间做源地址与端口改写过程的动画脚本。"
learning_goals: ["快速召回标准事实", "支持题库与导师 Agent 给出一致表述"]
prerequisites: []
related_docs: []
related_concepts: ["动画", "NAT"]
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
owner_agent: "媒体 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
  embedding_hints: ["动画", "NAT", "NAPT", "CN-MEDIA-014"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "expanded"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# CN-MEDIA-014

## 1. 资源目标
用动画展示 NAPT 的工作过程：内网主机访问公网时源地址与端口如何改写，回包如何反向映射。

## 2. 内容结构
1. 问题引入：一个公网 IP 如何供全家上网？
2. 分层定位：网络层边界路由器上的地址转换。
3. 核心过程（分镜）：
   - 镜头 1：内网主机 192.168.1.10:5000 → 公网服务器 93.184.216.34:80。
   - 镜头 2：路由器改写源为 203.0.113.1:40001，NAT 表高亮新增一行。
   - 镜头 3：第二个内网主机 192.168.1.20:5000 → 同样改写为 203.0.113.1:40002。
   - 镜头 4：回包到达，查表恢复目标地址，送给正确内网主机。
4. 易错纠偏：NAT 不是安全设备、NAPT 靠端口区分会话、外部无法主动连内网。
5. 小测：判断 NAT 表入站命中的场景。

## 3. 生成提示词钩子
- 风格：清晰、教学化、少文字、多箭头。
- 约束：不得把教学简化当作绝对事实。
- 必须链接相关事实卡与文档。

## 4. 相关链接
- [[计算机网络知识库/04_网络层/NAT]]
- [[计算机网络知识库/08_实验与工具/NAT抓包实验]]
- [[计算机网络知识库/10_代码案例/NAT表模拟]]
