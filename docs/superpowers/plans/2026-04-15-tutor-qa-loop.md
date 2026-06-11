# Tutor 答疑闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为聊天主链路新增 Tutor 答疑闭环：支持基于当前会话资源的继续追问、最近 quiz 自动纠错、无资源时的 Wiki 兜底问答，并保持现有 SSE 协议与持久化边界。

**Architecture:** 在现有 `Orchestrator` 统一入口中新增 Tutor 分支，路由层改为输出 `response_mode + route_tags + tutor_mode`，由 `Orchestrator` 负责 Tutor 上下文组装、token 流式发送、完整 assistant message 聚合与持久化。`TutorAgent` 只负责基于已组装上下文生成中文答疑文本；quiz 自动纠错依赖 `QuizAgent` 先收敛固定输出协议，保证最近一题可以被稳定解析。

**Tech Stack:** Python 3.12、FastAPI、Pydantic v2、SQLAlchemy、现有 SSE chat 协议、uv、pytest、ruff。

---

## 文件结构与职责

### 新增文件
- `backend/app/agents/tutor_agent.py` — TutorAgent：仅负责根据已组装的 Tutor 上下文生成中文答疑文本。
- `backend/app/agents/resource_types.py` — Tutor 上下文组装与 quiz 解析需要的轻量类型定义（如果当前未实现完整内容，则在本任务中补齐并收敛）。
- `backend/tests/test_agents/test_tutor_agent.py` — TutorAgent prompt 与输出约束单测。

### 修改文件
- `backend/app/agents/router_agent.py` — 扩展 RouteDecision 与 Tutor 路由规则。
- `backend/app/agents/orchestrator.py` — 新增 Tutor 分支、上下文组装、异常语义、assistant message 聚合持久化。
- `backend/app/agents/quiz_agent.py` — 收敛最近一题可解析的固定文本协议，支撑 Tutor 自动纠错。
- `backend/app/api/chat.py` — 注入 TutorAgent，保持 API 层薄，避免外层重复补发 Tutor 错误事件。
- `backend/tests/test_agents/test_orchestrator.py` — 新增 Tutor 主链路与失败语义测试。
- `backend/tests/test_agents/test_quiz_agent.py` — 锁定 quiz 固定文本协议与上游契约。
- `backend/tests/test_api/test_chat_api.py` — 新增 Tutor SSE 响应测试。

### 可直接复用的现有文件/接口
- `backend/app/schemas/chat.py` — 复用现有 `agent_status / token / done / error / resource_card / profile_updated` SSE 协议，不新增 tutor 专属事件。
- `backend/app/services/chat_service.py` — 复用 `save_message(...)` 持久化 Tutor 最终 assistant 回复；继续复用 `save_resource(...)` 持久化 document/quiz/code。

---

## 实现原则

1. **不新增 tutor 资源类型**：Tutor 回复只保存为 chat assistant message，不写入 `generated_resources`。
2. **不新增 tutor 专属 SSE 事件**：Tutor 成功链路固定为 `agent_status -> token... -> done`。
3. **clarification 也是正常成功回复**：`tutor_mode == "clarification"` 仍走标准 Tutor 成功链路并持久化 assistant message。
4. **部分 token 后失败必须在 Orchestrator 内部截断并吞异常**：避免 `api/chat.py` 外层兜底再次补发 `error`。
5. **quiz 自动纠错以前置契约为先**：若 recent quiz 无法稳定解析出最后一题的 `question / options / answer / explanation`，Tutor 不进入自动判分，只能退化为解释型答复或短澄清。
6. **严格 YAGNI**：第一版不引入独立 TutorContextBuilder，不纳入 Planner 编排，不做长期记忆或复杂教学状态机。

---

### Task 1: 收敛 Router 路由协议，支持 Tutor 主分支

**Files:**
- Modify: `backend/app/agents/router_agent.py`
- Test: `backend/tests/test_agents/test_orchestrator.py`

- [ ] **Step 1: 先为新路由语义写失败测试或断言入口**

在 `backend/tests/test_agents/test_orchestrator.py` 里补一个最小路由覆盖用例，至少断言以下三类输入能走到后续正确主分支：

```python
def test_router_like_tutor_request_flows_into_tutor_branch() -> None:
    events = asyncio.run(_collect_events(_build_orchestrator(), "这道题我选 B，对吗"))
    assert events[0].type == "agent_status"
```

