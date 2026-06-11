---
doc_id: "CN-K-009"
title: "IP协议"
doc_type: "knowledge"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "04_网络层"
section: ""
topic: "IP协议"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["IP", "IPv4", "数据报", "TTL", "分片"]
aliases: ["IP协议"]
summary: "说明 IP 数据报、无连接尽力而为服务、地址、TTL 与分片基础。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["IP", "IPv4", "数据报", "TTL", "分片"]
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
  embedding_hints: ["IP", "IPv4", "数据报", "TTL", "分片", "IP协议"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# IP协议

## 1. 学习目标
- 理解IP协议的基本定义、作用范围和所在层次。
- 能够用分层模型解释IP协议与相邻知识点的关系。
- 能够基于事实卡、实验或题目验证关键结论。

## 2. 核心概念
IP 提供无连接、尽力而为的数据报传递。

## 3. 知识讲解
IPv4 数据报由首部和数据载荷组成。首部通常 20 字节（无选项时），关键字段包括：

| 字段 | 长度 | 说明 |
|---|---|---|
| 版本 | 4 bit | IPv4 = 4，IPv6 = 6 |
| 首部长度（IHL） | 4 bit | 以 4 字节为单位，最小 5（20 字节） |
| 总长度 | 16 bit | 首部 + 数据，最大 65535 字节 |
| 标识 | 16 bit | 用于分片重组，同一数据报的所有片共享标识 |
| 标志 | 3 bit | DF（不分片）、MF（更多分片） |
| 片偏移 | 13 bit | 以 8 字节为单位，指示本片在原始数据报中的位置 |
| TTL | 8 bit | 每经过一台路由器减 1，到 0 时丢弃并向源发送 ICMP 超时报文 |
| 协议 | 8 bit | 上层协议号：TCP=6，UDP=17，ICMP=1 |
| 源 IP 地址 | 32 bit | 发送方网络层地址 |
| 目的 IP 地址 | 32 bit | 接收方网络层地址 |
| 首部校验和 | 16 bit | 仅校验首部，每跳重新计算 |

TTL 的实际意义不仅是防止环路，还被 traceroute 工具利用来探测路径：发送 TTL 逐跳递增的分组，路由器在 TTL 减为 0 时返回 ICMP 超时报文，从而揭示路径上的路由器地址。

IP 分片发生在中间路由器或源主机（取决于 DF 标志）。目的主机通过标识、源/目的 IP 和协议号识别属于同一原始数据报的片，通过片偏移和 MF 标志重组。分片会增加处理开销和丢包概率（任一片丢失导致整个数据报重传），因此现代网络常使用路径 MTU 发现来避免分片。


## 4. 关键事实
- 本主题应与课程分层模型一起理解，避免脱离上下文记忆术语。
- 未经来源核验的事实保持 `verified: false`，正式教学或考试生成前需要补充教材、RFC 或标准来源。
- 题库 Agent 生成题目时应同时引用章节文档和高优先级事实卡。

## 5. 易混淆点
- 不要把教学简化描述当成所有工程环境下的绝对行为。
- 注意区分协议规范、操作系统实现、抓包观察和应用层表现。


## 6. 导师 Agent 教学提示
- 学生常见困惑：分不清 IP 地址和 MAC 地址的作用域。
- 诊断建议：问"IP 地址在传输过程中会变吗？MAC 地址呢？"来检测理解程度。
- 个性化策略：用"邮政地址 vs 门牌号"类比——IP 地址像邮政编码（端到端），MAC 地址像每段运输的装卸地址（逐跳变化）。

## 7. 例题与解析
**例题：** 请说明IP协议解决的核心问题。
**解析：** 从层次定位、输入输出、关键机制、常见限制四方面作答。

## 8. 实验 / 代码 / 媒体生成钩子
- 实验：可设计 Wireshark 抓包、命令行诊断或协议过程模拟。
- 代码：可生成伪代码、socket 示例或报文字段解析。
- 媒体：可生成流程图、状态图、PPT 大纲或动画脚本。

## 9. 相关链接
- [[计算机网络知识库/00_课程总纲/知识地图]]

## 10. 参考来源
- 待补充：教材章节、RFC、IEEE/IETF 标准、实验截图。
