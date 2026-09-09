---
doc_id: "ALG-CODE-005"
title: "贪心：活动选择与Huffman编码"
doc_type: "code_case"
course: "算法设计与分析"
course_code: "ALG-LLM-WIKI"
chapter: "10_代码案例"
topic: "贪心算法"
keywords: ["贪心", "活动选择", "Huffman", "优先队列"]
summary: "活动选择的区间贪心与 Huffman 编码的堆贪心，附贪心与暴力对照。"
owner_agent: "代码 Agent"
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
tags: ["算法设计与分析", "RAG", "代码案例"]
---

# 贪心：活动选择与 Huffman 编码

## 1. 案例目标
实现两类贪心：区间调度（排序贪心）与哈夫曼树（堆贪心），体会"排序准则即贪心策略"。

## 2. 活动选择（最早结束时间贪心）

```python
def activity_selection(activities: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """activities: [(start, end), ...]，返回最大兼容活动子集。"""
    acts = sorted(activities, key=lambda x: x[1])   # 按结束时间排序
    chosen, last_end = [], float("-inf")
    for s, e in acts:
        if s >= last_end:
            chosen.append((s, e))
            last_end = e
    return chosen

acts = [(1,4),(3,5),(0,6),(5,7),(3,9),(5,9),(6,10),(8,11),(8,12),(2,14),(12,16)]
print(activity_selection(acts))   # [(1,4),(5,7),(8,11),(12,16)]
```

时间 $O(n\log n)$；正确性由交换论证保证（见 [[算法简答题]] 题目 6）。

## 3. Huffman 编码

```python
import heapq
from collections import Counter

class Node:
    __slots__ = ("freq", "sym", "left", "right")

    def __init__(self, freq, sym="", left=None, right=None):
        self.freq, self.sym, self.left, self.right = freq, sym, left, right

    def __lt__(self, other):          # 让 heapq 按频率比较
        return self.freq < other.freq

def huffman_codes(text: str) -> dict[str, str]:
    freq = Counter(text)
    heap = [Node(f, s) for s, f in freq.items()]
    if len(heap) == 1:
        return {heap[0].sym: "0"}
    heapq.heapify(heap)
    while len(heap) > 1:
        a, b = heapq.heappop(heap), heapq.heappop(heap)
        heapq.heappush(heap, Node(a.freq + b.freq, "", a, b))
    root = heap[0]

    codes: dict[str, str] = {}
    def walk(node: Node, path: str):
        if node.sym:
            codes[node.sym] = path
            return
        walk(node.left, path + "0")
        walk(node.right, path + "1")
    walk(root, "")
    return codes

codes = huffman_codes("abracadabra")
print(codes)
# 典型输出（0/1 可能互换）：{'a': '0', 'b': '111', 'r': '101', 'c': '1100',
#                           'd': '1101'}
encoded = "".join(codes[c] for c in "abracadabra")
print(len(encoded), "bits vs 固定编码", 11 * 3, "bits")
```

## 4. 正确性要点
- Huffman 贪心：每次合并频率最小的两棵树。可证存在一棵最优树使频率最小的两字符互为兄弟且位于最深层，故合并它们不破坏最优性（归纳可得全局最优）。
- 活动选择贪心：结束最早的活动可替换任何最优解的第一个活动。

## 5. 讨论
1. 活动选择若改为"选时长最短"或"最早开始"贪心，构造反例。
2. Huffman 树为什么保证是前缀码？（字符都在叶子上）
