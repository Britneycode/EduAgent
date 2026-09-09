---
doc_id: "CN-CODE-005"
title: "DNS查询示例"
doc_type: "code_case"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "10_代码案例"
section: ""
topic: "DNS查询示例"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["DNS查询示例", "代码案例"]
aliases: ["DNS查询示例"]
summary: "用 Python 标准库演示域名到地址的简单查询。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["DNS查询示例", "代码案例"]
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
  embedding_hints: ["DNS查询示例", "代码案例", "DNS查询示例"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# DNS查询示例

## 1. 案例目标
用 Python 标准库演示域名到地址的简单查询。

## 2. 示例代码 / 伪代码
```python
import socket
print(socket.getaddrinfo("example.com", 80))
```

## 3. 运行与观察
- 记录输入、输出、异常和抓包证据。
- 对照协议层次说明代码调用属于应用 API，真实协议处理由操作系统网络栈完成。

## 4. 易错点
- 示例代码用于教学，不代表生产级安全与健壮性。
- 网络代码需处理超时、异常、编码、资源释放和安全边界。

## 5. 关联事实卡
- [[计算机网络知识库/99_附录/事实卡/TCP三次握手]]
- [[计算机网络知识库/99_附录/事实卡/HTTP请求响应]]
- [[计算机网络知识库/99_附录/事实卡/DNS解析过程]]
