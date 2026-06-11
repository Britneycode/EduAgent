# 比赛演示版学习闭环 V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在聊天页内完成“3 题互动小测 → 立即评估 → 动态路径调整 → 资源联动展示”的比赛演示闭环，并保证 Tutor 主输出优先与全链路可降级。

**Architecture:** 以现有 Orchestrator + SSE 为主线，新增 Quiz/Evaluation/Path 三个服务模块与最小持久化表，前端扩展 chatStreamStore 与新增闭环卡片组件来承载互动与联动。

**Tech Stack:** FastAPI + SQLAlchemy(Alembic) + PostgreSQL（后端）；Next.js(App Router) + React + TypeScript + Zustand + Vitest（前端）；SSE（流式事件）。

---

## 0. 关键文件改动总览（先锁定边界）

### 后端（backend/）

**Create:**
- `backend/app/api/quiz.py` — Quiz 作答接口
- `backend/app/schemas/quiz.py` — Quiz 题目/作答/回包 schema
- `backend/app/schemas/evaluation.py` — 评估回包 schema
- `backend/app/schemas/path.py` — 路径回包 schema
- `backend/app/services/quiz_service.py` — 出题/判分/落库
- `backend/app/services/evaluation_service.py` — 评估摘要生成/落库
- `backend/app/services/path_service.py` — 路径分组生成/落库
- `backend/app/services/content_guard.py` — 轻量审核/结构校验/截断
- `backend/app/models/quiz_attempt.py` — quiz_attempts 模型
- `backend/app/models/learning_evaluation.py` — learning_evaluations 模型
- `backend/app/models/learning_path_version.py` — learning_path_versions 模型
- `backend/alembic/versions/<ts>_learning_loop_v2_tables.py` — 迁移
- `backend/tests/test_services/test_evaluation_service.py`
- `backend/tests/test_services/test_path_service.py`

**Modify:**
- `backend/app/api/__init__.py` — 注册 quiz 路由
- `backend/app/agents/quiz_agent.py` — 支持结构化 3 题输出（必要时）
- `backend/app/agents/media_agent.py` — 新增 `diagram` 输出
- `backend/app/agents/resource_types.py` — 补充 `diagram` 类型（若有枚举/校验）
- `backend/app/agents/orchestrator.py` — 支持 `quiz_presented`/增强 `agent_status`
- `backend/app/schemas/chat.py` — 新增 SSE event 类型与 payload
- `backend/app/services/chat_service.py` —（如需）保存资源 metadata 或新增 turn_id 字段

### 前端（frontend/）

**Create:**
- `frontend/src/components/chat/QuizCard.tsx` — 3 题互动小测卡
- `frontend/src/components/chat/EvaluationCard.tsx` — 评估摘要卡
- `frontend/src/components/chat/PathUpdateCard.tsx` — 路径调整卡
- `frontend/src/components/chat/NextActions.tsx` — 下一步行动区
- `frontend/src/lib/quizApi.ts` — 提交作答

**Modify:**
- `frontend/src/lib/types.ts` — 新增 quiz/evaluation/path 结构类型与 `diagram` resource_type
- `frontend/src/lib/sse.ts` — 解析新增 SSE 事件
- `frontend/src/store/chatStreamStore.ts` — turn 状态：quiz/eval/path/nextActions + 高亮联动
- `frontend/src/app/(main)/chat/[sessionId]/page.tsx` — 渲染闭环卡片与提交作答
- `frontend/src/components/chat/ResourceCard.tsx` — 支持 `diagram` 类型标签/默认展开策略
- `frontend/src/app/(main)/path/page.tsx`（若已存在）或对应路径页 — 展示最新 `learning_path_versions`
- `frontend/src/app/(main)/chat/[sessionId]/page.test.tsx` — 关键交互测试升级

---

## Task 1：定义 SSE 新事件与 payload（后端 schema 先行）

**Files:**
- Modify: `backend/app/schemas/chat.py`
- Test: `backend/tests/test_schemas/test_chat_events.py`（若项目已有 schemas 测试目录；否则先跳过）

- [ ] **Step 1: 在 `backend/app/schemas/chat.py` 增加新事件 payload 类型**

新增（示例，按现有文件风格放置）：

