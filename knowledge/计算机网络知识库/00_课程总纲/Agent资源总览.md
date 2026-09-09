---
doc_id: "CN-INDEX-004"
title: "Agent资源总览"
doc_type: "index"
course: "计算机网络"
course_code: "CN-LLM-WIKI"
chapter: "00_课程总纲"
topic: "Agent资源总览"
keywords: ["索引", "Dataview", "统计"]
aliases: ["Agent资源总览"]
summary: "按多智能体角色分类展示可调用的知识资源。"
verified: true
status: "active"
version: "0.1.0"
created: "2026-05-07"
last_reviewed: "2026-05-07"
owner_agent: "文档 Agent"
allowed_agents: ["画像 Agent", "文档 Agent", "题库 Agent", "代码 Agent", "媒体 Agent", "导师 Agent"]
rag:
  chunkable: false
  retrieval_priority: "medium"
quality:
  factual_risk: "low"
  hallucination_sensitive: false
  needs_citation: false
  completeness: "expanded"
  review_required: false
tags: ["计算机网络", "LLM-Wiki", "RAG", "索引"]
---

# Agent 资源总览

## 1. 用途
本页按多智能体角色分类展示各 Agent 可调用的知识资源，帮助系统集成时确定资源边界。

## 2. 画像 Agent 可用资源
```dataview
TABLE learning_goals AS "学习目标", difficulty AS "难度", prerequisites AS "先修"
FROM "计算机网络知识库"
WHERE doc_type = "knowledge"
SORT chapter ASC
```

## 3. 题库 Agent 可用资源
```dataview
TABLE summary AS "说明"
FROM "计算机网络知识库"
WHERE contains(tags, "题库") OR doc_type = "fact_card"
SORT file.name ASC
```

## 4. 代码 Agent 可用资源
```dataview
TABLE summary AS "说明"
FROM "计算机网络知识库"
WHERE doc_type = "code_case" OR doc_type = "lab"
SORT file.name ASC
```

## 5. 媒体 Agent 可用资源
```dataview
TABLE summary AS "说明", doc_type AS "类型"
FROM "计算机网络知识库"
WHERE doc_type = "media_resource"
SORT file.name ASC
```

## 6. 导师 Agent 可用资源
```dataview
TABLE summary AS "摘要", difficulty AS "难度"
FROM "计算机网络知识库"
WHERE doc_type = "knowledge" AND contains(file.content, "导师 Agent 教学提示")
SORT chapter ASC
```

## 7. 相关链接
- [[计算机网络知识库/00_课程总纲/知识地图]]
- [[计算机网络知识库/00_课程总纲/知识库说明]]
