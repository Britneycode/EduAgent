---
doc_id: "ALG-LAB-002"
title: "递归树与Master定理验证实验"
doc_type: "lab"
course: "算法设计与分析"
course_code: "ALG-LLM-WIKI"
chapter: "08_实验与工具"
topic: "递归式验证"
keywords: ["实验", "递归树", "Master定理", "递归计数"]
summary: "用调用计数与自监控递归实测验证 Master 定理三种情形。"
owner_agent: "代码 Agent"
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
tags: ["算法设计与分析", "RAG", "实验"]
---

# 递归树与 Master 定理验证实验

## 1. 实验目的
把"递归式 → 递归树 → $\Theta$ 解"的推理过程做成可测量实验，加深对 Master 定理三种情形的直觉。

## 2. 实验原理
不测墙钟时间，而是**统计关键操作次数**（比较、加法、递归调用展开的结点数），消除常数因子干扰：
- $T(n)=2T(n/2)+n$ → 预期操作数 $\Theta(n\log n)$；
- $T(n)=2T(n/2)+n^2$ → 预期 $\Theta(n^2)$（情形 3，根结点主导）；
- $T(n)=2T(n/2)+1$ → 预期 $\Theta(n)$（情形 1，叶结点主导）。

## 3. 实验内容

### 步骤 1：带计数的递归函数

```python
counter = {"ops": 0, "nodes": 0}

def rec(n: int, leaf_cost: int, root_cost) -> None:
    """root_cost(n) 返回根结点代价（如 n、n**2、1）。"""
    counter["nodes"] += 1
    if n <= 1:
        counter["ops"] += leaf_cost
        return
    counter["ops"] += root_cost(n)
    rec(n // 2, leaf_cost, root_cost)
    rec(n // 2, leaf_cost, root_cost)
```

### 步骤 2：收集数据并归一化

```python
import math

def measure(root_cost, name: str):
    print(f"--- T(n)=2T(n/2)+{name} ---")
    for n in (2**10, 2**12, 2**14):
        counter.update(ops=0, nodes=0)
        rec(n, 1, root_cost)
        # 归一化：除以理论函数，观察是否趋于常数
        print(f"n={n:6d} ops={counter['ops']:10d} "
              f"ops/(n log n)={counter['ops']/(n*math.log2(n)):6.3f} "
              f"nodes/n={counter['nodes']/n:6.3f}")

measure(lambda n: n, "n")          # 情形2: ops/(nlogn) → 常数
measure(lambda n: n * n, "n^2")    # 情形3: ops/n^2 → 常数
measure(lambda n: 1, "1")          # 情形1: nodes/n → 常数
```

### 步骤 3：画递归树
对 $T(n)=2T(n/2)+n$ 手画 $n=8$ 的递归树：逐层代价 $8,8,4\times2,\dots$，层数 $\log n$，验证"逐层相等 → 情形 2"。

## 4. 实验报告要求
1. 三个递归式的"归一化比值随 n 变化"表；
2. 说明每种情形下代价集中在哪一层（根/均匀/叶）；
3. 讨论：$T(n)=2T(n/2)+n\log n$ 为什么 Master 定理不适用（$f(n)$ 不是多项式与 $n^{\log_b a}$ 可比），用本实验方法实测其阶（$\Theta(n\log^2 n)$）。

## 5. 思考题
1. 若递归分成 3 份（$T(n)=3T(n/2)+n$），情形如何变化？
2. 递归深度 $\log n$ 与栈溢出：把 $n$ 提到 $2^{30}$ 会发生什么？