```python
from pydantic import BaseModel


class QuizQuestionPayload(BaseModel):
    id: str
    question: str
    options: list[str]


class QuizPresentedPayload(BaseModel):
    turn_id: str
    knowledge_point: str
    questions: list[QuizQuestionPayload]


class EvaluationUpdatePayload(BaseModel):
    turn_id: str
    knowledge_point: str
    score: int
    weak_points: list[str]
    mastery_delta: dict[str, int]
    pace_suggestion: str
    summary: str


class PathUpdatePayload(BaseModel):
    turn_id: str
    goal_topic: str
    mastered: list[str]
    strengthen: list[str]
    next: list[str]
    target: list[str]
    reason_summary: str


class NextActionPayload(BaseModel):
    label: str
    knowledge_point: str | None = None
    resource_id: int | None = None


class NextActionsPayload(BaseModel):
    turn_id: str
    actions: list[NextActionPayload]
```

并新增 `quiz_presented_event(...)` / `evaluation_update_event(...)` / `path_update_event(...)` / `next_actions_event(...)` 事件工厂函数，返回与现有 `SSEEvent` 一致的结构。

- [ ] **Step 2: 运行后端单测（若存在）**

Run: `cd backend && uv run pytest -q`

Expected: 通过或仅在本次新增未覆盖处失败。

- [ ] **Step 3: 如无 schemas 测试体系，至少运行导入检查**

Run: `cd backend && uv run python -c "from app.schemas.chat import QuizPresentedPayload"`

Expected: 无异常。

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/chat.py
git commit -m "feat: 增加学习闭环 SSE 事件 schema"
```

---

## Task 2：新增 3 张表模型 + Alembic 迁移

**Files:**
- Create: `backend/app/models/quiz_attempt.py`
- Create: `backend/app/models/learning_evaluation.py`
- Create: `backend/app/models/learning_path_version.py`
- Create: `backend/alembic/versions/<ts>_learning_loop_v2_tables.py`
- Modify: `backend/app/models/__init__.py`（若有统一导出/metadata 收集）

- [ ] **Step 1: 写迁移前先写模型（最小字段）**

示例（按你们现有 Base/SQLAlchemy async 模式调整）：

```python
from sqlalchemy import BigInteger, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[int] = mapped_column(BigInteger, index=True)
    turn_id: Mapped[str] = mapped_column(Text, index=True)
    knowledge_point: Mapped[str] = mapped_column(Text, index=True)

    quiz_payload: Mapped[dict] = mapped_column(JSONB)
    answers: Mapped[dict] = mapped_column(JSONB)

    score: Mapped[int] = mapped_column(Integer)
    correct_count: Mapped[int] = mapped_column(Integer)
```

另外两表同理，字段来自 spec（JSONB + summary 字段）。

- [ ] **Step 2: 生成 Alembic 迁移**

Run:

```bash
cd backend
uv run alembic revision --autogenerate -m "比赛演示版学习闭环V2数据表"
```

Expected: 生成一个新版本文件，包含 3 张表创建。

- [ ] **Step 3: 应用迁移到本地数据库（若有可用 PG）**

Run:

```bash
cd backend
uv run alembic upgrade head
```

Expected: success。

- [ ] **Step 4: Commit**

```bash
git add backend/app/models backend/alembic/versions
git commit -m "feat: 增加学习闭环V2数据表与模型"
```

---

## Task 3：实现 QuizService（出题 + 判分 + 落库）

**Files:**
- Create: `backend/app/services/quiz_service.py`
- Create: `backend/app/schemas/quiz.py`
- Modify: `backend/app/agents/quiz_agent.py`（若需要结构化生成）
- Test: `backend/tests/test_services/test_quiz_service.py`

- [ ] **Step 1: 写 failing test：判分逻辑最小用例**

`backend/tests/test_services/test_quiz_service.py`

```python
import pytest


def test_grade_single_choice_all_correct():
    questions = [
        {"id": "q1", "answer": "A"},
        {"id": "q2", "answer": "B"},
        {"id": "q3", "answer": "C"},
    ]
    answers = {"q1": "A", "q2": "B", "q3": "C"}

    from app.services.quiz_service import grade_answers

    result = grade_answers(questions, answers)
    assert result["correct_count"] == 3
    assert result["score"] == 100
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd backend && uv run pytest tests/test_services/test_quiz_service.py -q`

Expected: FAIL（找不到模块/函数）。

- [ ] **Step 3: 实现最小 `grade_answers` 与 QuizService 框架**

`backend/app/services/quiz_service.py`

```python
from __future__ import annotations

