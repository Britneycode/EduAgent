---
doc_id: "ALG-LAB-004"
title: "指数爆炸与NP难问题体验实验"
doc_type: "lab"
course: "算法设计与分析"
course_code: "ALG-LLM-WIKI"
chapter: "08_实验与工具"
topic: "NP难与指数爆炸"
keywords: ["实验", "指数爆炸", "子集枚举", "贪心近似", "NP难"]
summary: "实测枚举、回溯、贪心近似在 0-1 背包/TSP 上的规模极限，体会 NP 难的实际含义。"
owner_agent: "代码 Agent"
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
tags: ["算法设计与分析", "RAG", "实验"]
---

# 指数爆炸与 NP 难问题体验实验

## 1. 实验目的
用可测量的实验理解：为什么 NP 难问题"能算但算不大"，以及近似/启发式如何成为工程出路。

## 2. 实验内容

### 步骤 1：子集枚举的规模极限（0-1 背包精确解）

```python
import itertools, time, random

def knapsack_bruteforce(weights, values, W):
    n = len(weights)
    best = 0
    for mask in range(1 << n):            # 2^n 个子集
        w = v = 0
        for i in range(n):
            if mask >> i & 1:
                w += weights[i]; v += values[i]
        if w <= W:
            best = max(best, v)
    return best

for n in (10, 15, 20, 22, 24, 26):
    ws = [random.randint(1, 50) for _ in range(n)]
    vs = [random.randint(1, 50) for _ in range(n)]
    t0 = time.perf_counter()
    knapsack_bruteforce(ws, vs, sum(ws) // 2)
    print(f"n={n}: {time.perf_counter()-t0:.3f}s")
```

预期：n 每加 1 耗时 ×2——n=26 已需秒级，n=40 需数天。记录自己的"极限 n"。

### 步骤 2：DP 把它拉回伪多项式

用 [[0-1背包与完全背包]] 的 DP 解同一实例（把 n 加到 1000、W=10000），对比耗时。讨论：$O(nW)$ 为什么是"伪多项式"（把 W 换成 10^9 位二进制数试试）。

### 步骤 3：TSP 的贪心与 2-近似

```python
import math, random

def euclid_tsp_greedy(points):
    """最近邻启发式：从 0 出发每次去最近的未访问城市。"""
    n = len(points)
    unvisited = set(range(1, n))
    tour, cur, total = [0], 0, 0.0
    while unvisited:
        nxt = min(unvisited, key=lambda j:
                  math.dist(points[cur], points[j]))
        total += math.dist(points[cur], points[nxt])
        tour.append(nxt); unvisited.remove(nxt); cur = nxt
    total += math.dist(points[cur], points[0])
    return tour, total

pts = [(random.uniform(0, 100), random.uniform(0, 100)) for _ in range(500)]
tour, total = euclid_tsp_greedy(pts)
print("greedy tour length:", total)   # 与 n! 枚举（n>12 即不可行）对比只能靠近似
```

### 步骤 4：与简单下界比较
TSP 有容易计算的下界：MST 的权（生成树 + 回边 ≥ 最优环游）。对同一实例计算 `nx.minimum_spanning_tree` 总权，报告 `greedy/MST` 比值作为"近似度"的粗略感知。

## 3. 实验报告要求
1. "n vs 耗时"的指数增长表（步骤 1）；
2. 精确枚举 / DP / 贪心三者的可解规模与解质量对比表；
3. 回答：P vs NP 未解，为什么工程上已经"假设 P≠NP"地做决策？

## 4. 思考题
1. 0-1 背包的分数背包上界可以证明 1/2-近似或更优的近似比，试着给出证明思路。
2. 把最近邻贪心换成"2-opt 局部改进"，环游长度改善多少？