目标不是在这里详测 Router 细节，而是先让现有 Orchestrator 测试暴露：旧版 `generate_document` 布尔模型已不足以表达 Tutor 分支。

- [ ] **Step 2: 运行定向测试确认旧结构不满足需求**

Run:
`uv run pytest tests/test_agents/test_orchestrator.py -k tutor -v`

Expected: FAIL，原因应指向当前无 Tutor 分支或 RouteDecision 字段不足。

- [ ] **Step 3: 最小化重构 `RouteDecision` 结构**

在 `backend/app/agents/router_agent.py` 中把旧的布尔表达升级成显式主分支模型。目标结构：

```python
@dataclass(slots=True)
class RouteDecision:
    update_profile: bool
    topic: str
    resource_types: list[str]
    response_mode: Literal["resource_generation", "tutor", "none"]
    route_tags: list[Literal["profile", "resource_generation", "tutor"]]
    tutor_mode: Literal["explanation", "follow_up", "correction", "clarification"] | None = None
```

同时实现这些规则：
- 纯画像请求：`response_mode == "none"`
- 明显生成请求：`response_mode == "resource_generation"`
- 明显答疑请求：`response_mode == "tutor"`
- 模糊学习型请求优先归到 Tutor
- 有强画像信号时只作为附加 tag，不单独成为主响应模式

- [ ] **Step 4: 把 Tutor 路由判定写成小而清晰的规则函数**

推荐在 `RouterAgent` 内增加私有辅助方法，而不是把所有关键词堆到 `route()`：

```python
def _detect_response_mode(self, text: str) -> Literal["resource_generation", "tutor", "none"]:
    ...

def _detect_tutor_mode(self, text: str) -> str | None:
    ...

def _build_route_tags(self, update_profile: bool, response_mode: str) -> list[str]:
    ...
```

其中 `tutor_mode` 至少覆盖：
- `correction`：如“我选 B，对吗”
- `clarification`：不在 Router 硬判；这是 Tutor 内部上下文组装阶段的结果，因此 Router 对模糊问题通常先给 `tutor + follow_up/explanation` 候选即可
- `follow_up`：如“再讲一下”“这一题我还是不会”
- `explanation`：如“什么是链式法则”

注意：Router 只做轻量、保守判定，不引入复杂 NLP。

- [ ] **Step 5: 回填/更新现有资源生成默认逻辑**

在保留当前 document/quiz/code 学习包行为的前提下，确保：

```python
resource_types = ["document", "quiz", "code"] if response_mode == "resource_generation" else []
```

不要再以 `generate_document` 为条件驱动主流程。

- [ ] **Step 6: 运行 Router/Orchestrator 相关测试**

Run:
`uv run pytest tests/test_agents/test_orchestrator.py -v`

Expected: 原有资源生成链路测试仍通过；新增 Tutor 入口测试可能仍失败，但失败点应已前移到 Orchestrator/Tutor 缺失，而不是 RouteDecision 结构不匹配。

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/router_agent.py backend/tests/test_agents/test_orchestrator.py
git commit -m "feat(tutor): 扩展聊天路由支持答疑分支"
```

---

### Task 2: 收敛 Quiz 输出协议，保证最近一题可稳定解析

**Files:**
- Modify: `backend/app/agents/quiz_agent.py`
- Test: `backend/tests/test_agents/test_quiz_agent.py`

- [ ] **Step 1: 先写锁定固定文本协议的失败测试**

在 `backend/tests/test_agents/test_quiz_agent.py` 中新增断言，要求 quiz 内容至少包含一题完整的固定结构：

```python
def test_quiz_agent_uses_fixed_question_option_answer_explanation_format() -> None:
    resource = asyncio.run(
        QuizAgent(llm_client=StubLLMClient()).generate_quiz(
            "反向传播",
            PROFILE,
            document_content="这是上游讲义正文。",
        )
    )
    assert "题目：" in resource.content
    assert "选项：" in resource.content
    assert "答案：" in resource.content
    assert "解析：" in resource.content