from typing import Any


def grade_answers(questions: list[dict[str, Any]], answers: dict[str, str]) -> dict[str, int]:
    total = len(questions)
    correct = 0
    for q in questions:
        qid = q.get("id")
        ans = q.get("answer")
        if qid and answers.get(qid) == ans:
            correct += 1
    score = 0 if total == 0 else int(correct / total * 100)
    return {"correct_count": correct, "score": score}
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `cd backend && uv run pytest tests/test_services/test_quiz_service.py -q`

Expected: PASS。

- [ ] **Step 5: 扩展：定义 `QuizPresentedPayload` 的题目结构 schema（Pydantic）**

`backend/app/schemas/quiz.py`

```python
from pydantic import BaseModel


class QuizQuestion(BaseModel):
    id: str
    question: str
    options: list[str]
    answer: str | None = None
    explanation: str | None = None


class QuizPresented(BaseModel):
    turn_id: str
    knowledge_point: str
    questions: list[QuizQuestion]


class QuizAnswerItem(BaseModel):
    question_id: str
    answer: str


class QuizAnswerRequest(BaseModel):
    session_id: int
    turn_id: str
    knowledge_point: str
    answers: list[QuizAnswerItem]
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/quiz_service.py backend/app/schemas/quiz.py backend/tests/test_services/test_quiz_service.py
git commit -m "feat: 增加Quiz判分与基础schema"
```

---

## Task 4：实现 EvaluationService（评估摘要 + 落库）

**Files:**
- Create: `backend/app/services/evaluation_service.py`
- Create: `backend/app/schemas/evaluation.py`
- Test: `backend/tests/test_services/test_evaluation_service.py`

- [ ] **Step 1: 写 failing test：从分数推导 pace 建议与 weak_points**

`backend/tests/test_services/test_evaluation_service.py`

```python

def test_build_evaluation_summary_low_score():
    from app.services.evaluation_service import build_evaluation

    result = build_evaluation(
        knowledge_point="反向传播",
        score=33,
        wrong_points=["链式法则", "梯度"],
    )
    assert result.pace_suggestion
    assert "放慢" in result.pace_suggestion
    assert "链式法则" in result.weak_points
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_services/test_evaluation_service.py -q`

Expected: FAIL。

- [ ] **Step 3: 实现最小 build_evaluation（可演示优先）**

`backend/app/schemas/evaluation.py`

```python
from pydantic import BaseModel


class EvaluationSummary(BaseModel):
    turn_id: str
    knowledge_point: str
    score: int
    weak_points: list[str]
    mastery_delta: dict[str, int]
    pace_suggestion: str
    summary: str
```

`backend/app/services/evaluation_service.py`

```python
from __future__ import annotations

from app.schemas.evaluation import EvaluationSummary


def build_evaluation(*, turn_id: str = "", knowledge_point: str, score: int, wrong_points: list[str]) -> EvaluationSummary:
    if score >= 80:
        pace = "可以适当加快节奏，开始做更难的题。"
    elif score >= 60:
        pace = "节奏合适，建议再巩固一轮薄弱点后继续推进。"
    else:
        pace = "建议放慢节奏，先补齐前置知识并做1-2组基础题。"

    mastery_delta = {knowledge_point: max(-10, min(20, score - 60))}
    summary = f"本轮得分 {score} 分，建议优先巩固：{', '.join(wrong_points[:3]) or '暂无'}。"

    return EvaluationSummary(
        turn_id=turn_id,
        knowledge_point=knowledge_point,
        score=score,
        weak_points=wrong_points[:3],
        mastery_delta=mastery_delta,
        pace_suggestion=pace,
        summary=summary,
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && uv run pytest tests/test_services/test_evaluation_service.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/evaluation_service.py backend/app/schemas/evaluation.py backend/tests/test_services/test_evaluation_service.py
git commit -m "feat: 增加学习评估摘要生成"
```

---

## Task 5：实现 PathService（静态回退 + 基于评估的分组）

