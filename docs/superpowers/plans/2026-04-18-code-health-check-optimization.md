# EduAgent 全面工程体检与中等规模优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对 EduAgent 执行一次全面工程体检，修复前后端主路径中的高确定性问题，并输出已修复项、剩余问题清单和后续建议。

**Architecture:** 先以现有命令建立前后端健康基线，再围绕 chat / profile / wiki 主路径逐步修复阻断项和明显缺陷。后端优先用 pytest 保护服务与 API 行为，前端优先用 lint / build / 人工路径复核约束修改范围，避免大重构。

**Tech Stack:** Next.js 16、React 19、TypeScript、FastAPI、SQLAlchemy、pytest、ESLint

---

## 文件结构与职责映射

### 前端重点文件
- `frontend/package.json` — 前端可用检查命令入口
- `frontend/src/app/(main)/chat/[sessionId]/page.tsx` — 聊天主页面，负责历史消息加载、流式对话、错误展示
- `frontend/src/components/chat/SessionSidebar.tsx` — 会话列表、创建会话、当前会话高亮
- `frontend/src/lib/api.ts` — REST API 请求封装
- `frontend/src/lib/sse.ts` — SSE 流式通信、事件解析与错误兜底
- `frontend/src/lib/types.ts` — 聊天、资源、画像等前端类型定义
- `frontend/src/app/(main)/profile/page.tsx` — 学习画像页面

### 后端重点文件
- `backend/pyproject.toml` — 后端依赖与 pytest 配置
- `backend/app/main.py` — 应用入口、生命周期初始化
- `backend/app/api/chat.py` — 会话创建、流式聊天、会话详情接口
- `backend/app/services/chat_service.py` — 会话、消息、资源持久化逻辑
- `backend/app/api/profile.py` — 学习画像接口
- `backend/app/api/wiki.py` — Wiki 相关接口
- `backend/app/wiki/wiki_service.py` — Wiki 查询逻辑
- `backend/tests/test_api/test_chat_api.py` — 聊天 API 行为测试
- `backend/tests/test_services/test_chat_service.py` — 聊天服务层测试
- `backend/tests/test_api/test_profile_api.py` — 画像 API 测试
- `backend/tests/test_wiki.py` — Wiki 功能测试

### 结果记录文件
- `docs/superpowers/plans/2026-04-18-code-health-check-optimization.md` — 本计划
- 可选新增：`docs/superpowers/reports/2026-04-18-code-health-check-report.md` — 执行后的结果报告；如果仓库没有该目录，就把结果直接整理到最终回复中，不额外落盘

---

### Task 1: 建立前后端健康基线

**Files:**
- Modify: `frontend/package.json`
- Modify: `backend/pyproject.toml`
- Inspect: `frontend/src/app/(main)/chat/[sessionId]/page.tsx`
- Inspect: `backend/app/api/chat.py`

- [ ] **Step 1: 补齐前端类型检查命令（如果缺失）**

在 `frontend/package.json` 的 `scripts` 中补充 `type-check`，保持最小改动：

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint",
    "type-check": "tsc --noEmit"
  }
}
```

- [ ] **Step 2: 运行前端 lint，记录失败点**

Run: `bash -lc "cd frontend && pnpm lint"`
Expected: 输出 ESLint 结果；若失败，记录文件路径与错误类型。

- [ ] **Step 3: 运行前端 type-check，记录失败点**

Run: `bash -lc "cd frontend && pnpm type-check"`
Expected: 若当前存在类型问题，应看到具体文件和行号；若通过，输出无错误。

- [ ] **Step 4: 运行前端 build，记录失败点**

Run: `bash -lc "cd frontend && pnpm build"`
Expected: 要么成功构建，要么暴露出页面或数据获取链路中的阻断问题。

- [ ] **Step 5: 运行后端测试，记录失败点**

Run: `bash -lc "cd backend && uv run pytest"`
Expected: 输出失败用例列表或全部通过。

- [ ] **Step 6: 运行后端静态检查（若当前依赖已安装）**

Run: `bash -lc "cd backend && uv run ruff check ."`
Expected: 输出 ruff 发现的问题；如果环境未安装 ruff，记录为环境限制，不擅自改依赖。

- [ ] **Step 7: 汇总基线问题并按优先级分组**

把问题按 P0 / P1 / P2 分组，至少形成这样的执行草稿：

```md
P0
- 前端构建失败：frontend/src/app/(main)/chat/[sessionId]/page.tsx
- 后端接口测试失败：backend/tests/test_api/test_chat_api.py

