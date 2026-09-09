---
doc_id: "ALG-CODE-008"
title: "KMP字符串匹配"
doc_type: "code_case"
course: "算法设计与分析"
course_code: "ALG-LLM-WIKI"
chapter: "10_代码案例"
topic: "KMP"
keywords: ["KMP", "字符串匹配", "前缀函数", "失配"]
summary: "前缀函数计算与 KMP 匹配主过程，含摊还复杂度说明。"
owner_agent: "代码 Agent"
rag:
  chunkable: true
  chunk_strategy: "heading"
  chunk_boundary: "H2"
  retrieval_priority: "high"
tags: ["算法设计与分析", "RAG", "代码案例"]
---

# KMP 字符串匹配

## 1. 案例目标
实现 KMP：前缀函数（失配表）预处理 + 线性匹配，理解"文本指针不回退"。

## 2. 前缀函数

```python
def prefix_function(p: str) -> list[int]:
    """pi[i] = p[0..i] 的最长相等真前后缀长度。"""
    pi = [0] * len(p)
    k = 0
    for i in range(1, len(p)):
        while k > 0 and p[i] != p[k]:
            k = pi[k - 1]            # 沿前缀链回退
        if p[i] == p[k]:
            k += 1
        pi[i] = k
    return pi

print(prefix_function("ababaca"))   # [0, 0, 1, 2, 3, 0, 1]
```

## 3. 匹配主过程

```python
def kmp_search(text: str, pattern: str) -> list[int]:
    if not pattern:
        return []
    pi = prefix_function(pattern)
    hits, k = [], 0
    for i, ch in enumerate(text):
        while k > 0 and ch != pattern[k]:
            k = pi[k - 1]            # 失配：模式串指针回退，文本指针不动
        if ch == pattern[k]:
            k += 1
        if k == len(pattern):
            hits.append(i - len(pattern) + 1)
            k = pi[k - 1]            # 继续找下一个匹配
    return hits

print(kmp_search("ababcababaca", "ababaca"))   # [5]
```

## 4. 复杂度的摊还分析

- 预处理：$O(m)$。`k` 每次最多 +1，回退由 `pi` 链承担，总回退次数 ≤ 总增加次数 ≤ $m$。
- 匹配：同理，`k` 在整个扫描中至多增加 $n$ 次，回退也至多 $n$ 次 → $O(n)$。
- 总计 $O(n+m)$，最坏情况（如 `aaaa…a` 中找 `aaa…ab`）也线性，优于朴素 $O(nm)$。

## 5. 对照：朴素匹配

```python
def naive_search(text: str, pattern: str) -> list[int]:
    n, m = len(text), len(pattern)
    return [i for i in range(n - m + 1) if text[i:i+m] == pattern]
```

用 `text="a"*10**5 + "b"`, `pattern="a"*100 + "b"` 对比两者耗时，直观感受最坏差距。

## 6. 讨论
1. 手工推导 `pattern = "aabaab"` 的前缀函数。
2. 循环同构判定：在 `s+s` 中用 KMP 找 `t`，为什么成立？
3. KMP 与 Sunday/Boyer-Moore 的思路差异（前者利用已匹配前缀，后者利用失配字符信息跳跃）。
