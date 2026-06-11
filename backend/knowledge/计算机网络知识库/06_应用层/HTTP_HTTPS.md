---
doc_id: "CN-K-017"
title: "HTTP_HTTPS"
doc_type: "knowledge"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "06_应用层"
section: ""
topic: "HTTP_HTTPS"
subtopics: []
knowledge_level: "undergraduate"
difficulty: "medium"
audience: ["高等教育学生", "教师", "多智能体学习系统"]
keywords: ["HTTP", "HTTPS", "请求响应", "TLS"]
aliases: ["HTTP_HTTPS"]
summary: "介绍 HTTP 请求响应模型、方法、状态码、报文结构与 HTTPS。"
learning_goals: ["理解核心概念", "解释典型流程", "识别常见误解"]
prerequisites: []
related_docs: []
related_concepts: ["HTTP", "HTTPS", "请求响应", "TLS"]
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
  embedding_hints: ["HTTP", "HTTPS", "请求响应", "TLS", "HTTP_HTTPS"]
quality:
  factual_risk: "medium"
  hallucination_sensitive: true
  needs_citation: true
  completeness: "mvp"
  review_required: true
tags: ["计算机网络", "LLM-Wiki", "RAG"]
---

# HTTP_HTTPS

## 1. 学习目标
- 理解HTTP_HTTPS的基本定义、作用范围和所在层次。
- 能够用分层模型解释HTTP_HTTPS与相邻知识点的关系。
- 能够基于事实卡、实验或题目验证关键结论。

## 2. 核心概念
HTTP 是应用层请求-响应协议，HTTPS 通常指 HTTP over TLS。

## 3. 知识讲解
HTTP 请求报文结构：

```text
请求行：  GET /index.html HTTP/1.1
首部行：  Host: www.example.com
          User-Agent: Mozilla/5.0
          Accept: text/html
          Connection: keep-alive
空行：
消息体：  （GET 请求通常无消息体）
```

HTTP 响应报文结构：

```text
状态行：  HTTP/1.1 200 OK
首部行：  Content-Type: text/html
          Content-Length: 1234
          Date: Thu, 07 May 2026 12:00:00 GMT
空行：
消息体：  <html>...</html>
```

**常见 HTTP 方法：**
- GET：获取资源，安全且幂等。
- POST：提交数据，不幂等。
- PUT：替换资源，幂等。
- DELETE：删除资源，幂等。
- HEAD：只获取首部，不返回消息体。

**常见状态码分类：**
- 1xx：信息性（如 100 Continue）。
- 2xx：成功（200 OK、201 Created、204 No Content）。
- 3xx：重定向（301 永久、302 临时、304 Not Modified）。
- 4xx：客户端错误（400 Bad Request、401 Unauthorized、403 Forbidden、404 Not Found）。
- 5xx：服务器错误（500 Internal Server Error、502 Bad Gateway、503 Service Unavailable）。

**HTTPS 工作原理：** HTTPS 在 TCP 连接建立后、HTTP 通信前插入 TLS 握手。握手完成后，所有 HTTP 数据通过对称加密传输。客户端通过验证服务器证书的签名链来确认服务器身份。证书包含服务器公钥、域名、有效期、颁发者等信息。


## 4. 关键事实
- 本主题应与课程分层模型一起理解，避免脱离上下文记忆术语。
- 未经来源核验的事实保持 `verified: false`，正式教学或考试生成前需要补充教材、RFC 或标准来源。
- 题库 Agent 生成题目时应同时引用章节文档和高优先级事实卡。

## 5. 易混淆点
- 不要把教学简化描述当成所有工程环境下的绝对行为。
- 注意区分协议规范、操作系统实现、抓包观察和应用层表现。


## 6. 导师 Agent 教学提示
- 学生常见困惑：以为 HTTPS 是全新的协议。
- 诊断建议：问"HTTPS 和 HTTP 的请求方法一样吗？"
- 个性化策略：HTTPS = HTTP + TLS，就像普通信件加了一个加密信封。

## 7. 例题与解析
**例题：** 请说明HTTP_HTTPS解决的核心问题。
**解析：** 从层次定位、输入输出、关键机制、常见限制四方面作答。

## 8. 实验 / 代码 / 媒体生成钩子
- 实验：可设计 Wireshark 抓包、命令行诊断或协议过程模拟。
- 代码：可生成伪代码、socket 示例或报文字段解析。
- 媒体：可生成流程图、状态图、PPT 大纲或动画脚本。

## 9. 相关链接
- [[计算机网络知识库/00_课程总纲/知识地图]]

## 10. 参考来源
- 待补充：教材章节、RFC、IEEE/IETF 标准、实验截图。
