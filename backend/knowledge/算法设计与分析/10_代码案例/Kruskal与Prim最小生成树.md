---
doc_id: "ALG-CODE-007"
title: "Kruskal与Prim最小生成树"
doc_type: "code_case"
course: "算法设计与分析"
course_code: "ALG-LLM-WIKI"
chapter: "10_代码案例"
topic: "最小生成树"
keywords: ["最小生成树", "Kruskal", "Prim", "并查集"]
summary: "并查集版 Kruskal 与堆优化 Prim 的实现与对照。"
owner_agent: "代码 Agent"
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
tags: ["算法设计与分析", "RAG", "代码案例"]
---

# Kruskal 与 Prim 最小生成树

## 1. 案例目标
实现两种 MST 算法：Kruskal（按边贪心 + 并查集）与 Prim（按点扩展 + 堆），对照适用场景。

## 2. Kruskal（并查集）

```python
def kruskal(n: int, edges: list[tuple[int, int, int]]):
    """edges = [(w, u, v), ...]（无向）。返回 (总权, 边集)；图不连通返回 None。"""
    parent = list(range(n))
    rank = [0] * n

    def find(x: int) -> int:               # 路径压缩
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> bool:     # 按秩合并
        rx, ry = find(x), find(y)
        if rx == ry:
            return False                   # 已连通，选边会成环
        if rank[rx] < rank[ry]:
            rx, ry = ry, rx
        parent[ry] = rx
        if rank[rx] == rank[ry]:
            rank[rx] += 1
        return True

    total, mst = 0, []
    for w, u, v in sorted(edges):
        if union(u, v):
            total += w
            mst.append((u, v, w))
            if len(mst) == n - 1:
                break
    return (total, mst) if len(mst) == n - 1 else None

edges = [(1,0,1), (7,0,2), (5,1,2), (4,1,3), (2,2,3), (6,2,4), (3,3,4)]
print(kruskal(5, edges))   # (10, [(1,0,1), (2,2,3), (3,3,4), (4,1,3)])
```

时间 $O(m\log m)$（排序主导）。

## 3. Prim（堆优化）

```python
import heapq

def prim(n: int, adj: list[list[tuple[int, int]]], src: int = 0):
    """adj[u] = [(v, w), ...]。返回 (总权, 边集) 或 None（不连通）。"""
    INF = float("inf")
    best = [INF] * n          # 连入生成树的最小边权
    prev = [-1] * n
    in_tree = [False] * n
    best[src] = 0
    heap = [(0, src)]
    total, mst = 0, []
    while heap:
        w, u = heapq.heappop(heap)
        if in_tree[u]:
            continue
        in_tree[u] = True
        total += w
        if u != src:
            mst.append((prev[u], u, w))
        for v, wv in adj[u]:
            if not in_tree[v] and wv < best[v]:
                best[v] = wv
                prev[v] = u
                heapq.heappush(heap, (wv, v))
    return (total, mst) if all(in_tree) else None

adj = [[(1,1),(2,7)], [(0,1),(2,5),(3,4)], [(0,7),(1,5),(3,2),(4,6)],
       [(1,4),(2,2),(4,3)], [(2,6),(3,3)]]
print(prim(5, adj))   # (10, [(0,1,1), (1,3,4), (3,2,2), (3,4,3)])
```

时间 $O(m\log n)$；朴素版（邻接矩阵每次扫描最小键）为 $O(n^2)$，稠密图更优。

## 4. 对照

| | Kruskal | Prim |
|---|---|---|
| 贪心对象 | 全局边权排序 | 结点的最小入树边 |
| 中间状态 | 森林 | 一棵生长的树 |
| 复杂度 | $O(m\log m)$ | $O(m\log n)$ / $O(n^2)$ |
| 适用 | 稀疏图 | 稠密图（邻接矩阵版） |

## 5. 讨论
1. 用"切割性质"解释两种算法每一步选边为什么安全。
2. 若图有 $n-k$ 个连通分量，怎样修改以求"最小生成森林"？
