# EduAgent 首个可交付切片设计

日期：2026-04-14
主题：EduAgent 对话 MVP（聊天页 + 画像页）

## 1. 背景与目标

当前仓库仅包含需求与架构设计文档，尚未落地实际项目代码。根据 [项目要求.md](项目要求.md) 与 [PLAN.md](PLAN.md)，项目整体目标较大，包含多 Agent、知识中枢、RAG、多模态资源生成、学习路径规划等多个独立子系统。

为避免一次性实现范围失控，首个可交付切片聚焦于一条最短且可演示的垂直链路：

- 单用户 / 游客模式
- 聊天页 + 画像页
- FastAPI + SQLite + SSE
- 简化版 Router / Profile / Doc Agent
- 前后端真实联通
- 真实讯飞星火接入

> **SQLite 选择说明**：MVP 使用 SQLite 以避免 Docker/PostgreSQL 环境依赖，降低首次跑通门槛。
> SQLite 的 JSON 字段通过 `TEXT` + Python `json.loads/dumps` 模拟，不使用 PostgreSQL JSONB 特性。
> 切换到 PostgreSQL 时只需更换 `DATABASE_URL` 和调整 JSON 字段类型，模型层无侵入式改动。
> 如开发环境已具备 Docker，也可直接使用 PostgreSQL 跳过 SQLite 阶段。

该切片完成后，用户应能通过聊天输入学习需求，看到流式回复、获得个性化学习文档卡片，并在画像页查看动态更新后的 6+ 维学习画像。

## 2. 不纳入本切片的范围

以下模块明确不纳入首个实施包：

- 登录注册与 JWT 认证
- QuizAgent / CodeAgent / MediaAgent
- 资源中心页面
- Wiki 导入与 RAG 检索
- Redis / MinIO / Milvus
- 完整 LangGraph 并行编排
- 个性化学习路径规划
- 多用户体系

这些能力将在后续阶段逐步扩展，避免首轮实现被基础设施和横向能力拖慢。

## 3. 推荐实施方案

在三种路径中，选择“比赛可演示的垂直切片”作为首个实现方案。

### 方案结论

优先实现以下闭环：

用户输入学习需求 → Router 判定任务 → Profile 更新画像 → Doc 生成学习文档 → SSE 流式推送到前端 → 聊天页展示结果 → 画像页展示最新画像

### 选择原因

1. 能最快形成真实可演示成果
2. 与赛题核心亮点“对话式画像 + 个性化资源生成”直接对应
3. 代码结构仍可沿用最终架构方向，减少后续返工
4. 为 Quiz / Code / Wiki / Path 等后续模块保留稳定扩展接口

## 4. 系统边界

### 4.1 前端范围

首切片只实现以下页面与组件：

- 聊天页：`frontend/app/(main)/chat/[sessionId]/page.tsx`
- 画像页：`frontend/app/(main)/profile/page.tsx`
- 基础聊天组件
- 流式文本组件
- 文档资源卡片组件
- Agent 状态展示组件

### 4.2 后端范围

首切片只实现以下能力：

- 聊天 SSE 接口
- 画像查询接口
- 简化版 RouterAgent
- 简化版 ProfileAgent
- 简化版 DocAgent
- 会话、消息、画像、生成资源的 SQLite 持久化

### 4.3 切片完成标准

用户应能完成以下操作：

1. 能启动前后端
2. 能在聊天页发送学习请求
3. 能真实调用讯飞星火并获得流式输出
4. 能收到一张学习文档资源卡片
5. 聊天请求触发学生画像更新
6. 打开画像页查看 6+ 维画像结果

## 5. 模块设计

### 5.1 后端模块

建议后端目录与最终架构保持一致，但只实现 MVP 子集：

- `backend/app/main.py`：FastAPI 入口，注册路由
- `backend/app/api/chat.py`：聊天流式接口，负责接收消息、创建或复用会话、调用编排器、输出 SSE
- `backend/app/api/profile.py`：画像查询接口
- `backend/app/agents/router_agent.py`：调用讯飞星火 Lite 做意图识别，输出结构化 JSON（intent + topic + 参数），兜底规则：LLM 调用失败时降级为关键词匹配
- `backend/app/agents/profile_agent.py`：调用讯飞星火 Lite 从用户文本中抽取画像增量（structured output），输出标准化字段 JSON，比纯正则覆盖率更高且更稳定
- `backend/app/agents/doc_agent.py`：只负责基于主题与画像调用真实星火生成个性化学习文档
- `backend/app/agents/orchestrator.py`：串联 Router、Profile、Doc，编排调用顺序与 SSE 事件顺序
- `backend/app/services/chat_service.py`：封装会话创建/复用、消息落库、资源落库
- `backend/app/services/profile_service.py`：封装画像读取、合并与持久化
- `backend/app/core/database.py`：SQLite 与 SQLAlchemy 会话管理
- `backend/app/core/llm.py`：定义统一 LLM 客户端接口，默认真实接入讯飞星火，并为后续 DeepSeek 预留扩展点