P1
- SessionSidebar 创建会话后列表状态不同步
- 聊天页对非法 sessionId 的处理不稳定

P2
- 聊天页资源挂载逻辑重复且存在无效中间变量
```

- [ ] **Step 8: 提交基线准备改动**

```bash
git add frontend/package.json docs/superpowers/plans/2026-04-18-code-health-check-optimization.md
git commit -m "chore: add code health check baseline steps"
```

---

### Task 2: 用测试保护后端聊天会话与流式接口

**Files:**
- Modify: `backend/tests/test_services/test_chat_service.py`
- Modify: `backend/tests/test_api/test_chat_api.py`
- Modify: `backend/app/services/chat_service.py`
- Modify: `backend/app/api/chat.py`

- [ ] **Step 1: 先写服务层失败测试，覆盖会话标题与不存在会话场景**

在 `backend/tests/test_services/test_chat_service.py` 添加以下测试：

```python
def test_update_session_title_persists_to_database() -> None:
    with SessionLocal() as db:
        service = ChatService(session=db)
        session_id = service.create_session("旧标题")

        service.update_session_title(session_id, "新的学习目标")
        session = service.get_session(session_id)

        assert session is not None
        assert session.title == "新的学习目标"


def test_session_exists_returns_false_for_missing_session() -> None:
    with SessionLocal() as db:
        service = ChatService(session=db)

        assert service.session_exists(999999) is False
```

- [ ] **Step 2: 运行新增服务测试，确认当前行为是否暴露问题**

Run: `bash -lc "cd backend && uv run pytest tests/test_services/test_chat_service.py -v"`
Expected: 如果实现存在边界问题，应至少有一项失败；否则记录为现有行为已满足。

- [ ] **Step 3: 为聊天 API 写失败测试，覆盖非法会话 ID 的错误返回**

在 `backend/tests/test_api/test_chat_api.py` 添加测试：

```python
def test_chat_stream_returns_error_for_missing_session(client) -> None:
    response = client.post(
        "/api/chat/stream",
        json={"session_id": 999999, "message": "帮我复习反向传播"},
    )

    assert response.status_code == 200
    assert '"type":"error"' in response.text
    assert "会话不存在，请先创建会话后再发送消息" in response.text
```

- [ ] **Step 4: 运行聊天 API 测试，确认失败或现状**

Run: `bash -lc "cd backend && uv run pytest tests/test_api/test_chat_api.py -v"`
Expected: 能验证接口对非法 session_id 的处理；如果失败，进入实现修复。

- [ ] **Step 5: 最小化整理 `ChatService`，去掉重复 `_require_session()` 调用并保持语义一致**

把 `backend/app/services/chat_service.py` 中重复的 session 获取收敛成局部变量，避免多次重复调用：

```python
def create_session(self, title: str = "新学习会话") -> int:
    db = self._require_session()
    chat_session = ChatSession(title=title)
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return chat_session.id


def list_sessions(self) -> list[ChatSession]:
    db = self._require_session()
    return db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
```

同样方式整理 `save_message`、`get_session`、`list_messages`、`list_resources`、`save_resource`。

- [ ] **Step 6: 收紧 `chat.py` 中的异常边界，保持错误信息可预期**

将 `backend/app/api/chat.py` 中的消息保存与编排异常分层保留为明确结构，不要吞掉可预期错误：

```python
try:
    chat_service.save_message(
        session_id=session_id,
        role="user",
        content=request.message,
    )
except Exception:
    yield encode_sse_event(
        error_event(
            message="保存聊天消息失败，请稍后重试",
            session_id=session_id,
        )
    )
    return
