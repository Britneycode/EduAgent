---
doc_id: "CN-CODE-010"
title: "TCP可靠传输模拟"
doc_type: "code_case"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "10_代码案例"
section: ""
topic: "TCP可靠传输模拟"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["TCP可靠传输模拟", "代码案例"]
aliases: ["TCP可靠传输模拟"]
summary: "用 Python 模拟停等协议，展示序号、确认和超时重传。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["TCP可靠传输模拟", "代码案例"]
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
  embedding_hints: ["TCP可靠传输模拟", "代码案例", "TCP可靠传输模拟"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# TCP可靠传输模拟

## 1. 案例目标
用 Python 模拟停等协议，展示序号、确认和超时重传。

## 2. 先修知识
- [[计算机网络知识库/01_基础理论/分层体系结构]]

## 3. 示例代码 / 伪代码
```python
import random, time

def send_packet(seq, loss_prob=0.3):
    lost = random.random() < loss_prob
    if lost:
        print(f"  Packet seq={seq} LOST")
        return False
    print(f"  Packet seq={seq} sent successfully")
    return True

def stop_and_wait(total, loss_prob=0.3):
    seq = 0
    sent = 0
    while sent < total:
        print(f"Sending frame {sent+1}/{total}")
        if send_packet(seq, loss_prob):
            print(f"  ACK {seq} received")
            sent += 1
        else:
            print(f"  Timeout! Retransmitting seq={seq}")
        seq = 1 - seq  # 0/1 alternating

stop_and_wait(5)
```

## 4. 运行与观察
- 记录输入、输出和异常。
- 对照协议层次说明代码对应的网络行为。

## 5. 易错点
- 示例代码用于教学，不代表生产级安全与健壮性。
- 网络代码需处理超时、异常、编码和资源释放。

## 6. 相关链接
- [[计算机网络知识库/05_运输层/TCP]]
- [[计算机网络知识库/99_附录/事实卡/TCP可靠传输]]
