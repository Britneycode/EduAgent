# Tutor 驱动学习闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为比赛版聊天主链路落地 Tutor 驱动学习闭环，让一次对话可以流式展示 Tutor 主回答、资源卡片、路径调整、评估摘要和下一步建议。

**Architecture:** 保持现有 `Orchestrator` 作为单一编排入口，在后端新增轻量学习回合结构与 SSE 事件，不把复杂逻辑塞进前端。前端继续以聊天页为主舞台，基于现有 Zustand 流式状态扩展出学习回合视图，并确保任何增强模块失败时都不会阻塞 Tutor 主回答。

**Tech Stack:** Python 3.12、FastAPI、Pydantic v2、SQLAlchemy、Next.js App Router、React 19、TypeScript、Zustand、Vitest、pytest、SSE。

---

## 文件结构与职责

### 后端
- Modify: `backend/app/schemas/chat.py` — 扩展比赛版 SSE 事件、学习回合相关 payload 模型。
- Modify: `backend/app/agents/resource_types.py` — 补充学习回合、路径更新、评估摘要、画像变化等轻量类型。
- Modify: `backend/app/agents/router_agent.py` — 继续负责意图识别，但把闭环类请求稳定归到 Tutor 主线可用的 route decision。
- Modify: `backend/app/agents/planner_agent.py` — 从返回 `resource_types` 升级为比赛版闭环规划入口。
- Modify: `backend/app/agents/media_agent.py` — 保留 `mindmap`，新增/强化 `diagram` 输出。
- Modify: `backend/app/agents/tutor_agent.py` — 从单纯答疑改为能汇总学习回合结果的主回答生成器。
- Modify: `backend/app/agents/orchestrator.py` — 编排 Tutor/Media/Path/Evaluation，负责降级与 SSE 下发。
- Modify: `backend/app/api/chat.py` — 继续输出同一 SSE 接口，不新增第二条聊天流接口。
- Create: `backend/app/services/evaluation_service.py` — 根据答题结果和文本反馈生成中等粒度评估摘要。
- Create: `backend/app/services/path_service.py` — 输出分组后的路径摘要与优先推进建议。
- Create: `backend/app/services/learning_turn_service.py` — 组装 `LearningTurnResult`，统一回合级输出。

### 前端
- Modify: `frontend/src/lib/types.ts` — 扩展 `diagram`、路径/评估/画像变化/下一步建议类型与 SSE 事件。
- Modify: `frontend/src/lib/sse.ts` — 解析新增 SSE 事件并分发给聊天页。
- Modify: `frontend/src/store/chatStreamStore.ts` — 保存流式中的路径更新、评估摘要、画像变化、下一步建议。
- Modify: `frontend/src/app/(main)/chat/[sessionId]/page.tsx` — 从“文本 + 资源”升级为“学习回合视图”。
- Modify: `frontend/src/components/chat/ResourceCard.tsx` — 支持 `diagram` 类型与更清晰的资源标签。
- Create: `frontend/src/components/chat/LearningTurnPanel.tsx` — 汇总显示资源区、路径卡、评估卡、下一步建议。
- Create: `frontend/src/components/chat/PathUpdateCard.tsx` — 展示当前目标、已掌握/待巩固/下一步。
- Create: `frontend/src/components/chat/EvaluationSummaryCard.tsx` — 展示掌握度变化、薄弱点、节奏建议。
- Create: `frontend/src/components/chat/ProfileDeltaCard.tsx` — 展示本轮画像变化摘要。
- Create: `frontend/src/components/chat/NextActionsCard.tsx` — 展示可执行下一步建议。
- Modify: `frontend/src/app/(main)/path/page.tsx` — 兼容比赛版路径分组结构，而不是只拼 prerequisites。
- Modify: `frontend/src/app/(main)/chat/[sessionId]/page.test.tsx` — 覆盖回到会话页时学习回合流式状态恢复。
- Create: `frontend/src/lib/sse.test.ts` — 锁定新增 SSE 事件解析行为。

### 测试与基线对齐
- Modify: `backend/tests/test_agents/test_orchestrator.py` — 覆盖学习回合成功链路与降级链路。
- Modify: `backend/tests/test_api/test_chat_api.py` — 覆盖新 SSE 事件与鉴权后的聊天接口行为。
- Modify: `backend/tests/test_agents/test_router_agent.py` — 覆盖 Tutor 闭环类路由输入。
- Modify: `backend/tests/test_agents/test_planner_agent.py` — 覆盖比赛版学习回合规划结果。
- Modify: `backend/tests/test_agents/test_media_agent.py` — 覆盖 `diagram` 资源输出。
- Create: `backend/tests/test_services/test_evaluation_service.py` — 覆盖答题结果 + 文本反馈混合评估。
- Create: `backend/tests/test_services/test_path_service.py` — 覆盖路径分组与优先建议。

---

## 数据契约

### 学习回合结果

```ts
interface LearningTurnResult {
  tutor_response: string;
  resources: ResourceCard[];
  path_update?: PathUpdate;
  evaluation?: EvaluationSummary;
  profile_delta?: ProfileDelta;
  next_actions: string[];
}
```

### 前端类型目标

