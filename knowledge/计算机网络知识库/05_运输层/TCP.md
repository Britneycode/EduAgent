---
doc_id: "CN-K-013"
title: "TCP"
doc_type: "knowledge"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "05_运输层"
section: ""
topic: "TCP"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["TCP", "可靠传输", "字节流", "序号"]
aliases: ["TCP"]
summary: "介绍 TCP 的面向连接、可靠字节流、序号确认、重传和控制机制。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["TCP", "可靠传输", "字节流", "序号"]
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
  embedding_hints: ["TCP", "可靠传输", "字节流", "序号", "TCP"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# TCP

## 1. 学习目标
- 理解TCP的基本定义、作用范围和所在层次。
- 能够用分层模型解释TCP与相邻知识点的关系。
- 能够基于事实卡、实验或题目验证关键结论。

## 2. 核心概念
TCP 是面向连接、可靠、按序、面向字节流的运输层协议。

## 3. 知识讲解
TCP 报文段（segment）首部通常 20 字节，关键字段包括：

| 字段 | 长度 | 说明 |
|---|---|---|
| 源端口 | 16 bit | 发送方进程端口号 |
| 目的端口 | 16 bit | 接收方进程端口号 |
| 序号 | 32 bit | 本报文段数据第一个字节的编号 |
| 确认号 | 32 bit | 期望收到对方下一个字节的编号（累积确认） |
| 数据偏移 | 4 bit | 首部长度，以 4 字节为单位 |
| 标志位 | 6 bit | URG、ACK、PSH、RST、SYN、FIN |
| 窗口 | 16 bit | 接收窗口大小，用于流量控制 |
| 校验和 | 16 bit | 首部 + 数据 + 伪首部校验 |
| 紧急指针 | 16 bit | URG=1 时有效，指示紧急数据末尾位置 |

**序号与确认号机制：** TCP 对字节流中的每个字节编号。发送方在序号字段填入本段数据的起始编号；接收方在确认号字段填入期望收到的下一个字节编号，实现累积确认。例如：发送方发送序号 1000、长度 500 的报文段，接收方回复确认号 1500，表示序号 0-1499 的数据已正确接收。

**滑动窗口：** 接收方通过窗口字段通告其接收缓冲区剩余空间（rwnd）。发送方维护拥塞窗口（cwnd）。实际可发送数据量 = min(rwnd, cwnd)。窗口机制允许连续发送多个报文段而不必逐个等待确认，显著提高吞吐量。

**标志位详解：**
- SYN=1：连接建立请求，携带初始序号。
- ACK=1：确认号字段有效，TCP 连接建立后所有报文段通常 ACK=1。
- FIN=1：请求释放连接。
- RST=1：强制终止连接或拒绝非法报文段。
- PSH=1：提示接收方尽快将数据交付应用层。
- URG=1：紧急指针有效。


## 4. 关键事实
- 本主题应与课程分层模型一起理解，避免脱离上下文记忆术语。
- 未经来源核验的事实保持 `verified: false`，正式教学或考试生成前需要补充教材、RFC 或标准来源。
- 题库 Agent 生成题目时应同时引用章节文档和高优先级事实卡。

## 5. 易混淆点
- 不要把教学简化描述当成所有工程环境下的绝对行为。
- 注意区分协议规范、操作系统实现、抓包观察和应用层表现。


## 6. 导师 Agent 教学提示
- 学生常见困惑：不理解"字节流"与"消息边界"的区别。
- 诊断建议：让学生比较 TCP 和 UDP 发送两次 100 字节数据，接收方分别收到什么。
- 个性化策略：用"水管"类比字节流——数据像水流一样连续到达，不保留发送时的分段。

## 7. 例题与解析
**例题：** 请说明TCP解决的核心问题。
**解析：** 从层次定位、输入输出、关键机制、常见限制四方面作答。

## 8. 实验 / 代码 / 媒体生成钩子
- 实验：可设计 Wireshark 抓包、命令行诊断或协议过程模拟。
- 代码：可生成伪代码、socket 示例或报文字段解析。
- 媒体：可生成流程图、状态图、PPT 大纲或动画脚本。

## 9. 相关链接
- [[计算机网络知识库/00_课程总纲/知识地图]]

## 10. 参考来源
- 待补充：教材章节、RFC、IEEE/IETF 标准、实验截图。
