---
doc_id: "NAT转换过程图"
title: "CN-MEDIA-015"
doc_type: "media_resource"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "11_媒体资源"
section: ""
topic: "CN-MEDIA-015"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["图示", "NAT", "地址转换"]
aliases: ["CN-MEDIA-015"]
summary: "用于展示 NAPT 出站改写与入站恢复的示意图说明。"
learning_goals: ["快速召回标准事实", "支持题库与导师 Agent 给出一致表述"]
prerequisites: []
related_docs: []
related_concepts: ["图示", "NAT"]
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
  embedding_hints: ["图示", "NAT", "CN-MEDIA-015"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "expanded"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# CN-MEDIA-015

## 1. 资源目标
绘制一张 NAPT 转换示意图，直观呈现内网私有地址到公网地址、以及端口映射的对应关系。

## 2. 内容结构
1. 画面布局：
   - 左侧内网主机列表（192.168.1.10、192.168.1.20…）。
   - 中间 NAT 路由器 + NAT 表（内网IP:端口 ↔ 公网IP:端口）。
   - 右侧公网服务器（93.184.216.34:80）。
2. 关键标注：
   - 出站方向：源地址/源端口改写。
   - 入站方向：目的地址/目的端口恢复。
   - NAT 表列名与映射行高亮。
3. 配图提示词：清晰箭头、暖色高亮映射行、中文标签。

## 3. 生成提示词钩子
- 风格：简洁、教学化、箭头清晰。
- 约束：标注"私有地址不可在公网路由"。
- 必须链接相关事实卡与文档。

## 4. 相关链接
- [[计算机网络知识库/04_网络层/NAT]]
- [[计算机网络知识库/11_媒体资源/动画脚本/NAT工作原理动画]]