**Files:**
- Create: `backend/app/services/path_service.py`
- Create: `backend/app/schemas/path.py`
- Test: `backend/tests/test_services/test_path_service.py`

- [ ] **Step 1: failing test：输出必须包含四组字段**

`backend/tests/test_services/test_path_service.py`

```python

def test_build_path_update_groups_present():
    from app.services.path_service import build_path_update

    result = build_path_update(
        turn_id="t1",
        goal_topic="反向传播",
        prerequisites=["梯度下降", "链式法则"],
        mastered=["梯度下降"],
        weak_points=["链式法则"],
    )

    assert result.target == ["反向传播"]
    assert "梯度下降" in result.mastered
    assert "链式法则" in result.strengthen
    assert result.next
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && uv run pytest tests/test_services/test_path_service.py -q`

Expected: FAIL。

- [ ] **Step 3: 实现最小 build_path_update（演示优先）**

`backend/app/schemas/path.py`

```python
from pydantic import BaseModel


class PathUpdate(BaseModel):
    turn_id: str
    goal_topic: str
    mastered: list[str]
    strengthen: list[str]
    next: list[str]
    target: list[str]
    reason_summary: str
```

`backend/app/services/path_service.py`

```python
from __future__ import annotations

from app.schemas.path import PathUpdate


def build_path_update(
    *,
    turn_id: str,
    goal_topic: str,
    prerequisites: list[str],
    mastered: list[str],
    weak_points: list[str],
) -> PathUpdate:
    strengthen = [p for p in prerequisites if p in weak_points and p not in mastered]
    next_nodes = [p for p in prerequisites if p not in mastered]

    reason = "根据本轮评估结果，已将薄弱点前置巩固，并推荐下一步学习节点。"

    return PathUpdate(
        turn_id=turn_id,
        goal_topic=goal_topic,
        mastered=mastered,
        strengthen=strengthen,
        next=next_nodes[:3] or prerequisites[:3],
        target=[goal_topic],
        reason_summary=reason,
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && uv run pytest tests/test_services/test_path_service.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/path_service.py backend/app/schemas/path.py backend/tests/test_services/test_path_service.py
git commit -m "feat: 增加动态学习路径分组更新"
```

---

## Task 6：实现 Quiz 作答 API（POST /api/quiz/answer）

**Files:**
- Create: `backend/app/api/quiz.py`
- Modify: `backend/app/api/__init__.py`
- Modify: `backend/app/main.py`（若路由注册在此）
- Test: `backend/tests/test_api/test_quiz_api.py`

- [ ] **Step 1: failing test：接口返回 evaluation + path_update**