```

如果当前测试暴露 `HTTPException` 或 `LLMClientError` 边界问题，优先做最小修复，不改事件格式。

- [ ] **Step 7: 重新运行聊天相关测试**

Run: `bash -lc "cd backend && uv run pytest tests/test_services/test_chat_service.py tests/test_api/test_chat_api.py -v"`
Expected: PASS。

- [ ] **Step 8: 提交后端聊天链路修复**

```bash
git add backend/app/services/chat_service.py backend/app/api/chat.py backend/tests/test_services/test_chat_service.py backend/tests/test_api/test_chat_api.py
git commit -m "fix: harden chat session persistence flow"
```

---

### Task 3: 修复前端聊天页的会话加载与流式状态问题

**Files:**
- Modify: `frontend/src/app/(main)/chat/[sessionId]/page.tsx`
- Modify: `frontend/src/lib/sse.ts`
- Modify: `frontend/src/lib/api.ts`
- Inspect: `frontend/src/lib/types.ts`

- [ ] **Step 1: 先把聊天页的非法 sessionId 行为写成待修复清单**

确认这几个现象是否存在：

```ts
const parsedSessionId = parseInt(sessionIdParam, 10);
const hasValidSessionId = !isNaN(parsedSessionId) && parsedSessionId > 0;
const [sessionId, setSessionId] = useState<number>(hasValidSessionId ? parsedSessionId : 1);
```

目标问题：非法路由参数时默认落到 `1`，可能把消息发到错误会话。

- [ ] **Step 2: 把 `sessionId` 改为可空状态，避免错误默认值**

在 `frontend/src/app/(main)/chat/[sessionId]/page.tsx` 中改成：

```tsx
const parsedSessionId = Number(sessionIdParam);
const hasValidSessionId = Number.isInteger(parsedSessionId) && parsedSessionId > 0;

const [sessionId, setSessionId] = useState<number | null>(
  hasValidSessionId ? parsedSessionId : null
);
```

并把发送逻辑接到 `streamChat(sessionId, trimmed, ...)`，不要再假设一定有初始会话。

- [ ] **Step 3: 清理历史资源挂载逻辑中的无效变量与重复映射**

删除未使用的 `resourcesByMsg`，把资源转换逻辑提成一个局部函数：

```tsx
const toResourceCard = (resource: SessionDetail["resources"][number]): ResourceCardType => ({
  id: resource.id,
  resource_type: resource.resource_type,
  title: resource.title,
  content: resource.content,
  knowledge_point: resource.knowledge_point,
  agent_name: resource.agent_name,
});
```

然后统一复用：

```tsx
const attached = remaining
  .filter(
    (resource) =>
      new Date(resource.created_at).getTime() <=
      new Date(m.created_at).getTime() + 1000
  )
  .map(toResourceCard);
