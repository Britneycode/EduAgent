# EduAgent 自动评测基线

> 更新时间：2026-05-02

本文档记录 O-17 自动评测集的使用方式和覆盖范围。评测目标不是替代完整人工验收，而是为画像抽取、路由、RAG 命中、题目结构和内容安全建立一组可重复运行的工程基线。

## 运行命令

```bash
cd backend
uv run pytest tests/evals -q
```

如果需要查看每条样例 ID：

```bash
cd backend
uv run pytest tests/evals -vv
```

当前评测不依赖外部 LLM 或讯飞凭证。题目结构评测使用固定 fake LLM 响应，RAG 评测使用本地内存向量库和轻量 embedding，保证本地与 CI 都能稳定复现。

## 覆盖范围

| 类别 | 样例文件 | 覆盖目标 |
|---|---|---|
| 画像抽取 | `backend/tests/evals/fixtures/profile_cases.json` | 专业、年级、学习目标、认知风格、知识基础、学习节奏、编程水平、每周学时 |
| 路由判定 | `backend/tests/evals/fixtures/router_cases.json` | 画像更新、资料生成、Tutor 问答、PPT/动画资源类型选择 |
| RAG 命中 | `backend/tests/evals/fixtures/rag_cases.json` | 混合检索命中、课程隔离、来源片段和置信度 |
| 题目结构 | `backend/tests/evals/fixtures/quiz_payload.json` | 训练模式 settings、选择/判断/简答题结构、答案与解析字段 |
| 内容安全 | `backend/tests/evals/fixtures/safety_cases.json` | SQL/脚本风险过滤、虚构引用提示、低置信度提示 |

## 结果判读

- `uv run pytest tests/evals -q` 会输出通过数量，例如 `11 passed`。
- 单条失败时，pytest 会显示失败样例 ID，例如 `router_document_ppt_animation`。
- 断言信息会包含期望值、实际值和完整输出，便于定位是样例漂移还是实现回归。

## 扩展规则

新增评测样例时优先修改 fixtures，而不是把样例硬编码在测试逻辑里。新增类别时保持以下约束：

- 样例必须可离线运行，不依赖真实 LLM、OCR、TTS 或外部向量服务。
- 断言应验证用户可感知的契约，例如字段结构、资源类型、来源命中和安全提示。
- 失败信息必须能指出具体样例 ID 和偏差字段。
- 需要真实模型评估时，应另建慢速/人工评测通道，不混入当前默认基线。