### 5.2 前端模块

建议前端模块如下：

- `frontend/app/(main)/chat/[sessionId]/page.tsx`：聊天主页面
- `frontend/components/chat/ChatMessage.tsx`：消息气泡组件
- `frontend/components/chat/StreamingText.tsx`：流式文本组件
- `frontend/components/chat/ResourceCard.tsx`：学习文档卡片组件
- `frontend/components/chat/AgentStatus.tsx`：Agent 状态组件
- `frontend/app/(main)/profile/page.tsx`：画像页
- `frontend/lib/api.ts`：HTTP 请求封装
- `frontend/lib/sse.ts`：SSE 事件解析封装

## 6. 核心数据流

典型输入示例：

> 我是计算机专业大三学生，机器学习基础一般，想复习反向传播，最好有图文结合的讲解。

系统处理流程：

1. 聊天接口接收消息并保存到消息表
2. Orchestrator 调用 RouterAgent 做任务识别
3. Router 判定本次请求需要更新画像并生成学习文档
4. ProfileAgent 调用星火 Lite 从文本中抽取专业、年级、知识基础、学习目标、认知偏好等信息，与默认用户的已有画像合并更新（跨 session 累积）
5. DocAgent 根据画像生成个性化学习文档
6. 后端通过 SSE 依次推送状态事件、画像更新事件、流式文本事件、资源卡片事件与完成事件
7. 前端聊天页实时展示生成过程
8. 用户进入画像页查看更新后的画像结果；若未传 `session_id`，后端先创建默认会话并返回新会话标识，画像按 `session_id` 归属

## 7. 数据模型设计

本阶段采用 SQLite，但字段设计尽量贴近 [PLAN.md](PLAN.md) 中正式结构，便于后续切换 PostgreSQL。

### 7.1 chat_sessions

字段：

- `id`
- `title`
- `created_at`
- `updated_at`

用途：

- 支撑聊天页会话访问
- 为后续多用户扩展保留空间

### 7.2 chat_messages

字段：

- `id`
- `session_id`
- `role`
- `content`
- `message_type`
- `created_at`

用途：

- 保存用户消息与助手回复
- 支持后续消息回放

### 7.3 student_profiles

字段：

- `id`
- `user_id`（固定为默认用户 ID=1，画像跨 session 持久化）
- `session_id`（记录最后更新画像的 session，用于溯源）
- `major`
- `grade`
- `knowledge_base`（JSON）
- `cognitive_style`
- `learning_goal`
- `weak_points`（JSON）
- `learning_pace`
- `interest_areas`（JSON）
- `coding_level`
- `weekly_hours`
- `updated_at`

> **画像持久化策略变更**：原设计画像绑定 `session_id`，导致每次新会话丢失历史画像，
> 与赛题"随学随新"要求冲突。改为画像绑定 `user_id`（MVP 阶段固定为默认用户 1），
> 跨 session 累积更新。`session_id` 字段仅记录最后更新来源，便于调试。

该结构满足赛题所需 6+ 维画像要求。

### 7.4 generated_resources

字段：

- `id`
- `session_id`
- `resource_type`
- `title`
- `content`
- `knowledge_point`
- `agent_name`
- `created_at`

首切片至少支持 `document` 类型。

## 8. SSE 事件协议

为保证后续扩展 Quiz / Code / Media 等 Agent 时无需推翻前端，首个切片先固定基础事件协议。

### 8.1 agent_status

用于展示当前 Agent 工作进度：

```json
{
  "type": "agent_status",
  "agent": "ProfileAgent",
  "status": "working",
  "message": "正在更新学习画像"
}
```

### 8.2 profile_updated

用于通知前端画像已更新：

```json
{
  "type": "profile_updated",
  "profile": {
    "major": "计算机专业",
    "grade": "大三",
    "learning_goal": "复习",
    "cognitive_style": "图文结合"
  }
}
```

### 8.3 token

用于流式正文输出：

```json
{
  "type": "token",
  "content": "反向传播算法的核心思想是..."
}
```

### 8.4 resource_card

用于推送结构化资源卡片：

```json
{
  "type": "resource_card",
  "resource": {
    "id": 1,
    "resource_type": "document",
    "title": "反向传播个性化学习讲义",
    "content": "..."
  }
}
```

### 8.5 done