```

- [ ] **Step 4: 修正流式结束时的空消息追加问题**

仅当有正文或资源时才追加 assistant 消息：

```tsx
onDone: () => {
  if (!collectedContent && collectedResources.length === 0) {
    setStreamState({
      isStreaming: false,
      streamingContent: "",
      agentName: "",
      agentStatus: null,
      resources: [],
      wikiFallback: null,
    });
    return;
  }

  const assistantMsg: ChatMsg = {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    content: collectedContent,
    resources: [...collectedResources],
  };
  setMessages((prev) => [...prev, assistantMsg]);
  setStreamState({
    isStreaming: false,
    streamingContent: "",
    agentName: "",
    agentStatus: null,
    resources: [],
    wikiFallback: null,
  });
}
```

- [ ] **Step 5: 强化 `streamChat` 的流结束处理，避免残留 buffer 丢事件**

在 `frontend/src/lib/sse.ts` 中于读取循环结束后补一轮尾包解析：

```ts
if (buffer.trim()) {
  const tailEvents = parseSSEChunk(buffer);
  for (const event of tailEvents) {
    if (event.type === "done") {
      handlers.onDone?.(event.session_id ?? sessionId);
    }
  }
}
```

如果你更倾向统一分发，则提取 `dispatchEvent(event, handlers, sessionId)`，但不要扩大改动范围到整个事件系统重写。

- [ ] **Step 6: 为 `fetchSessionDetail` 增加明确的 no-store，避免旧详情缓存**

在 `frontend/src/lib/api.ts` 中修改：

```ts
const response = await fetch(`${API_BASE}/api/chat/sessions/${sessionId}`, {
  cache: "no-store",
});
```

`fetchSessions` 同样加 `cache: "no-store"`。

- [ ] **Step 7: 运行前端 lint 与 type-check 验证聊天页修改**

Run: `bash -lc "cd frontend && pnpm lint && pnpm type-check"`
Expected: PASS。

- [ ] **Step 8: 提交聊天页修复**

```bash
git add frontend/src/app/(main)/chat/[sessionId]/page.tsx frontend/src/lib/sse.ts frontend/src/lib/api.ts frontend/package.json
git commit -m "fix: stabilize chat session loading flow"
```

---

### Task 4: 优化 SessionSidebar 会话列表与创建体验

**Files:**
- Modify: `frontend/src/components/chat/SessionSidebar.tsx`
- Modify: `frontend/src/lib/api.ts`
- Inspect: `frontend/src/lib/types.ts`

- [ ] **Step 1: 把创建会话后的本地插入逻辑改成“乐观更新 + 后台刷新”**

当前代码直接插入：

```tsx
setSessions((prev) => [
  {
    id: sessionId,
    title: `新建会话 ${sessionId}`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  ...prev.filter((session) => session.id !== sessionId),
]);
```

保留乐观更新，但在跳转后再执行一次真实刷新：

```tsx
const refreshSessions = async () => {
  const data = await fetchSessions();
  setSessions(data);
};
```

在 `handleCreateSession` 成功后增加：

```tsx
void refreshSessions();
```

- [ ] **Step 2: 提取会话列表加载函数，复用到初始化和创建后刷新**

把 `useEffect` 中的匿名加载逻辑改成：

```tsx
const loadSessions = useCallback(async () => {
  setCreateError(null);
  try {
    const data = await fetchSessions();
    setSessions(data);
  } catch {
    setSessions([]);
  } finally {
    setLoading(false);
  }
}, []);
```

然后：

```tsx
useEffect(() => {
  void loadSessions();
}, [loadSessions]);
```

- [ ] **Step 3: 保持创建态与加载态文案一致为中文**

确保保留这些中文文案，不引入英文：

```tsx
{creating ? "正在创建..." : "新建对话"}
```

```tsx
<p className="px-2 py-3 text-sm text-[var(--color-warm-gray-400)]">
  正在加载会话...
</p>
```

- [ ] **Step 4: 运行前端 lint 验证 Sidebar 改动**

Run: `bash -lc "cd frontend && pnpm lint"`
Expected: PASS。

- [ ] **Step 5: 提交 Sidebar 优化**

```bash
git add frontend/src/components/chat/SessionSidebar.tsx frontend/src/lib/api.ts
git commit -m "refactor: refresh chat sessions after creation"
```

---

### Task 5: 复核 profile / wiki 主路径并修复高确定性问题

**Files:**
- Modify: `backend/app/api/profile.py`
- Modify: `backend/app/api/wiki.py`
- Modify: `backend/tests/test_api/test_profile_api.py`
- Modify: `backend/tests/test_wiki.py`
- Inspect: `frontend/src/app/(main)/profile/page.tsx`

- [ ] **Step 1: 先运行画像与 Wiki 相关测试，确认当前失败点**

Run: `bash -lc "cd backend && uv run pytest tests/test_api/test_profile_api.py tests/test_wiki.py -v"`
Expected: 输出明确的失败用例或全部通过。

- [ ] **Step 2: 如果 profile API 存在空会话或缺省参数问题，先写失败测试**

在 `backend/tests/test_api/test_profile_api.py` 按实际接口补充这类断言：

```python
def test_get_profile_without_session_id_returns_default_profile(client) -> None:
    response = client.get("/api/profile")

    assert response.status_code == 200
    body = response.json()
    assert "knowledge_level" in body
```
```

如果真实响应结构不同，以当前 schema 为准调整字段名，不凭空创造新结构。

- [ ] **Step 3: 如果 wiki API 对未知主题/章节返回不稳定，先写失败测试**

在 `backend/tests/test_wiki.py` 或 API 测试中补充：

```python
def test_wiki_related_returns_empty_list_for_unknown_topic(client) -> None:
    response = client.get("/api/wiki/related/不存在的知识点")

    assert response.status_code == 200
    assert response.json() == []
```

如果当前接口约定不是空数组，而是受控错误消息，则按现有约定断言，不改公共契约。

- [ ] **Step 4: 仅做高确定性修复，避免扩张到业务设计层**

允许的实现示例：

```python
@router.get("/related/{topic}", response_model=list[WikiEntryResponse])
async def get_related_topics(topic: str) -> list[WikiEntryResponse]:
    entries = wiki_service.get_related(topic)
    return [WikiEntryResponse.model_validate(entry) for entry in entries]
```

或者：

```python
if profile is None:
    return ProfileResponse.default()
```

前提是这些行为已经被现有 schema 或测试约定支持。

- [ ] **Step 5: 重新运行画像与 Wiki 测试**

Run: `bash -lc "cd backend && uv run pytest tests/test_api/test_profile_api.py tests/test_wiki.py -v"`
Expected: PASS。

- [ ] **Step 6: 提交 profile / wiki 修复**

```bash
git add backend/app/api/profile.py backend/app/api/wiki.py backend/tests/test_api/test_profile_api.py backend/tests/test_wiki.py
git commit -m "fix: tighten profile and wiki response handling"
```

---

### Task 6: 完整回归验证并形成结果清单

**Files:**
- Modify: `docs/superpowers/reports/2026-04-18-code-health-check-report.md`（可选）
- Inspect: `frontend/src/app/(main)/chat/[sessionId]/page.tsx`
- Inspect: `backend/app/api/chat.py`

- [ ] **Step 1: 运行完整前端检查链路**

Run: `bash -lc "cd frontend && pnpm lint && pnpm type-check && pnpm build"`
Expected: 全部通过；如果某项失败，记录为剩余问题并附原因。

- [ ] **Step 2: 运行完整后端检查链路**

Run: `bash -lc "cd backend && uv run pytest"`
Expected: 全部通过；如果失败，列出仍然失败的测试。

若 ruff 可用，再执行：

Run: `bash -lc "cd backend && uv run ruff check ."`
Expected: PASS 或得到剩余静态问题列表。

- [ ] **Step 3: 启动前端开发服务器并手工走一次聊天主路径**

Run: `bash -lc "cd frontend && pnpm dev"`
Expected: 本地开发服务器启动成功。

手工验证点：
- 新建对话后跳转到新会话页面
- 发送一条消息后不会落到错误的 sessionId
- 流式返回结束后不会多出空 assistant 消息
- Sidebar 中当前会话状态正常显示
- “查看学习画像”链接仍可跳转

- [ ] **Step 4: 形成最终结果报告**

如果要落盘，创建 `docs/superpowers/reports/2026-04-18-code-health-check-report.md`，至少包含：

```md
# 代码体检结果

## 已修复
- 修复聊天页在非法 sessionId 下错误回落到 1 的问题
- 修复 SSE 尾包未解析导致 done 事件可能丢失的问题
- 优化 SessionSidebar 创建后会话列表刷新

## 未修复
- 某些 Wiki 边界行为依赖真实知识库数据，当前仅完成受控返回校验

## 后续建议
- 为前端补充组件级测试或 E2E
- 为 chat / profile / wiki 增加更细粒度的 API 边界测试
```

如果不落盘，则在最终交付回复中按相同结构输出。

- [ ] **Step 5: 做最终提交**

```bash
git add frontend backend docs/superpowers/plans/2026-04-18-code-health-check-optimization.md
git commit -m "fix: improve project code health across chat flows"
```

---

## Self-Review

### Spec coverage
- 已覆盖前端 lint / type-check / build 基线检查
- 已覆盖后端 pytest / ruff 基线检查
- 已覆盖 chat 主路径修复
- 已覆盖 SessionSidebar 体验优化
- 已覆盖 profile / wiki 主路径复核
- 已覆盖最终“已修复 / 未修复 / 后续建议”产出

### Placeholder scan
- 无 TBD / TODO / “后续再实现”式占位
- 每个代码修改步骤都给出具体代码或命令
- 未使用“参考前一任务”之类省略写法

### Type consistency
- 前端会话 ID 统一为 `number | null` 输入到 `streamChat`
- 后端聊天服务与聊天 API 都沿用现有 `ChatService` / `SSEEvent` 命名
- 报告输出结构与设计文档中的三类结果一致