```

同时把 Stub LLM 返回内容改成符合目标协议的多题文本，至少最后一题要可稳定切分。

- [ ] **Step 2: 运行定向测试确认旧 prompt/归一化逻辑不满足约束**

Run:
`uv run pytest tests/test_agents/test_quiz_agent.py -v`

Expected: FAIL，暴露当前测试与实现并未锁定固定协议。

- [ ] **Step 3: 修改 QuizAgent prompt，显式要求固定协议输出**

在 `backend/app/agents/quiz_agent.py` 的 `build_prompt(...)` 中把“每道题都附参考答案或解析”收紧成唯一协议，例如：

```python
"3. 每道题必须严格按以下四段输出：题目：... / 选项：... / 答案：... / 解析：...。"
"4. 若是填空题，选项段固定写为：选项：无。"
"5. 至少输出三道题，并确保最后一题同样遵守该格式。"
```

不要支持多种格式；第一版只锁一种协议。

- [ ] **Step 4: 只做必要的内容归一化，不要改写题目结构**

如果当前 `_normalize_content(...)` 会破坏题块分隔，调整为仅补充标题或清理首尾空白，确保不改变 `题目/选项/答案/解析` 的顺序与标记。

- [ ] **Step 5: 更新 Stub 返回值与关键 prompt 断言**

把测试中的 Stub 返回值改成类似：

```text
题目：什么是链式法则？
选项：
A. 一种优化器
B. 多层导数逐层相乘的法则
C. 一种损失函数
D. 一种正则化方法
答案：B
解析：链式法则用于把复合函数的导数拆成逐层相乘。
```

并在 prompt 断言中锁定：
- “题目：”
- “选项：”
- “答案：”
- “解析：”

- [ ] **Step 6: 运行 QuizAgent 单测**

Run:
`uv run pytest tests/test_agents/test_quiz_agent.py -v`

Expected: PASS。

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/quiz_agent.py backend/tests/test_agents/test_quiz_agent.py
git commit -m "feat(tutor): 收敛练习题输出协议支持自动纠错"
```

---

### Task 3: 新增 TutorAgent，只负责生成中文答疑文本

**Files:**
- Create: `backend/app/agents/tutor_agent.py`
- Create/Modify: `backend/app/agents/resource_types.py`
- Test: `backend/tests/test_agents/test_tutor_agent.py`

- [ ] **Step 1: 先写 TutorAgent 的失败测试**

新增 `backend/tests/test_agents/test_tutor_agent.py`，先锁定 prompt 约束，而不是生成正文细节：

```python
class StubTutorLLMClient(BaseLLMClient):
    async def generate_text(self, prompt: str) -> str:
        assert "必须用中文回答" in prompt
        assert "先直接解释，再补一个简短引导问题" in prompt
        assert "最近练习题" in prompt
        return "我先基于刚才这道练习题解释。链式法则的关键是逐层相乘。你想让我再举一个数值例子吗？"
```

至少覆盖：
- explanation 模式
- correction 模式带用户答案与题目内容
- 有 wiki_context 时 prompt 包含知识库补充

- [ ] **Step 2: 运行测试确认文件缺失**

Run:
`uv run pytest tests/test_agents/test_tutor_agent.py -v`

Expected: FAIL with `ModuleNotFoundError` 或 `ImportError`。

- [ ] **Step 3: 在 `resource_types.py` 中定义轻量上下文类型**

如果 `backend/app/agents/resource_types.py` 目前不存在或内容不完整，在这里定义最小可用类型，不要过度抽象：

```python
from dataclasses import dataclass
from typing import Literal

TutorMode = Literal["explanation", "follow_up", "correction", "clarification"]

@dataclass(slots=True)
class TutorContext:
    topic: str
    profile: dict[str, str] | None
    recent_document: str | None
    recent_quiz: str | None
    recent_code: str | None
    wiki_context: str | None
    tutor_mode: TutorMode
    quiz_answer_guess: str | None = None
```

只放类型，不放业务逻辑。

- [ ] **Step 4: 实现最小 TutorAgent**

在 `backend/app/agents/tutor_agent.py` 中参考现有 Agent 风格实现：

```python
class TutorAgent:
    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client or get_default_llm_client()

    async def generate_reply(self, user_message: str, context: TutorContext) -> str:
        prompt = self.build_prompt(user_message, context)
        return (await self.llm_client.generate_text(prompt)).strip()
```

`build_prompt(...)` 必须明确写入：
- 必须用中文回答
- 优先围绕当前会话资源解释
- 不足时再补 Wiki
- 先直接解释，再补一个简短引导问题
- correction 模式需输出“判断结果 + 原因 + 正确思路”
- 不输出英文小节标题，不输出协议文本

- [ ] **Step 5: 让 prompt 根据上下文做最小分支**

例如：

```python
if context.tutor_mode == "correction":
    parts.append("这是一次练习题纠错请求，请明确说明判断结果、原因和正确思路。")
if context.recent_quiz:
    parts.extend(["最近练习题：", context.recent_quiz])
if context.wiki_context:
    parts.extend(["知识库补充：", context.wiki_context])
```