```ts
export type ResourceType =
  | "document"
  | "quiz"
  | "code"
  | "mindmap"
  | "diagram"
  | "ppt"
  | "animation"
  | "reading";

export interface PathUpdate {
  target_topic: string;
  mastered: string[];
  strengthening: string[];
  next_up: string[];
  priority_suggestion: string;
}

export interface EvaluationSummary {
  mastery_delta: string;
  weak_points: string[];
  pace_advice: string;
  should_adjust_path: boolean;
  recommended_resource_type?: ResourceType;
}

export interface ProfileDelta {
  learning_pace?: string;
  weak_points?: string[];
  confidence_note?: string;
}
```

### 新 SSE 事件目标

```ts
export interface SSEEvent {
  type:
    | "agent_status"
    | "profile_updated"
    | "token"
    | "resource_card"
    | "path_update"
    | "evaluation_update"
    | "profile_delta"
    | "next_actions"
    | "wiki_fallback"
    | "done"
    | "error";
  session_id: number | null;
  payload: Record<string, unknown>;
}
```

---

### Task 1: 先把后端与前端的基础类型扩成闭环可承载结构

**Files:**
- Modify: `backend/app/schemas/chat.py`
- Modify: `backend/app/agents/resource_types.py`
- Modify: `frontend/src/lib/types.ts`
- Test: `frontend/src/lib/sse.test.ts`

- [ ] **Step 1: 先写前端 SSE 类型测试**

```ts
import { describe, expect, it } from "vitest";
import { parseSSEChunk } from "@/lib/sse";

describe("parseSSEChunk", () => {
  it("解析比赛版学习闭环事件", () => {
    const chunk = [
      'data: {"type":"path_update","session_id":1,"payload":{"target_topic":"反向传播","mastered":["导数"],"strengthening":["链式法则"],"next_up":["损失函数"],"priority_suggestion":"先补链式法则"}}',
      "",
      'data: {"type":"next_actions","session_id":1,"payload":{"actions":["先看算法图解","再做一道练习题"]}}',
      "",
    ].join("\n");

    const events = parseSSEChunk(chunk);

    expect(events).toHaveLength(2);
    expect(events[0].type).toBe("path_update");
    expect(events[1].type).toBe("next_actions");
  });
});
```

- [ ] **Step 2: 运行前端定向测试确认当前类型尚未支持**

Run: `pnpm test -- src/lib/sse.test.ts`
Expected: FAIL，原因是现有 `SSEEvent` 和解析分发尚未包含新事件。

- [ ] **Step 3: 扩展后端 SSE schema 与 payload 模型**

在 `backend/app/schemas/chat.py` 增加：

```py
class PathUpdatePayload(BaseModel):
    target_topic: str
    mastered: list[str] = Field(default_factory=list)
    strengthening: list[str] = Field(default_factory=list)
    next_up: list[str] = Field(default_factory=list)
    priority_suggestion: str

class EvaluationSummaryPayload(BaseModel):
    mastery_delta: str
    weak_points: list[str] = Field(default_factory=list)
    pace_advice: str
    should_adjust_path: bool
    recommended_resource_type: str | None = None

class ProfileDeltaPayload(BaseModel):
    learning_pace: str | None = None
    weak_points: list[str] = Field(default_factory=list)
    confidence_note: str | None = None

class NextActionsPayload(BaseModel):
    actions: list[str] = Field(default_factory=list)
```

并把 `SSEEvent.type` 扩成包含：
- `path_update`
- `evaluation_update`
- `profile_delta`
- `next_actions`

- [ ] **Step 4: 扩展后端轻量领域类型**

在 `backend/app/agents/resource_types.py` 中加入：

```py
@dataclass(slots=True)
class PathUpdate:
    target_topic: str
    mastered: list[str]
    strengthening: list[str]
    next_up: list[str]
    priority_suggestion: str

@dataclass(slots=True)
class EvaluationSummary:
    mastery_delta: str
    weak_points: list[str]
    pace_advice: str
    should_adjust_path: bool
    recommended_resource_type: str | None = None

@dataclass(slots=True)
class ProfileDelta:
    learning_pace: str | None = None
    weak_points: list[str] | None = None
    confidence_note: str | None = None

@dataclass(slots=True)
class LearningTurnResult:
    tutor_response: str
    resources: list[AgentResource]
    path_update: PathUpdate | None = None
    evaluation: EvaluationSummary | None = None
    profile_delta: ProfileDelta | None = None
    next_actions: list[str] | None = None
```

- [ ] **Step 5: 扩展前端共享类型**

在 `frontend/src/lib/types.ts` 中补充：

```ts
export interface PathUpdate {
  target_topic: string;
  mastered: string[];
  strengthening: string[];
  next_up: string[];
  priority_suggestion: string;
}

export interface EvaluationSummary {
  mastery_delta: string;
  weak_points: string[];
  pace_advice: string;
  should_adjust_path: boolean;
  recommended_resource_type?: ResourceType;
}

export interface ProfileDelta {
  learning_pace?: string;
  weak_points?: string[];
  confidence_note?: string;
}
```

同时把 `ResourceType` 加入 `diagram`。

- [ ] **Step 6: 运行前端测试确认通过**

