---
doc_id: "ALG-CODE-006"
title: "Dijkstra与Bellman-Ford"
doc_type: "code_case"
course: "算法设计与分析"
course_code: "ALG-LLM-WIKI"
chapter: "10_代码案例"
topic: "单源最短路"
keywords: ["最短路", "Dijkstra", "Bellman-Ford", "堆优化", "负权"]
summary: "堆优化 Dijkstra 与 Bellman-Ford 的实现、路径回溯与负权环检测。"
owner_agent: "代码 Agent"
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
tags: ["算法设计与分析", "RAG", "代码案例"]
---

# Dijkstra 与 Bellman-Ford

## 1. 案例目标
实现两种单源最短路算法，理解各自适用条件（非负权 / 允许负权），并支持路径回溯与负权环检测。

## 2. 堆优化 Dijkstra（非负权）

```python
import heapq

def dijkstra(n: int, adj: list[list[tuple[int, int]]], src: int):
    """adj[u] = [(v, w), ...]，边权 w >= 0。返回 (dist, prev)。"""
    INF = float("inf")
    dist = [INF] * n
    prev = [-1] * n
    dist[src] = 0
    heap = [(0, src)]                      # (距离, 结点)
    done = [False] * n
    while heap:
        d, u = heapq.heappop(heap)
        if done[u]:                        # 惰性删除：跳过过期条目
            continue
        done[u] = True
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))
    return dist, prev

def path_to(prev: list[int], v: int) -> list[int]:
    out = []
    while v != -1:
        out.append(v)
        v = prev[v]
    return out[::-1]

adj = [[(1, 2), (2, 5)],            # 0
       [(2, 1), (3, 6)],            # 1
       [(3, 2)],                    # 2
       []]                          # 3
dist, prev = dijkstra(4, adj, 0)
print(dist)                 # [0, 2, 3, 5]
print(path_to(prev, 3))     # [0, 1, 2, 3]
```

时间 $O((n+m)\log n)$；正确性依赖边权非负的贪心不变量。

## 3. Bellman-Ford（支持负权）

```python
def bellman_ford(n: int, edges: list[tuple[int, int, int]], src: int):
    """edges = [(u, v, w), ...]，允许负权。返回 (dist, prev) 或 None（负环）。"""
    INF = float("inf")
    dist = [INF] * n
    prev = [-1] * n
    dist[src] = 0
    for _ in range(n - 1):                 # 最多 n-1 轮松弛
        changed = False
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                prev[v] = u
                changed = True
        if not changed:                    # 提前收敛
            break
    for u, v, w in edges:                  # 第 n 轮仍可松弛 → 存在负环
        if dist[u] + w < dist[v]:
            return None
    return dist, prev

edges = [(0, 1, 2), (0, 2, 5), (1, 2, 1), (1, 3, 6), (2, 3, 2)]
print(bellman_ford(4, edges, 0)[0])   # [0, 2, 3, 5]

neg = [(0, 1, 4), (1, 2, -3), (2, 1, -3)]     # 1-2 间负环
print(bellman_ford(3, neg, 0))                # None
```

时间 $O(nm)$；第 $n$ 轮仍能松弛等价于存在源点可达的负环。

## 4. 讨论
1. Dijkstra 中 `done` 数组去掉会怎样？（同一结点可能被重复扩展，结果仍正确但退化）
2. 为什么"路径数最多 n-1 条边"决定了 Bellman-Ford 的轮数？
3. 若只要判负环而不求距离，可用队列优化的 SPFA，比较其最坏复杂度。