`backend/tests/test_api/test_quiz_api.py`

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_quiz_answer_returns_evaluation_and_path(async_client: AsyncClient):
    payload = {
        "session_id": 1,
        "turn_id": "t1",
        "knowledge_point": "反向传播",
        "answers": [
            {"question_id": "q1", "answer": "A"},
            {"question_id": "q2", "answer": "B"},
            {"question_id": "q3", "answer": "C"},
        ],
    }
    resp = await async_client.post("/api/quiz/answer", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "evaluation" in data
    assert "path_update" in data
```

说明：`async_client` fixture 需复用现有后端测试基础设施；若项目暂无 API 测试框架，先改为用 `TestClient` 同步测试。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_api/test_quiz_api.py -q`

Expected: FAIL。

- [ ] **Step 3: 实现 API（最小可演示）**

`backend/app/api/quiz.py`（示意，真实实现应注入 service 与 DB session）：

```python
from fastapi import APIRouter

from app.schemas.quiz import QuizAnswerRequest
from app.services.evaluation_service import build_evaluation
from app.services.path_service import build_path_update

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.post("/answer")
async def submit_quiz_answer(req: QuizAnswerRequest):
    # 演示版：先从 req.answers 推断 wrong_points（后续接入 quiz_attempts 真题面）
    wrong_points = []
    score = 60

    evaluation = build_evaluation(turn_id=req.turn_id, knowledge_point=req.knowledge_point, score=score, wrong_points=wrong_points)
    path_update = build_path_update(
        turn_id=req.turn_id,
        goal_topic=req.knowledge_point,
        prerequisites=["梯度下降", "链式法则"],
        mastered=[],
        weak_points=evaluation.weak_points,
    )

    next_actions = [
        {"label": "先看算法流程图解", "knowledge_point": req.knowledge_point},
        {"label": "再做一组基础题", "knowledge_point": req.knowledge_point},
    ]

    return {"evaluation": evaluation.model_dump(), "path_update": path_update.model_dump(), "next_actions": next_actions}
```

注意：此处是为了让测试与前端串起来的最小版本；后续 Task 会把“真实题面/判分/落库”接入。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && uv run pytest tests/test_api/test_quiz_api.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/quiz.py backend/app/api/__init__.py backend/tests/test_api/test_quiz_api.py
git commit -m "feat: 增加Quiz作答接口返回评估与路径更新"
```

---

## Task 7：Orchestrator 下发 quiz_presented 事件（Tutor 必达不受影响）

**Files:**
- Modify: `backend/app/agents/orchestrator.py`
- Modify: `backend/app/agents/quiz_agent.py`（结构化 3 题输出）

- [ ] **Step 1: 增加 turn_id 生成（UUID 字符串）**

在 `Orchestrator.run` 开始处生成 `turn_id`，并在本轮所有事件 payload 中携带。

- [ ] **Step 2: 在 Tutor intro token 之后，调用 QuizAgent 生成 3 题并发送 quiz_presented 事件**

约束：Quiz 失败必须捕获异常，改为发 `agent_status` 降级信息，不中断。

- [ ] **Step 3: 本轮暂不强制落库题面（落库在 Task 9 里补齐）**

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/orchestrator.py backend/app/agents/quiz_agent.py
git commit -m "feat: 聊天流下发互动小测题目卡"
```

---

## Task 8：前端 SSE 解析新增事件 + chatStreamStore 承载 turn 状态

**Files:**
- Modify: `frontend/src/lib/sse.ts`
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/store/chatStreamStore.ts`

- [ ] **Step 1: 在 `frontend/src/lib/types.ts` 增加类型**

```ts
export type ResourceType =
  | "document"
  | "quiz"
  | "code"
  | "mindmap"
  | "ppt"
  | "diagram";

export interface QuizQuestion {
  id: string;
  question: string;
  options: string[];
}

export interface QuizPresented {
  turn_id: string;
  knowledge_point: string;
  questions: QuizQuestion[];
}

export interface EvaluationSummary {
  turn_id: string;
  knowledge_point: string;
  score: number;
  weak_points: string[];
  mastery_delta: Record<string, number>;
  pace_suggestion: string;
  summary: string;
}

export interface PathUpdate {
  turn_id: string;
  goal_topic: string;
  mastered: string[];
  strengthen: string[];
  next: string[];
  target: string[];
  reason_summary: string;
}

export interface NextAction {
  label: string;
  knowledge_point?: string;
  resource_id?: number;
}
```

- [ ] **Step 2: 修改 `frontend/src/lib/sse.ts` 解析新事件**

在现有 handler 基础上新增回调：`onQuizPresented`/`onEvaluationUpdate`/`onPathUpdate`/`onNextActions`。

- [ ] **Step 3: 扩展 store：新增 turnState 字段**

示例：

```ts
turn?: {
  turnId: string;
  knowledgePoint: string;
  quiz?: QuizPresented;
  evaluation?: EvaluationSummary;
  pathUpdate?: PathUpdate;
  nextActions?: NextAction[];
  highlightedKnowledgePoint?: string;
};
```

并新增 actions：`setQuizPresented`、`setEvaluation`、`setPathUpdate`、`setNextActions`、`highlightKnowledgePoint`。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/sse.ts frontend/src/store/chatStreamStore.ts
git commit -m "feat: 前端支持学习闭环 SSE 事件与turn状态"
```

---

## Task 9：前端新增 QuizCard（3 题作答 + 提交）并接入 /api/quiz/answer

**Files:**
- Create: `frontend/src/components/chat/QuizCard.tsx`
- Create: `frontend/src/lib/quizApi.ts`
- Modify: `frontend/src/app/(main)/chat/[sessionId]/page.tsx`

- [ ] **Step 1: 实现 `submitQuizAnswers` API 调用**

`frontend/src/lib/quizApi.ts`

```ts
export async function submitQuizAnswers(payload: {
  session_id: number;
  turn_id: string;
  knowledge_point: string;
  answers: { question_id: string; answer: string }[];
}) {
  const resp = await fetch("/api/quiz/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    throw new Error("提交作答失败");
  }
  return resp.json();
}
```

- [ ] **Step 2: 实现 QuizCard（本地状态收集答案 + 提交）**

`frontend/src/components/chat/QuizCard.tsx`（最小 UI）：

```tsx
"use client";

import { useMemo, useState } from "react";
import type { QuizPresented } from "@/lib/types";

export function QuizCard(props: {
  quiz: QuizPresented;
  onSubmit: (answers: { question_id: string; answer: string }[]) => Promise<void>;
}) {
  const { quiz, onSubmit } = props;
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const canSubmit = useMemo(
    () => quiz.questions.every((q) => Boolean(answers[q.id])) && !submitting,
    [quiz.questions, answers, submitting]
  );

  return (
    <div className="mt-3 rounded-xl bg-[var(--color-parchment)] p-4 ring-1 ring-[var(--color-warm-gray-200)]">
      <div className="mb-2 text-sm font-medium text-[var(--color-warm-gray-800)]">本轮小测（3题）</div>
      <div className="space-y-4">
        {quiz.questions.map((q, idx) => (
          <div key={q.id}>
            <div className="mb-2 text-sm text-[var(--color-warm-gray-700)]">{idx + 1}. {q.question}</div>
            <div className="grid gap-2">
              {q.options.map((opt) => (
                <label key={opt} className="flex cursor-pointer items-center gap-2 rounded-lg bg-[var(--color-ivory)] px-3 py-2 ring-1 ring-[var(--color-warm-gray-200)]">
                  <input
                    type="radio"
                    name={q.id}
                    value={opt}
                    checked={answers[q.id] === opt}
                    onChange={() => setAnswers((prev) => ({ ...prev, [q.id]: opt }))}
                  />
                  <span className="text-sm text-[var(--color-warm-gray-700)]">{opt}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button
        type="button"
        disabled={!canSubmit}
        onClick={async () => {
          setSubmitting(true);
          try {
            const items = Object.entries(answers).map(([question_id, answer]) => ({ question_id, answer }));
            await onSubmit(items);
          } finally {
            setSubmitting(false);
          }
        }}
        className="mt-4 rounded-xl bg-[var(--color-terracotta)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {submitting ? "正在提交..." : "提交作答"}
      </button>
    </div>
  );
}
```

- [ ] **Step 3: 在 chat page 接入 QuizCard 并在 onSubmit 中调用接口，写回 store**

在 `page.tsx` 的 stream handlers 中加入 `onQuizPresented`，并在渲染区域根据 `streamState.turn?.quiz` 渲染 `QuizCard`。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/chat/QuizCard.tsx frontend/src/lib/quizApi.ts frontend/src/app/(main)/chat/[sessionId]/page.tsx
git commit -m "feat: 聊天页支持互动小测作答并提交"
```

---

## Task 10：前端新增 EvaluationCard/PathUpdateCard/NextActions 并实现资源联动高亮

**Files:**
- Create: `frontend/src/components/chat/EvaluationCard.tsx`
- Create: `frontend/src/components/chat/PathUpdateCard.tsx`
- Create: `frontend/src/components/chat/NextActions.tsx`
- Modify: `frontend/src/components/chat/ResourceCard.tsx`
- Modify: `frontend/src/store/chatStreamStore.ts`
- Modify: `frontend/src/app/(main)/chat/[sessionId]/page.tsx`

- [ ] **Step 1: 实现三个卡片组件（只渲染结构化字段）**

要求：全部中文，风格沿用 parchment/ivory。

- [ ] **Step 2: PathUpdateCard 节点点击触发 `highlightKnowledgePoint(kp)`**

- [ ] **Step 3: ResourceCard 支持高亮（当 resource.knowledge_point == highlightedKnowledgePoint）**

示例：外层加 `ring-[var(--color-terracotta)]`。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/chat/EvaluationCard.tsx frontend/src/components/chat/PathUpdateCard.tsx frontend/src/components/chat/NextActions.tsx frontend/src/components/chat/ResourceCard.tsx frontend/src/store/chatStreamStore.ts frontend/src/app/(main)/chat/[sessionId]/page.tsx
git commit -m "feat: 增加评估/路径/下一步卡片与资源联动高亮"
```

---

## Task 11：MediaAgent 新增 diagram 资源类型 + 前端展示标签

**Files:**
- Modify: `backend/app/agents/media_agent.py`
- Modify: `backend/app/agents/orchestrator.py`
- Modify: `frontend/src/components/chat/ResourceCard.tsx`
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: 后端新增 `generate_diagram`**

`media_agent.py` 增加 prompt：输出 Mermaid flowchart 代码块 + 简短说明，全部中文。

- [ ] **Step 2: Orchestrator 支持 resource_type == diagram**

在 `_generate_resource` 分支新增 `diagram`，并在 `PlannerAgent.plan_resources`（或 Router 决策）让比赛版闭环默认包含 `diagram`。

- [ ] **Step 3: 前端 ResourceCard 增加 diagram 标签与配色**

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/media_agent.py backend/app/agents/orchestrator.py frontend/src/components/chat/ResourceCard.tsx frontend/src/lib/types.ts
git commit -m "feat: MediaAgent 支持diagram图解资源"
```

---

## Task 12：后端接入 ContentGuard（结构校验/截断）+ agent_status 增强耗时/降级原因

**Files:**
- Create: `backend/app/services/content_guard.py`
- Modify: `backend/app/agents/orchestrator.py`
- Modify: `backend/app/schemas/chat.py`

- [ ] **Step 1: failing test：Mermaid 必须含代码块，否则降级为纯文本提示**

`backend/tests/test_services/test_content_guard.py`

```python

def test_guard_mermaid_requires_code_block():
    from app.services.content_guard import guard_mermaid

    out, degraded, reason = guard_mermaid("流程图", "这里没有代码块")
    assert degraded is True
    assert "代码块" in reason
    assert "```mermaid" in out
```

- [ ] **Step 2: 实现 `guard_mermaid`**

```python

def guard_mermaid(title: str, content: str) -> tuple[str, bool, str]:
    text = (content or "").strip()
    if "```mermaid" in text:
        return text, False, ""
    fallback = f"```mermaid\nflowchart TD\n  A[\"{title}\"]-->B[\"图解生成失败，请稍后重试\"]\n```\n"
    return fallback, True, "图解内容缺少 Mermaid 代码块，已自动降级。"
```

- [ ] **Step 3: Orchestrator 在发送 resource_card 前调用 guard，并将 degraded 信息写入 agent_status**

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/content_guard.py backend/app/agents/orchestrator.py backend/app/schemas/chat.py backend/tests/test_services/test_content_guard.py
git commit -m "feat: 增加内容结构校验与降级原因上报"
```

---

## Task 13：端到端验证：本地跑通演示场景 1

**Files:**
- Modify（必要时）: 若发现 bug，按最小修复更新

- [ ] **Step 1: 启动后端**

Run:

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Expected: 服务启动成功。

- [ ] **Step 2: 启动前端**

Run:

```bash
cd frontend
pnpm install
pnpm dev
```

Expected: 页面可打开。

- [ ] **Step 3: 演示脚本（反向传播）手动走通**

在聊天里输入：`帮我讲清楚反向传播，并出3道小测题`

Expected:
- Tutor 流式输出出现
- 出现 3 题小测卡，可选答案并提交
- 提交后出现评估摘要卡 + 路径调整卡
- 点击路径“下一步”节点，资源卡出现高亮联动

- [ ] **Step 4: Commit（若有修复）**

按修复文件选择性提交。

---

## 计划自检（对照 spec 覆盖）

- SSE 新事件：Task 1/7/8 覆盖
- 互动小测：Task 7/9 覆盖
- 评估与路径：Task 4/5/6/10 覆盖
- Media diagram：Task 11 覆盖
- 审核/降级/耗时：Task 12 覆盖
- 演示稳定性验证：Task 13 覆盖

---

## 执行交接

计划已保存到 `docs/superpowers/plans/2026-04-20-demo-learning-loop-v2.md`。

两种执行方式：

1. **Subagent-Driven（推荐）**：我按 Task 逐个派发子代理实现，每个 Task 完成后我审查再继续
2. **Inline Execution**：我在当前会话按 Task 执行，分批提交与回归

你选哪一种？