不要在 TutorAgent 里查询数据库、解析 quiz、发 SSE 或保存消息。

- [ ] **Step 6: 运行 TutorAgent 单测**

Run:
`uv run pytest tests/test_agents/test_tutor_agent.py -v`

Expected: PASS。

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/tutor_agent.py backend/app/agents/resource_types.py backend/tests/test_agents/test_tutor_agent.py
git commit -m "feat(tutor): 新增答疑生成 Agent"
```

---

### Task 4: 在 Orchestrator 中实现 Tutor 分支与上下文组装

**Files:**
- Modify: `backend/app/agents/orchestrator.py`
- Modify: `backend/app/agents/resource_types.py`
- Test: `backend/tests/test_agents/test_orchestrator.py`

- [ ] **Step 1: 先写 Orchestrator 的 Tutor 失败测试**

在 `backend/tests/test_agents/test_orchestrator.py` 里新增这些测试骨架：

```python
def test_orchestrator_tutor_success_streams_agent_status_tokens_and_done() -> None:
    ...

def test_orchestrator_profile_only_request_emits_profile_updated_then_done() -> None:
    ...

def test_orchestrator_tutor_does_not_emit_resource_card() -> None:
    ...

def test_orchestrator_tutor_pre_token_failure_emits_error_without_done() -> None:
    ...

def test_orchestrator_tutor_partial_token_failure_stops_without_error_or_done() -> None:
    ...
```

这里要通过 Stub tutor agent / stub chat service 精确控制：
- 成功输出
- 首 token 前抛错
- token 发送过程中抛错
- save_message 失败但仍 done

- [ ] **Step 2: 运行定向测试确认旧 Orchestrator 缺少 Tutor 分支**

Run:
`uv run pytest tests/test_agents/test_orchestrator.py -k tutor -v`

Expected: FAIL。

- [ ] **Step 3: 扩展 Orchestrator 构造函数依赖**

在 `backend/app/agents/orchestrator.py` 构造函数中新增 `tutor_agent`：

```python
def __init__(
    self,
    *,
    router_agent: RouterAgent,
    profile_agent: ProfileAgent,
    planner_agent: PlannerAgent,
    doc_agent: DocAgent,
    quiz_agent: QuizAgent,
    code_agent: CodeAgent,
    tutor_agent: TutorAgent,
    profile_service: ProfileService,
    chat_service: ChatService,
) -> None:
    self.tutor_agent = tutor_agent
```

- [ ] **Step 4: 先实现 `response_mode == "none"` 的纯画像短路**

在 `run()` 中沿用现有画像更新逻辑后，增加：

```python
if decision.response_mode == "none":
    yield done_event(session_id=session_id)
    return
```

注意不要补发 `agent_status`，要保持 spec 里的 `profile_updated -> done`。

- [ ] **Step 5: 抽取 Tutor 上下文组装辅助方法**

在 `Orchestrator` 内新增小而明确的私有方法，不要引入 Builder 类：

```python
async def _build_tutor_context(self, session_id: int, user_message: str, decision: RouteDecision, profile: dict[str, str] | None) -> TutorContext:
    ...
```

至少完成这些职责：
- 从 `generated_resources` 数据源读取当前 `session_id` 最近资源（通过 `ChatService` 现有查询能力，若缺失则在不破坏边界的前提下补最小查询接口）
- 按 `quiz > code > document` 或显式线索锁定主资源类型
- 填充 `recent_document / recent_quiz / recent_code`
- 推导最终 `tutor_mode`
- 提取 `quiz_answer_guess`
- 仅在通用概念问答场景下才允许 Wiki 兜底；题目定位失败优先短澄清

如果当前 `ChatService` 缺少“按 session 获取最近资源”的读接口，可在该类中补一个最小方法并一并测试，但不要顺手扩成通用仓库层。

- [ ] **Step 6: 把 quiz 解析逻辑限制在 Orchestrator 内的小辅助函数**

推荐加 2~3 个私有函数，而不是新建复杂模块：

```python
def _extract_quiz_answer_guess(self, user_message: str) -> str | None:
    ...

def _parse_latest_quiz_item(self, quiz_content: str) -> ParsedQuizItem | None:
    ...

def _build_clarification_reply(self, ...) -> str:
    ...
