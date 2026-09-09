---
doc_id: "CN-CODE-013"
title: "DHCP客户端模拟"
doc_type: "code_case"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "10_代码案例"
section: ""
topic: "DHCP客户端模拟"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["DHCP", "代码案例", "租约"]
aliases: ["DHCP客户端模拟"]
summary: "用 Python 状态机模拟 DHCP 四步交互与租约续租流程。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["DHCP", "代码案例", "租约"]
graph_nodes: ["cn_dhcp"]
graph_edges: []
source_level: "teaching_consensus"
sources: []
verified: false
status: "draft"
version: "0.1.0"
created: "2026-05-19"
last_reviewed: "2026-05-19"
reviewer: "待审核"
owner_agent: "代码 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
  embedding_hints: ["DHCP", "代码案例", "租约", "DORA"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# DHCP客户端模拟

## 1. 案例目标
用 Python 状态机模拟 DHCP 客户端的 DISCOVER→OFFER→REQUEST→ACK 四步交互与租期过半续租。

## 2. 先修知识
- [[计算机网络知识库/04_网络层/DHCP]]

## 3. 示例代码 / 伪代码
```python
class DHCPClient:
    """极简 DHCP 客户端状态机模拟。"""

    def __init__(self):
        self.state = "INIT"
        self.ip = None
        self.lease = 0
        self.elapsed = 0

    def step(self, event):
        if self.state == "INIT" and event == "power_on":
            print("发送 DISCOVER（广播 0.0.0.0:68 -> 255.255.255.255:67）")
            self.state = "SELECTING"
        elif self.state == "SELECTING" and event == "receive OFFER":
            print("选择服务器，广播 REQUEST")
            self.state = "REQUESTING"
        elif self.state == "REQUESTING" and event == "receive ACK":
            self.ip = "192.168.1.50"
            self.lease = 24 * 60  # 24 小时（分钟）
            print(f"收到 ACK，绑定 IP {self.ip}，租期 {self.lease} 分钟")
            self.state = "BOUND"
        elif self.state == "BOUND":
            self.elapsed += 1
            # 租期过半触发续租
            if self.elapsed >= self.lease * 0.5:
                print("租期过半，单播 REQUEST 续租")
                self.state = "RENEWING"
        elif self.state == "RENEWING" and event == "receive ACK":
            print("续租成功，继续使用该 IP")
            self.elapsed = 0
            self.state = "BOUND"
        else:
            print(f"状态 {self.state} 收到事件 {event}：忽略")

client = DHCPClient()
for ev in ["power_on", "receive OFFER", "receive ACK"]:
    client.step(ev)
# 模拟时间流逝直到续租
while client.state != "RENEWING":
    client.step("tick")
client.step("receive ACK")
```

## 4. 运行与观察
- 客户端在获得地址前源地址为 0.0.0.0，且 DISCOVER/REQUEST 依赖广播。
- 租期过半（50%）触发续租，对应真实 DHCP 的 T1 时刻行为。
- 思考：如果续租失败，客户端会怎样？

## 5. 相关链接
- [[计算机网络知识库/04_网络层/DHCP]]
- [[计算机网络知识库/08_实验与工具/DHCP抓包实验]]
