---
doc_id: "ALG-MEDIA-PPT-004"
title: "图算法PPT"
doc_type: "media_resource"
course: "算法设计与分析"
course_code: "ALG-LLM-WIKI"
chapter: "11_媒体资源"
topic: "图算法"
keywords: ["PPT", "BFS", "DFS", "最短路", "最小生成树"]
summary: "第 5–7 章合并课堂 PPT 大纲：图遍历、最短路、最小生成树。"
owner_agent: "媒体 Agent"
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
tags: ["算法设计与分析", "RAG", "媒体资源"]
---

# 图算法 PPT 大纲

## 第 1 节：图的表示（2 页）
- 邻接矩阵 vs 邻接表：空间 $O(n^2)$ vs $O(n+m)$，适用密度对比
- 建模示例：地图、社交网络、任务依赖

## 第 2 节：遍历：BFS 与 DFS（4 页）
- BFS 队列动画：逐层扩散，无权图最短路
- DFS 栈/递归动画：深入回退，拓扑排序应用
- 两者访问序对比图（同一张图）

## 第 3 节：单源最短路（5 页）
- Dijkstra 过程动画：结点按距离依次"定型"（贪心不变量）
- 负权反例页：Dijkstra 出错的具体图例
- Bellman-Ford：逐轮松弛表格动画 + 负环检测

## 第 4 节：最小生成树（5 页）
- 生成树与切割性质（证明用图示：任何割中最轻横跨边必在 MST 中）
- Kruskal 动画：边排序 + 并查集合并（森林 → 树）
- Prim 动画：树外结点的"最小入树边"逐步生长
- 两算法对比表：贪心对象、复杂度、适用图密度

## 第 5 节：应用与小结（2 页）
- 应用：导航（最短路）、电网/管网设计（MST）、课程先修（拓扑）
- 练习：手算 Dijkstra 与 Kruskal（对应 [[算法计算题]] 题目 7–8）