```

规则：
- 单选题提取唯一字母
- 多选题提取并排序字母集合
- 填空题只做安全的短字符串比对
- 任一关键环节不可靠时进入短澄清或解释型答复

- [ ] **Step 7: 实现 Tutor 成功链路**

在 `run()` 中新增 Tutor 分支：

```python
if decision.response_mode == "tutor":
    yield agent_status_event(
        agent="TutorAgent",
        status="working",
        message="正在辅导讲解",
        session_id=session_id,
    )
    ...
```

随后：
1. 组装上下文
2. 调 `TutorAgent.generate_reply(...)`
3. 按现有 token 拆分逻辑发送 `token`
4. 在 Orchestrator 内聚合完整文本
5. 流结束后 `chat_service.save_message(session_id, role="assistant", content=full_text)`
6. 正常完成则发 `done`

不要发 `resource_card`。

- [ ] **Step 8: 实现 Tutor 失败语义**

按 spec 固定三种情况：

```python
try:
    reply = await self.tutor_agent.generate_reply(...)
except Exception as exc:
    yield error_event(message=str(exc), session_id=session_id)
    return
```

然后在 token 发送阶段单独区分：
- 首 token 前失败：`agent_status -> error`
- 部分 token 后失败：记录日志、停止流、吞异常、不发 `error`/`done`
- token 全发完但 `save_message` 失败：记录日志，仍发 `done`

实现时可用布尔标志控制：

```python
sent_any_token = False
```

- [ ] **Step 9: 跑通 Orchestrator 全量单测**

Run:
`uv run pytest tests/test_agents/test_orchestrator.py -v`

Expected: PASS，包括原有 document/quiz/code 主链路与新增 Tutor 测试。

- [ ] **Step 10: Commit**

```bash
git add backend/app/agents/orchestrator.py backend/app/agents/resource_types.py backend/tests/test_agents/test_orchestrator.py
git commit -m "feat(tutor): 在编排器中接入答疑分支"
```

---

### Task 5: 更新 API 装配层并补齐 Tutor SSE 测试

**Files:**
- Modify: `backend/app/api/chat.py`
- Modify: `backend/tests/test_api/test_chat_api.py`

- [ ] **Step 1: 先写 Chat API 的 Tutor SSE 失败测试**

在 `backend/tests/test_api/test_chat_api.py` 中新增 stub orchestrator 事件流工厂，覆盖：

```python
async def _tutor_success_events(session_id: int) -> AsyncGenerator[SSEEvent, None]:
    ...

async def _tutor_pre_token_error_events(session_id: int) -> AsyncGenerator[SSEEvent, None]:
    ...

async def _tutor_partial_token_events(session_id: int) -> AsyncGenerator[SSEEvent, None]:
    ...
```

新增断言：
- Tutor 成功流包含 `agent_status`、`token`、`done`
- 不包含 `resource_card`
- 纯画像请求只返回 `profile_updated`、`done`
- 首 token 前失败时最后一个事件为 `error`
- 部分 token 后中断时不存在补发的 `error` 或 `done`

- [ ] **Step 2: 运行 API 定向测试确认当前覆盖缺口**

Run:
`uv run pytest tests/test_api/test_chat_api.py -k tutor -v`

Expected: FAIL。

- [ ] **Step 3: 在 API 装配层注入 TutorAgent**

修改 `backend/app/api/chat.py` 的 `build_orchestrator(...)`：

```python
from app.agents.tutor_agent import TutorAgent
```

并在实例化时传入：

```python
tutor_agent=TutorAgent(),
```

保持 API 层仍只负责：
- 保存 user message
- 创建 orchestrator
- 透传 orchestrator 产出的 SSE

不要把 Tutor assistant message 聚合/保存写到 API 层。

- [ ] **Step 4: 审视 API 外层兜底，不要破坏已有通用错误处理**

这里不要求删除外层 `except`，但要确保新增 Orchestrator Tutor 分支已经在“部分 token 后失败”场景中吞掉异常，因此 API 外层测试不会再看到补发的 `error`。

- [ ] **Step 5: 运行 Chat API 单测**

Run:
`uv run pytest tests/test_api/test_chat_api.py -v`

Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/chat.py backend/tests/test_api/test_chat_api.py
git commit -m "test(tutor): 补齐答疑流式接口覆盖"
```

---

### Task 6: 做集成验证并修正边界问题