Run: `pnpm test -- src/lib/sse.test.ts`
Expected: PASS。

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/chat.py backend/app/agents/resource_types.py frontend/src/lib/types.ts frontend/src/lib/sse.test.ts
git commit -m "feat: 补齐学习闭环基础类型与事件协议"
```

---

### Task 2: 把 SSE 解析器和流式状态扩展成学习回合状态

**Files:**
- Modify: `frontend/src/lib/sse.ts`
- Modify: `frontend/src/store/chatStreamStore.ts`
- Test: `frontend/src/app/(main)/chat/[sessionId]/page.test.tsx`

- [ ] **Step 1: 先写聊天页状态恢复测试**

在 `frontend/src/app/(main)/chat/[sessionId]/page.test.tsx` 增加：

```ts
it("重新进入会话时继续展示学习回合中的路径和评估信息", async () => {
  useParamsMock.mockReturnValue({ sessionId: "1" });

  useChatStreamStore.setState({
    streams: {
      1: {
        isStreaming: true,
        streamingContent: "我们先看链式法则。",
        agentName: "TutorAgent",
        agentStatus: "正在组织学习回合",
        resources: [],
        wikiFallback: null,
        error: null,
        pathUpdate: {
          target_topic: "反向传播",
          mastered: ["导数"],
          strengthening: ["链式法则"],
          next_up: ["损失函数"],
          priority_suggestion: "先补链式法则",
        },
        evaluation: {
          mastery_delta: "对链式法则的理解仍不稳定",
          weak_points: ["复合函数求导"],
          pace_advice: "先慢下来做一步一步推导",
          should_adjust_path: true,
        },
        profileDelta: null,
        nextActions: ["先看图解", "再做一道题"],
      },
    },
    controllers: {},
  });

  render(<ChatPage />);

  await waitFor(() => {
    expect(screen.getByText("先补链式法则")).toBeInTheDocument();
    expect(screen.getByText("复合函数求导")).toBeInTheDocument();
    expect(screen.getByText("先看图解")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行测试确认当前 store 不支持这些字段**

Run: `pnpm test -- src/app/(main)/chat/[sessionId]/page.test.tsx`
Expected: FAIL，原因是 `ChatStreamState` 尚未包含闭环字段。

- [ ] **Step 3: 扩展 SSE handlers**

在 `frontend/src/lib/sse.ts` 中新增：

```ts
onPathUpdate?: (payload: PathUpdate, sessionId: number | null) => void;
onEvaluationUpdate?: (payload: EvaluationSummary, sessionId: number | null) => void;
onProfileDelta?: (payload: ProfileDelta, sessionId: number | null) => void;
onNextActions?: (payload: { actions: string[] }, sessionId: number | null) => void;
```

并在 `switch` 中处理：

```ts
case "path_update":
case "evaluation_update":
case "profile_delta":
case "next_actions":
```

- [ ] **Step 4: 扩展流式 store 状态**

在 `frontend/src/store/chatStreamStore.ts` 中把状态补成：

```ts
export interface ChatStreamState {
  isStreaming: boolean;
  streamingContent: string;
  agentName: string;
  agentStatus: string | null;
  resources: ResourceCard[];
  pathUpdate: PathUpdate | null;
  evaluation: EvaluationSummary | null;
  profileDelta: ProfileDelta | null;
  nextActions: string[];
  wikiFallback: string | null;
  error: string | null;
}
```

同时新增 setter：
- `setPathUpdate`
- `setEvaluation`
- `setProfileDelta`
- `setNextActions`

- [ ] **Step 5: 确保 `startStream` 和 `clearStream` 会重置新增字段**

```ts
const EMPTY_STREAM_STATE: ChatStreamState = {
  isStreaming: false,
  streamingContent: "",
  agentName: "",
  agentStatus: null,
  resources: [],
  pathUpdate: null,
  evaluation: null,
  profileDelta: null,
  nextActions: [],
  wikiFallback: null,
  error: null,
};
```

- [ ] **Step 6: 运行聊天页测试**

Run: `pnpm test -- src/app/(main)/chat/[sessionId]/page.test.tsx`
Expected: PASS。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/sse.ts frontend/src/store/chatStreamStore.ts frontend/src/app/(main)/chat/[sessionId]/page.test.tsx
git commit -m "feat: 扩展聊天流状态支持学习回合信息"
```

---

### Task 3: 先把 Planner 从资源列表升级成比赛版回合规划入口

**Files:**
- Modify: `backend/app/agents/planner_agent.py`
- Modify: `backend/app/agents/router_agent.py`
- Test: `backend/tests/test_agents/test_planner_agent.py`
- Test: `backend/tests/test_agents/test_router_agent.py`

- [ ] **Step 1: 先写 Planner 返回闭环计划的测试**

```py
def test_planner_builds_learning_turn_plan_for_tutor_driven_request() -> None:
    decision = RouteDecision(
        update_profile=True,
        generate_document=True,
        is_tutor_question=False,
        topic="反向传播",
        resource_types=["document", "quiz", "diagram"],
    )

    plan = PlannerAgent().plan_learning_turn(
        "反向传播",
        {"learning_goal": "补机器学习基础"},
        decision,
    )

    assert plan.primary_agent == "TutorAgent"
    assert "diagram" in plan.resource_types
    assert plan.needs_path_update is True
    assert plan.needs_evaluation is True
```

- [ ] **Step 2: 运行后端定向测试确认当前 Planner 不支持**

Run: `uv run pytest backend/tests/test_agents/test_planner_agent.py backend/tests/test_agents/test_router_agent.py -v`
Expected: FAIL。

- [ ] **Step 3: 在 `planner_agent.py` 中新增比赛版规划结构**

```py
@dataclass(slots=True)
class LearningTurnPlan:
    primary_agent: str
    resource_types: list[str]
    needs_path_update: bool
    needs_evaluation: bool
    needs_profile_delta: bool
    next_action_count: int

class PlannerAgent:
    def plan_learning_turn(
        self,
        topic: str,
        profile: dict[str, Any] | None,
        route_decision: RouteDecision,
    ) -> LearningTurnPlan:
        return LearningTurnPlan(
            primary_agent="TutorAgent",
            resource_types=self._normalize_resource_types(route_decision.resource_types),
            needs_path_update=True,
            needs_evaluation=True,
            needs_profile_delta=bool(route_decision.update_profile),
            next_action_count=2,
        )
```

- [ ] **Step 4: 把 `diagram` 纳入资源规划默认值**

资源规划规则收紧为：

```py
def _normalize_resource_types(self, resource_types: list[str]) -> list[str]:
    normalized = ["document", "quiz"]
    if "diagram" in resource_types or "mindmap" in resource_types:
        normalized.append("diagram")
    else:
        normalized.append("mindmap")
    return normalized
```

第一版不把 `code` 作为 Tutor 闭环默认项，避免演示节奏过重。

- [ ] **Step 5: 保留 Router 的轻量职责，但让其更容易触发闭环**

在 `backend/app/agents/router_agent.py` 中把类似这些输入稳定路由到 Tutor 闭环主线：
- “帮我梳理……学习路径”
- “我现在大二，想补……基础”
- “这题我没听懂”

如果是明确的图解请求，则在 `resource_types` 里带上 `diagram`。

- [ ] **Step 6: 运行后端测试**

Run: `uv run pytest backend/tests/test_agents/test_planner_agent.py backend/tests/test_agents/test_router_agent.py -v`
Expected: PASS。

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/planner_agent.py backend/app/agents/router_agent.py backend/tests/test_agents/test_planner_agent.py backend/tests/test_agents/test_router_agent.py
git commit -m "feat: 新增比赛版学习回合规划入口"
```

---

### Task 4: 新增 Evaluation Service，落地中等粒度评估摘要

**Files:**
- Create: `backend/app/services/evaluation_service.py`
- Create: `backend/tests/test_services/test_evaluation_service.py`

- [ ] **Step 1: 先写服务测试**

```py
from app.services.evaluation_service import EvaluationService


def test_evaluation_service_merges_quiz_result_and_feedback() -> None:
    result = EvaluationService().summarize(
        topic="反向传播",
        quiz_result={"correct_rate": 0.4, "wrong_points": ["链式法则"]},
        feedback_text="我还是没听懂反向传播里的求导过程",
        profile={"learning_pace": "正常"},
    )

    assert result.mastery_delta
    assert "链式法则" in result.weak_points
    assert result.should_adjust_path is True
```

- [ ] **Step 2: 运行测试确认文件缺失**

Run: `uv run pytest backend/tests/test_services/test_evaluation_service.py -v`
Expected: FAIL with `ModuleNotFoundError`。

- [ ] **Step 3: 写最小实现**

```py
class EvaluationService:
    def summarize(
        self,
        *,
        topic: str,
        quiz_result: dict[str, Any] | None,
        feedback_text: str | None,
        profile: dict[str, Any] | None,
    ) -> EvaluationSummary:
        wrong_points = list((quiz_result or {}).get("wrong_points") or [])
        feedback = (feedback_text or "").strip()
        should_adjust_path = bool(wrong_points) or ("没听懂" in feedback)

        return EvaluationSummary(
            mastery_delta=f"当前主题「{topic}」仍需继续巩固",
            weak_points=wrong_points or ([topic] if should_adjust_path else []),
            pace_advice="先放慢节奏，结合图解再练一题" if should_adjust_path else "可以继续推进下一知识点",
            should_adjust_path=should_adjust_path,
            recommended_resource_type="diagram" if should_adjust_path else "quiz",
        )
```

- [ ] **Step 4: 运行服务测试**

Run: `uv run pytest backend/tests/test_services/test_evaluation_service.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/evaluation_service.py backend/tests/test_services/test_evaluation_service.py
git commit -m "feat: 新增学习效果评估服务"
```

---

### Task 5: 新增 Path Service，输出比赛版路径分组摘要

**Files:**
- Create: `backend/app/services/path_service.py`
- Create: `backend/tests/test_services/test_path_service.py`

- [ ] **Step 1: 先写路径服务测试**

```py
from app.services.path_service import PathService


def test_path_service_groups_nodes_by_learning_status() -> None:
    result = PathService().build_update(
        topic="反向传播",
        evaluation={
            "weak_points": ["链式法则"],
            "should_adjust_path": True,
        },
        profile={"knowledge_base": {"导数": "熟悉"}},
    )

    assert result.target_topic == "反向传播"
    assert "导数" in result.mastered
    assert "链式法则" in result.strengthening
    assert result.next_up
```

- [ ] **Step 2: 运行测试确认当前缺失**

Run: `uv run pytest backend/tests/test_services/test_path_service.py -v`
Expected: FAIL。

- [ ] **Step 3: 写最小路径服务实现**

```py
class PathService:
    def build_update(
        self,
        *,
        topic: str,
        evaluation: dict[str, Any] | EvaluationSummary,
        profile: dict[str, Any] | None,
    ) -> PathUpdate:
        knowledge_base = (profile or {}).get("knowledge_base") or {}
        mastered = [name for name, level in knowledge_base.items() if level]
        weak_points = list(
            getattr(evaluation, "weak_points", None)
            or evaluation.get("weak_points")
            or []
        )

        return PathUpdate(
            target_topic=topic,
            mastered=mastered[:3],
            strengthening=weak_points[:3],
            next_up=[topic],
            priority_suggestion=weak_points[0] if weak_points else f"继续推进 {topic}",
        )
```

- [ ] **Step 4: 运行服务测试**

Run: `uv run pytest backend/tests/test_services/test_path_service.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/path_service.py backend/tests/test_services/test_path_service.py
git commit -m "feat: 新增比赛版路径摘要服务"
```

---

### Task 6: 扩展 Media Agent，补上 diagram 资源类型

**Files:**
- Modify: `backend/app/agents/media_agent.py`
- Modify: `backend/app/schemas/chat.py`
- Modify: `frontend/src/components/chat/ResourceCard.tsx`
- Test: `backend/tests/test_agents/test_media_agent.py`

- [ ] **Step 1: 先写 MediaAgent 测试**

```py
async def test_media_agent_generates_diagram_resource() -> None:
    agent = MediaAgent(llm_client=StubLLMClient(), wiki_service=None)

    resource = await agent.generate_diagram(
        topic="反向传播",
        profile={"learning_goal": "补机器学习基础"},
        tutor_context="重点解释梯度如何逐层回传",
    )

    assert resource.resource_type == "diagram"
    assert "```mermaid" in resource.content
```

- [ ] **Step 2: 运行测试确认当前缺失**

Run: `uv run pytest tests/test_agents/test_media_agent.py -v`
Expected: FAIL。

- [ ] **Step 3: 在 `MediaAgent` 中新增 `generate_diagram(...)`**

```py
async def generate_diagram(
    self,
    topic: str,
    profile: dict[str, Any] | None,
    tutor_context: str | None = None,
) -> AgentResource:
    normalized_topic = topic.strip() if topic else "当前学习主题"
    wiki_context, wiki_fallback = await self._build_wiki_context(normalized_topic)
    prompt = self._build_diagram_prompt(normalized_topic, profile or {}, wiki_context, tutor_context or "")
    content = await self.llm_client.generate_text(prompt)
    return AgentResource(
        title=f"{normalized_topic}算法图解",
        resource_type="diagram",
        content=self._normalize_content(normalized_topic, content, "算法图解"),
        knowledge_point=normalized_topic,
        agent_name="MediaAgent",
        wiki_fallback=wiki_fallback,
    )
```

- [ ] **Step 4: 扩展前后端对 `diagram` 的资源类型支持**

`backend/app/schemas/chat.py`

```py
resource_type: Literal["document", "quiz", "code", "mindmap", "diagram", "ppt", "reading"]
```

`frontend/src/components/chat/ResourceCard.tsx`

```ts
const RESOURCE_TYPE_LABELS: Record<ResourceType, string> = {
  document: "学习文档",
  quiz: "练习题",
  code: "代码实践",
  mindmap: "思维导图",
  diagram: "算法图解",
  ppt: "教学演示",
  animation: "算法动画",
  reading: "拓展阅读",
};
```

- [ ] **Step 5: 运行测试**

Run: `uv run pytest tests/test_agents/test_media_agent.py -v && pnpm test -- src/app/(main)/chat/[sessionId]/page.test.tsx`
Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/media_agent.py backend/app/schemas/chat.py frontend/src/components/chat/ResourceCard.tsx backend/tests/test_agents/test_media_agent.py
git commit -m "feat: 新增算法图解资源类型"
```

---

### Task 7: 让 TutorAgent 输出真正的主回答，并接收学习回合上下文

**Files:**
- Modify: `backend/app/agents/tutor_agent.py`
- Create: `backend/app/services/learning_turn_service.py`
- Modify: `backend/tests/test_agents/test_orchestrator.py`

- [ ] **Step 1: 先写 Tutor 主回答测试**

```py
async def test_tutor_agent_builds_primary_response_from_learning_turn_context() -> None:
    response = await TutorAgent(llm_client=StubLLMClient(), wiki_service=None).answer_learning_turn(
        topic="反向传播",
        profile={"learning_goal": "补机器学习基础"},
        resources=[
            AgentResource(
                title="反向传播学习文档",
                resource_type="document",
                content="先理解误差如何影响梯度。",
                knowledge_point="反向传播",
                agent_name="DocAgent",
            )
        ],
        evaluation=EvaluationSummary(
            mastery_delta="链式法则理解不稳定",
            weak_points=["链式法则"],
            pace_advice="先慢下来推导",
            should_adjust_path=True,
            recommended_resource_type="diagram",
        ),
        next_actions=["先看图解", "再做一道题"],
    )

    assert "反向传播" in response
    assert "链式法则" in response
    assert "先看图解" in response
```

- [ ] **Step 2: 运行测试确认当前方法不存在**

Run: `uv run pytest tests/test_agents/test_orchestrator.py -k learning_turn -v`
Expected: FAIL。

- [ ] **Step 3: 新增学习回合组装服务**

```py
class LearningTurnService:
    def build_result(
        self,
        *,
        tutor_response: str,
        resources: list[AgentResource],
        path_update: PathUpdate | None,
        evaluation: EvaluationSummary | None,
        profile_delta: ProfileDelta | None,
        next_actions: list[str],
    ) -> LearningTurnResult:
        return LearningTurnResult(
            tutor_response=tutor_response,
            resources=resources,
            path_update=path_update,
            evaluation=evaluation,
            profile_delta=profile_delta,
            next_actions=next_actions,
        )
```

- [ ] **Step 4: 扩展 TutorAgent 主回答接口**

```py
async def answer_learning_turn(
    self,
    *,
    topic: str,
    profile: dict[str, Any] | None,
    resources: list[AgentResource],
    evaluation: EvaluationSummary | None,
    next_actions: list[str],
) -> str:
    prompt = self._build_learning_turn_prompt(
        topic=topic,
        profile=profile or {},
        resources=resources,
        evaluation=evaluation,
        next_actions=next_actions,
    )
    return await self.llm_client.generate_text(prompt)
```

提示词要求锁定：
- 主体是 Tutor，不能列成生硬接口 dump
- 先讲解，再点出薄弱点，再给下一步建议
- 全部中文

- [ ] **Step 5: 运行测试**

Run: `uv run pytest tests/test_agents/test_orchestrator.py -k learning_turn -v`
Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/tutor_agent.py backend/app/services/learning_turn_service.py backend/tests/test_agents/test_orchestrator.py
git commit -m "feat: 让 Tutor 输出学习回合主回答"
```

---

### Task 8: 重写 Orchestrator，把增强模块挂到 Tutor 主链路下并做好降级

**Files:**
- Modify: `backend/app/agents/orchestrator.py`
- Modify: `backend/app/api/chat.py`
- Modify: `backend/tests/test_agents/test_orchestrator.py`
- Modify: `backend/tests/test_api/test_chat_api.py`

- [ ] **Step 1: 先写学习回合 SSE 顺序测试**

```py
async def test_orchestrator_streams_learning_turn_events_in_order() -> None:
    events = [event async for event in build_orchestrator_for_test().run(session_id=1, user_message="帮我梳理反向传播学习路径")]

    assert events[0].type == "agent_status"
    assert any(event.type == "token" for event in events)
    assert any(event.type == "resource_card" for event in events)
    assert any(event.type == "path_update" for event in events)
    assert any(event.type == "evaluation_update" for event in events)
    assert any(event.type == "next_actions" for event in events)
    assert events[-1].type == "done"
```

- [ ] **Step 2: 写 Media 降级测试**

```py
async def test_orchestrator_keeps_tutor_response_when_media_fails() -> None:
    events = [event async for event in build_orchestrator_for_test(media_error=True).run(session_id=1, user_message="帮我讲解反向传播")]

    assert any(event.type == "token" for event in events)
    assert not any(
        event.type == "error" and event.payload.get("message") == "生成学习资源失败，请稍后重试"
        for event in events
    )
    assert events[-1].type == "done"
```

- [ ] **Step 3: 运行测试确认当前流程不满足**

Run: `uv run pytest tests/test_agents/test_orchestrator.py tests/test_api/test_chat_api.py -v`
Expected: FAIL。

- [ ] **Step 4: 在 `Orchestrator.run(...)` 中改成 Tutor 必达主流程**

目标顺序：

```py
plan = self.planner_agent.plan_learning_turn(...)
resources = []
evaluation = self.evaluation_service.summarize(...)
path_update = self.path_service.build_update(...)
next_actions = self._build_next_actions(...)
tutor_response = await self.tutor_agent.answer_learning_turn(...)
```

流式顺序固定为：
1. `agent_status`（组织回合）
2. `token`（Tutor 主回答）
3. `resource_card`（按生成结果逐个下发）
4. `evaluation_update`
5. `path_update`
6. `profile_delta`（若有）
7. `next_actions`
8. `done`

- [ ] **Step 5: 明确降级规则写死在编排器里**

```py
try:
    diagram = await self.media_agent.generate_diagram(...)
    resources.append(diagram)
except Exception:
    logger.warning("diagram generation failed", exc_info=True)
```

同理：
- `PathService` 失败：不发 `path_update`，只保留 `next_actions`
- `EvaluationService` 失败：不发 `evaluation_update`
- `TutorAgent` 失败：发送 `error_event(...)` 后结束

- [ ] **Step 6: 保持 `/api/chat/stream` 接口不变，只注入新增服务**

在 `backend/app/api/chat.py` 的 `build_orchestrator(...)` 中新增：

```py
from app.services.evaluation_service import EvaluationService
from app.services.learning_turn_service import LearningTurnService
from app.services.path_service import PathService
```

并注入到 `Orchestrator(...)`。

- [ ] **Step 7: 运行后端测试**

Run: `uv run pytest tests/test_agents/test_orchestrator.py tests/test_api/test_chat_api.py -v`
Expected: PASS。

- [ ] **Step 8: Commit**

```bash
git add backend/app/agents/orchestrator.py backend/app/api/chat.py backend/tests/test_agents/test_orchestrator.py backend/tests/test_api/test_chat_api.py
git commit -m "feat: 打通 Tutor 驱动学习闭环编排"
```

---

### Task 9: 把聊天页改造成学习回合视图

**Files:**
- Modify: `frontend/src/app/(main)/chat/[sessionId]/page.tsx`
- Create: `frontend/src/components/chat/LearningTurnPanel.tsx`
- Create: `frontend/src/components/chat/PathUpdateCard.tsx`
- Create: `frontend/src/components/chat/EvaluationSummaryCard.tsx`
- Create: `frontend/src/components/chat/ProfileDeltaCard.tsx`
- Create: `frontend/src/components/chat/NextActionsCard.tsx`
- Test: `frontend/src/app/(main)/chat/[sessionId]/page.test.tsx`

- [ ] **Step 1: 先写渲染测试**

```ts
it("流式中展示学习回合面板", async () => {
  useParamsMock.mockReturnValue({ sessionId: "1" });
  useChatStreamStore.getState().startStream(1);
  useChatStreamStore.getState().appendToken(1, "我们先理解链式法则。");
  useChatStreamStore.getState().setPathUpdate(1, {
    target_topic: "反向传播",
    mastered: ["导数"],
    strengthening: ["链式法则"],
    next_up: ["损失函数"],
    priority_suggestion: "先补链式法则",
  });
  useChatStreamStore.getState().setEvaluation(1, {
    mastery_delta: "链式法则理解不稳定",
    weak_points: ["链式法则"],
    pace_advice: "先慢下来推导",
    should_adjust_path: true,
  });
  useChatStreamStore.getState().setNextActions(1, ["先看图解", "再做一道题"]);

  render(<ChatPage />);

  await waitFor(() => {
    expect(screen.getByText("学习回合")).toBeInTheDocument();
    expect(screen.getByText("评估摘要")).toBeInTheDocument();
    expect(screen.getByText("路径调整")).toBeInTheDocument();
    expect(screen.getByText("下一步建议")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行测试确认当前 UI 不支持**

Run: `pnpm test -- src/app/(main)/chat/[sessionId]/page.test.tsx`
Expected: FAIL。

- [ ] **Step 3: 新建 `LearningTurnPanel.tsx`**

```tsx
interface LearningTurnPanelProps {
  resources: ResourceCardType[];
  pathUpdate: PathUpdate | null;
  evaluation: EvaluationSummary | null;
  profileDelta: ProfileDelta | null;
  nextActions: string[];
}

export function LearningTurnPanel(props: LearningTurnPanelProps) {
  return (
    <div className="mt-4 space-y-3">
      <div className="text-xs tracking-[0.18em] text-[var(--color-warm-gray-400)] uppercase">
        学习回合
      </div>
      {props.resources.length > 0 && <div>{props.resources.map(...)}</div>}
      {props.pathUpdate && <PathUpdateCard pathUpdate={props.pathUpdate} />}
      {props.evaluation && <EvaluationSummaryCard evaluation={props.evaluation} />}
      {props.profileDelta && <ProfileDeltaCard profileDelta={props.profileDelta} />}
      {props.nextActions.length > 0 && <NextActionsCard actions={props.nextActions} />}
    </div>
  );
}
```

- [ ] **Step 4: 在聊天页把流式与历史消息都挂上学习回合面板**

`frontend/src/app/(main)/chat/[sessionId]/page.tsx`

```tsx
{streamState.streamingContent && (
  <div className="flex justify-start">
    <div className="max-w-[88%] rounded-xl rounded-bl-sm bg-[var(--color-ivory)] px-5 py-4 ring-1 ring-[var(--color-warm-gray-200)] md:max-w-[78%]">
      <StreamingText content={streamState.streamingContent} />
      <LearningTurnPanel
        resources={streamState.resources}
        pathUpdate={streamState.pathUpdate}
        evaluation={streamState.evaluation}
        profileDelta={streamState.profileDelta}
        nextActions={streamState.nextActions}
      />
    </div>
  </div>
)}
```

第一版历史消息可以先只保留资源卡片，不强行回填旧会话的路径/评估缺失字段。

- [ ] **Step 5: 保持全部 UI 中文并延续现有暖色系风格**

卡片标题固定用：
- `学习回合`
- `路径调整`
- `评估摘要`
- `画像变化`
- `下一步建议`

- [ ] **Step 6: 运行测试**

Run: `pnpm test -- src/app/(main)/chat/[sessionId]/page.test.tsx`
Expected: PASS。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/(main)/chat/[sessionId]/page.tsx frontend/src/components/chat/LearningTurnPanel.tsx frontend/src/components/chat/PathUpdateCard.tsx frontend/src/components/chat/EvaluationSummaryCard.tsx frontend/src/components/chat/ProfileDeltaCard.tsx frontend/src/components/chat/NextActionsCard.tsx frontend/src/app/(main)/chat/[sessionId]/page.test.tsx
git commit -m "feat: 将聊天页升级为学习回合视图"
```

---

### Task 10: 让路径页兼容比赛版路径分组结构

**Files:**
- Modify: `frontend/src/app/(main)/path/page.tsx`
- Test: `frontend/src/app/(main)/chat/[sessionId]/page.test.tsx`

- [ ] **Step 1: 先写最小渲染断言**

```ts
expect(screen.getByText("待巩固")).toBeInTheDocument();
expect(screen.getByText("下一步")).toBeInTheDocument();
```

- [ ] **Step 2: 修改路径页本地结构**

```ts
interface PathGroupState {
  targetTopic: string;
  mastered: string[];
  strengthening: string[];
  nextUp: string[];
  prioritySuggestion: string;
}
```

先在页面内部兼容新结构，保留旧的 `generatePath()` 作为临时数据来源，不要求这一步马上切到新后端接口。

- [ ] **Step 3: 用三组列表替代纯时间线**

```tsx
<section>
  <h2>已掌握</h2>
  ...
</section>
<section>
  <h2>待巩固</h2>
  ...
</section>
<section>
  <h2>下一步</h2>
  ...
</section>
```

- [ ] **Step 4: 运行前端测试**

Run: `pnpm test -- src/app/(main)/chat/[sessionId]/page.test.tsx`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/(main)/path/page.tsx frontend/src/app/(main)/chat/[sessionId]/page.test.tsx
git commit -m "feat: 让路径页兼容比赛版分组结构"
```

---

### Task 11: 补最小可观测、缓存与演示稳定性钩子

**Files:**
- Modify: `backend/app/agents/orchestrator.py`
- Modify: `backend/app/agents/media_agent.py`
- Modify: `backend/tests/test_agents/test_orchestrator.py`

- [ ] **Step 1: 先写最小日志字段测试或断言**

```py
assert any("degraded" in record.message for record in caplog.records)
```

- [ ] **Step 2: 在 Orchestrator 中记录最小可观测字段**

```py
logger.info(
    "learning_turn_completed",
    extra={
        "session_id": session_id,
        "topic": decision.topic,
        "resource_types": plan.resource_types,
        "degraded": degraded,
        "success": True,
    },
)
```

- [ ] **Step 3: 对图解生成加进程内轻量缓存**

第一版只在 `MediaAgent` 里用最小字典缓存，不引入 Redis：

```py
self._diagram_cache: dict[tuple[str, str], AgentResource] = {}
cache_key = (normalized_topic, profile.get("learning_goal") or "")
```

- [ ] **Step 4: 运行后端测试**

Run: `uv run pytest tests/test_agents/test_orchestrator.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/orchestrator.py backend/app/agents/media_agent.py backend/tests/test_agents/test_orchestrator.py
git commit -m "feat: 增加比赛版最小缓存与可观测字段"
```

---

### Task 12: 修当前测试基线失配，确保实现阶段可持续推进

**Files:**
- Modify: `backend/tests/test_agents/test_orchestrator.py`
- Modify: `backend/tests/test_agents/test_router_agent.py`
- Modify: `backend/tests/test_api/test_chat_api.py`
- Modify: `backend/tests/test_api/test_profile_api.py`
- Modify: `frontend/package.json`

- [ ] **Step 1: 先补前端类型检查脚本**

在 `frontend/package.json` 中加入：

```json
{
  "scripts": {
    "type-check": "tsc --noEmit"
  }
}
```

- [ ] **Step 2: 对齐后端测试签名变化**

修掉当前已知失配：
- `Orchestrator.__init__()` 需要 `media_agent` / `tutor_agent`
- `RouteDecision` 需要当前字段集
- chat/profile API 测试补上鉴权
- health 断言兼容 `llm_warning`

- [ ] **Step 3: 跑后端关键测试**

Run: `uv run pytest tests/test_agents/test_orchestrator.py tests/test_api/test_chat_api.py tests/test_api/test_profile_api.py -v`
Expected: PASS 或只剩外部网络依赖相关失败。

- [ ] **Step 4: 跑前端测试与类型检查**

Run: `pnpm test && pnpm type-check && pnpm lint`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_agents/test_orchestrator.py backend/tests/test_agents/test_router_agent.py backend/tests/test_api/test_chat_api.py backend/tests/test_api/test_profile_api.py frontend/package.json
git commit -m "test: 对齐当前仓库基线与学习闭环测试"
```

---

## 实施顺序说明

1. 先扩类型和 SSE 契约，避免前后端并行时字段不断返工。
2. 再补 Planner / Evaluation / Path / Media 这四块闭环骨架。
3. 然后改 Tutor 与 Orchestrator，把增强结果统一挂到 Tutor 主输出下。
4. 最后再升级聊天页和路径页 UI，并补稳定性与基线测试。

## 验收标准

- 聊天接口在一次学习请求中可以流式返回 Tutor 主回答。
- 同一轮响应可见资源卡、评估摘要、路径调整和下一步建议。
- `diagram` 可以作为独立资源类型落到前后端。
- Media / Evaluation / Path 任一模块失败时，Tutor 主回答仍能完成。
- 前端测试、类型检查、关键后端测试可通过。

## 风险与处理

- **当前测试基线不干净**：先执行 Task 12 对齐签名和鉴权，再做大步实现。
- **历史会话没有新字段**：第一版历史消息不强制回填路径/评估，只增强流式中的当前回合。
- **`diagram` prompt 不稳定**：先锁 Mermaid 输出协议，必要时回退到 Markdown 图解。
- **路径接口尚未重构**：路径页先兼容分组结构，不阻塞聊天页闭环主线。