用于声明本次流式响应结束，且事件顺序约束为：`agent_status(Profile)` → `profile_updated` → `agent_status(Doc)` → 多个 `token` → `resource_card` → `done`。若中途失败，则以 `error` 终止，且不再继续发送后续成功事件。

```json
{
  "type": "done"
}
```

### 8.6 error

用于向前端报告中文错误信息：

```json
{
  "type": "error",
  "message": "生成学习资源失败，请稍后重试"
}
```

## 9. 真实讯飞星火接入约束

- 默认必须走真实讯飞星火调用，不提供“伪成功”的本地 mock 响应。
- 必须通过环境变量配置 `SPARK_APP_ID`、`SPARK_API_KEY`、`SPARK_API_SECRET`。
- 若星火凭证缺失或调用失败，后端返回明确中文错误事件，前端展示失败提示，但不能伪造生成内容。
- LLM 客户端层负责鉴权、请求封装与错误转换，Agent 层不直接拼接底层 HTTP 请求。

## 10. 验收样例

以输入“我是计算机专业大三学生，机器学习基础一般，想复习反向传播，最好有图文结合的讲解”为例，本轮至少应满足：

- 聊天页出现中文流式讲解内容；
- 画像中写入专业、年级、知识基础、学习目标或认知偏好中的至少 4 项有效字段；
- 返回一张 `document` 类型资源卡片；
- SSE 事件顺序符合本规格定义。

首切片不做复杂容灾，但需保证 demo 稳定和错误可感知。

### 9.1 后端

- LLM 调用失败：返回 `error` 事件，不直接中断为 500
- 画像提取失败：保留旧画像，继续走通用文档生成链路
- 文档生成失败：向前端返回明确中文错误
- SQLite 写入失败：向前端返回统一错误消息，日志记录具体原因

### 9.2 前端

- SSE 连接中断：显示“连接已中断，请重试”
- 无数据场景：显示中文空态
- 画像页加载失败：显示可重试状态
- 所有 UI 文案、按钮、状态、错误信息均使用中文

## 10. 测试策略

首切片采用“必要测试 + 手工验证”策略。

### 10.1 后端优先测试项

- RouterAgent 意图判定
- ProfileAgent 画像提取与合并
- DocAgent 输出结构
- 聊天接口 SSE 事件顺序
- 画像接口返回结构

### 10.2 前端优先测试项

- 聊天页流式文本展示
- 资源卡片正确渲染
- 画像页 6+ 维字段展示
- 错误态渲染

### 10.3 手工验证链路

1. 打开聊天页
2. 输入一条同时包含画像信息与学习需求的消息
3. 观察 Agent 状态与流式输出
4. 收到文档卡片
5. 打开画像页确认画像更新成功

## 11. 分阶段优先级

### Phase A：当前首包

- 前后端工程初始化
- 聊天页
- 画像页
- SSE 流式输出
- Router / Profile / Doc 简化闭环
- SQLite 持久化

### Phase B：资源能力扩展

- QuizAgent
- CodeAgent
- 更多资源卡片
- 资源中心页面

### Phase C：知识中枢能力

- 初始知识库导入
- RAG 检索
- Wiki 页面
- 基础知识图谱查询

### Phase D：正式编排与路径规划

- LangGraph 真正接入
- PlannerAgent
- 个性化学习路径规划
- 路径可视化

### Phase E：比赛打磨

- MediaAgent
- 内容安全过滤
- 讯飞工具深度接入
- UI 细节优化
- 提交文档与演示材料完善

## 12. 首个实施包定义

### 12.1 后端首包

- FastAPI 项目初始化
- SQLite + SQLAlchemy
- 聊天、画像、资源模型
- `/api/chat/stream`
- `/api/profile`
- RouterAgent / ProfileAgent / DocAgent / orchestrator
- 真实讯飞星火客户端封装

### 12.2 前端首包

- Next.js 项目初始化
- 暖色 Claude 风格基础布局
- 聊天页
- 画像页
- SSE 消费逻辑
- 文档卡片与 Agent 状态组件

### 12.3 明确排除项

- 登录注册
- RAG
- Redis / MinIO / Milvus
- Quiz / Code / Media
- 学习路径
- 多用户体系

## 13. 结论

首个实现目标不是一次性完成整个 EduAgent，而是先交付一个稳定、可演示、可扩展的垂直切片：

> 单用户模式下的聊天页 + 画像页闭环，后端基于 FastAPI + SQLite + SSE，前端基于 Next.js，完成简化版 Router / Profile / Doc Agent，并为后续真实 LLM 与多 Agent 扩展保留接口。

该设计兼顾了比赛展示效果、实现可控性与后续演进空间，是当前阶段最合适的落地起点。