**Files:**
- Modify as needed: `backend/app/agents/router_agent.py`
- Modify as needed: `backend/app/agents/quiz_agent.py`
- Modify as needed: `backend/app/agents/tutor_agent.py`
- Modify as needed: `backend/app/agents/orchestrator.py`
- Modify as needed: `backend/app/api/chat.py`
- Modify as needed: `backend/tests/test_agents/test_tutor_agent.py`
- Modify as needed: `backend/tests/test_agents/test_quiz_agent.py`
- Modify as needed: `backend/tests/test_agents/test_orchestrator.py`
- Modify as needed: `backend/tests/test_api/test_chat_api.py`

- [ ] **Step 1: 运行 Tutor 相关最小测试集**

Run:
`uv run pytest tests/test_agents/test_tutor_agent.py tests/test_agents/test_quiz_agent.py tests/test_agents/test_orchestrator.py tests/test_api/test_chat_api.py -v`

Expected: PASS。

- [ ] **Step 2: 修正暴露出的边界问题，但不要顺手扩 scope**

只允许修正以下类别问题：
- tutor_mode 判断与 spec 不一致
- clarification 被误当成特殊控制流
- quiz 最近一题解析不稳定
- Tutor 分支意外发出 `resource_card`
- 部分 token 后失败仍向外抛异常

不要趁机新增 Prompt 工具类、ContextBuilder、Planner 集成等第二版设计。

- [ ] **Step 3: 运行全量后端测试**

Run:
`uv run pytest`

Expected: PASS。

- [ ] **Step 4: 运行静态检查**

Run:
`uv run ruff check .`

Expected: PASS。

- [ ] **Step 5: 如有必要运行格式化并复验**

Run:
`uv run ruff format . && uv run ruff check . && uv run pytest`

Expected: 全部 PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/router_agent.py backend/app/agents/quiz_agent.py backend/app/agents/tutor_agent.py backend/app/agents/orchestrator.py backend/app/api/chat.py backend/tests/test_agents/test_tutor_agent.py backend/tests/test_agents/test_quiz_agent.py backend/tests/test_agents/test_orchestrator.py backend/tests/test_api/test_chat_api.py
git commit -m "feat(tutor): 完成答疑闭环最小实现"
```

---

## 额外实现说明

### 关于 `resource_types.py`
如果该文件现在已经承载 `AgentResource` 等共享类型，本次只补 Tutor 所需的轻量 dataclass；不要搬迁现有资源模型，也不要做全仓库类型重构。

### 关于 ChatService 读接口
若 Orchestrator 在实现 Tutor 上下文时缺少“获取当前 session 最近资源”的能力，优先在 `ChatService` 内增加最小读取方法，例如：

```python
def list_recent_resources(self, session_id: int, limit: int = 10) -> list[GeneratedResource]:
    ...
```

但仅在实现确实需要时再加；如果当前已有等价接口，直接复用。

### 关于日志
若现有代码基线已有 logger，复用它记录：
- Tutor 部分 token 后失败
- Tutor `save_message` 失败

不要为了这次任务新增全局日志封装。

---

## 验证清单

完成后必须人工确认以下行为：

1. 输入“我是大三学生，准备考研，基础一般”时，只返回 `profile_updated -> done`。
2. 输入“帮我复习反向传播并给我练习题和代码示例”时，仍按原顺序产出 `document -> quiz -> code` 三张资源卡。
3. 输入“给我讲一下什么是链式法则”时，走 Tutor 分支，返回 `agent_status -> token... -> done`，无 `resource_card`。
4. 输入“这道题我选 B，对吗”时，如最近 quiz 可解析，则 Tutor 输出判断结果、原因与正确思路。
5. 输入“还是不懂，再讲一下”且最近资源不明确时，Tutor 返回短澄清；clarification 仍作为正常 assistant message 持久化。
6. Tutor 首 token 前失败时，客户端只看到一次 `error`。
7. Tutor 部分 token 后失败时，客户端看不到补发的 `error` 或 `done`。
8. Tutor 全部 token 已发送但 `save_message` 失败时，客户端仍以 `done` 结束。

---

## 推荐执行顺序

1. Task 1：先把 Router 分支语义收紧
2. Task 2：再锁定 Quiz 上游协议
3. Task 3：新增 TutorAgent
4. Task 4：接入 Orchestrator 主流程
5. Task 5：补 API 装配与 SSE 测试
6. Task 6：做整体验证与边界修正

这个顺序的原因是：
- 先锁路由和 quiz 契约，能减少后续 Orchestrator 集成时的歧义
- TutorAgent 单独落地后，Orchestrator 接入会更机械
- API 层最后补，能避免反复修改 stub 事件流
