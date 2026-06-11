# CLAUDE.md - EduAgent 开发指南

## 基本要求

- **始终用中文回答**，包括代码注释、commit message、文档
- **前端界面全部适配中文**：所有 UI 文案、placeholder、toast、错误提示、按钮文字等必须使用中文，不出现英文 UI 文案

---

## 项目概述

EduAgent 是一个以 **LLM Wiki（知识中枢）** 为核心的个性化多 Agent 学习系统，面向高等教育场景。通过 8 个协同 Agent 为学生生成个性化、多模态学习资源。这是一个参赛项目（科大讯飞相关赛事）。

**核心设计文档：**
- `PLAN.md` — 完整架构设计（Agent 角色、数据库、目录结构、开发阶段）
- `DESIGN.md` — Claude 风格 UI 设计系统（色彩、字体、组件样式）
- `项目要求.md` — 赛题需求原文

---

## 技术栈

### 后端 (backend/)
- **语言**: Python 3.12
- **框架**: FastAPI
- **Agent**: LangGraph（多 Agent 编排）
- **LLM**: 讯飞星火（主）+ DeepSeek（辅）
- **ORM**: SQLAlchemy + Alembic (迁移)
- **数据库**: PostgreSQL
- **向量库**: Milvus 或 Chroma（RAG）
- **缓存**: Redis
- **对象存储**: MinIO (S3 兼容)

### 前端 (frontend/)
- **框架**: Next.js 15 (App Router) + React 19 + TypeScript
- **样式**: Tailwind CSS + shadcn/ui
- **流式**: SSE (Server-Sent Events)
- **图表**: recharts (雷达图等)

---

## 关键命令

### 后端
```bash
cd backend

# 依赖管理 (uv)
uv sync                          # 安装依赖
uv add <package>                 # 添加依赖

# 开发
uv run uvicorn app.main:app --reload --port 8000

# 数据库迁移
uv run alembic upgrade head      # 应用迁移
uv run alembic revision --autogenerate -m "描述"  # 生成迁移

# 测试
uv run pytest                    # 全部测试
uv run pytest tests/test_agents/ # Agent 测试
uv run pytest -x -v              # 详细输出，失败即停

# 代码质量
uv run ruff check .              # lint
uv run ruff format .             # format
```

### 前端
```bash
cd frontend

pnpm install                     # 安装依赖
pnpm dev                         # 开发服务器 (localhost:3000)
pnpm build                       # 生产构建
pnpm lint                        # ESLint
pnpm type-check                  # TypeScript 类型检查
```

### 基础设施
```bash
docker compose up -d             # 启动 PG + Redis + MinIO + Milvus
docker compose down              # 停止
docker compose logs -f postgres  # 查看日志
```

---

## 架构要点

### 后端目录约定

```
backend/app/
├── api/          # FastAPI 路由 — 薄层，仅参数校验和调用 service
├── agents/       # LangGraph Agent 定义 — 每个 Agent 一个文件
│   └── tools/    # Agent 使用的工具函数
├── wiki/         # LLM Wiki 知识中枢 — RAG、向量化、知识图谱
├── models/       # SQLAlchemy 模型
├── services/     # 业务逻辑层
└── core/         # 基础设施（DB、Redis、LLM 客户端、认证）
```

### 8 个 Agent 角色

| Agent | 文件 | 职责 |
|-------|------|------|
| Router | `router_agent.py` | 意图识别，路由到正确 Agent |
| Planner | `planner_agent.py` | 复合任务分解，多 Agent 并行编排 |
| Profile | `profile_agent.py` | 对话式 8 维度学生画像构建/更新 |
| Doc | `doc_agent.py` | 讲解文档 + 思维导图 + 拓展材料 |
| Quiz | `quiz_agent.py` | 选择/填空/编程等多类型题目 |
| Code | `code_agent.py` | 可运行的 Python 代码实操案例 |
| Media | `media_agent.py` | PPT + 算法动画 + 教学视频 |
| Tutor | `tutor_agent.py` | 即时答疑 + 苏格拉底式引导 |

**编排规则**：
- Router 先行，识别意图
- 复合任务交给 Planner 分解
- ProfileAgent 串行优先（其他 Agent 依赖画像数据）
- DocAgent / QuizAgent / CodeAgent 可并行执行
- MediaAgent 按需触发

### LLM Wiki 知识中枢

Wiki 是所有 Agent 的共享知识层，三个子系统：
1. **知识图谱** — 章节→知识点→概念的 DAG 依赖关系
2. **RAG 检索** — 向量 + BM25 混合搜索，Rerank 重排
3. **内容管理** — Agent 生成内容可回写，版本管理

### 数据库

PostgreSQL，核心表：
- `users` — 用户
- `student_profiles` — 8 维度学生画像（JSONB）
- `chat_sessions` / `chat_messages` — 对话
- `generated_resources` — 生成的多模态资源
- `learning_paths` — 个性化学习路径
- `learning_activities` — 学习行为追踪
- `wiki_entries` — 知识 Wiki 条目

### 前端页面结构

```
app/(main)/
├── chat/[sessionId]  — 核心对话界面（SSE 流式 + 多模态卡片）
├── profile/          — 学习画像仪表盘（雷达图）
├── resources/        — 资源中心
├── path/             — 学习路径可视化
└── wiki/             — 知识 Wiki 浏览
```

---

## 代码风格与约定

### Python (后端)

- **格式化**: ruff format（行宽 88）
- **lint**: ruff check
- **类型标注**: 所有函数签名必须有类型标注
- **异步优先**: FastAPI 路由和 service 方法用 `async def`
- **Pydantic**: 请求/响应模型用 Pydantic v2 BaseModel
- **命名**: snake_case（函数/变量），PascalCase（类），UPPER_SNAKE_CASE（常量）
- **导入顺序**: stdlib → 第三方 → 本地，各组间空行

```python
# API 路由模板
@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    ...
```

```python
# Agent 定义模板
class DocAgent:
    """文档生成 Agent — 根据画像生成个性化学习文档"""

    def __init__(self, llm: BaseLLM, wiki: WikiEngine):
        self.llm = llm
        self.wiki = wiki

    async def generate(self, topic: str, profile: StudentProfile) -> Resource:
        # 1. 从 Wiki 检索相关知识
        context = await self.wiki.search(topic)
        # 2. 根据画像调整 prompt
        prompt = self._build_prompt(topic, profile, context)
        # 3. 调用 LLM 生成
        content = await self.llm.agenerate(prompt)
        return Resource(type="document", content=content)
```

### TypeScript (前端)

- **格式化**: Prettier（自动）
- **lint**: ESLint (next.js 默认配置)
- **组件**: 函数组件 + hooks，不用 class 组件
- **命名**: PascalCase（组件/类型），camelCase（函数/变量）
- **状态管理**: zustand（轻量）或 React Context（简单场景）
- **样式**: Tailwind 工具类优先，不写自定义 CSS 除非必要
- **服务端组件优先**: 默认 Server Component，需要交互时加 `"use client"`

### UI 设计规则（DESIGN.md）

**必须遵守的视觉约定：**
- 页面背景色 `#f5f4ed`（Parchment），不用纯白
- 卡片背景 `#faf9f5`（Ivory）
- 主色调 `#c96442`（Terracotta），仅用于主 CTA
- 所有灰色必须带暖色调（黄褐底），禁止冷蓝灰
- 标题用衬线字体 Georgia（权重 500），正文用 sans-serif
- 阴影用 ring shadow（`0px 0px 0px 1px`），不用 drop shadow
- 圆角 8-12px（按钮/卡片），不用尖角

---

## 开发工作流

### 添加新 Agent

1. 在 `backend/app/agents/` 创建 `xxx_agent.py`
2. 实现核心 `generate()` 或 `process()` 异步方法
3. 在 `orchestrator.py` 中注册到 LangGraph 图
4. 如果 Agent 需要工具，在 `agents/tools/` 添加
5. 写测试 `tests/test_agents/test_xxx_agent.py`

### 添加新 API 端点

1. 在 `backend/app/api/` 对应文件添加路由
2. 请求/响应模型定义在路由文件内或 `models/` 中
3. 业务逻辑放 `services/`，路由层保持薄
4. 需要认证的端点加 `Depends(get_current_user)`

### 添加前端页面

1. 在 `frontend/app/(main)/` 下创建页面目录
2. 默认写 Server Component，交互部分拆成 Client Component
3. 复用 `components/ui/` 中的 shadcn 基础组件
4. 业务组件放对应的 `components/<feature>/` 目录
5. API 调用通过 `lib/api.ts` 封装

### 知识库内容更新

初始知识库在 `backend/knowledge/ai_intro/` 下，Markdown 格式：
- 每章一个 `.md` 文件
- `metadata.json` 定义课程结构和知识点依赖
- `knowledge_graph.json` 定义概念间的 DAG 依赖

---

## 赛题硬性要求清单

开发时务必确保满足以下赛题刚性约束：

1. **画像维度 >= 6 个** — 当前设计 8 个维度
2. **资源类型 >= 5 种** — 当前设计 7 种（文档/思维导图/题目/代码/PPT/动画/拓展阅读）
3. **必须体现"多智能体"架构** — 8 个 Agent 有明确角色分工和协同
4. **讯飞工具** — AI 辅助工具需选用科大讯飞（星火 LLM / TTS / OCR / 内容审核）
5. **防幻觉** — RAG + 自检 + 输出过滤三道防线
6. **流式输出** — SSE 实现，不能白屏等待
7. **初始知识库** — 需自行构造人工智能导论课程文档集
8. **开源协议声明** — 使用的开源项目需在文档中标注

---

## 环境变量

后端需要的环境变量（放 `backend/.env`，不提交到 git）：

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/eduagent
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# 讯飞星火
SPARK_APP_ID=xxx
SPARK_API_KEY=xxx
SPARK_API_SECRET=xxx

# DeepSeek (备用)
DEEPSEEK_API_KEY=xxx

# JWT
JWT_SECRET_KEY=xxx
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

---

## 不要做的事

- 不要在 Agent 中硬编码知识内容，所有知识走 LLM Wiki 检索
- 不要用同步阻塞调用 LLM，全部用 async
- 不要把前端状态全塞 Context，用 zustand 管复杂状态
- 不要给 UI 加冷蓝灰色，严格遵守 DESIGN.md 的暖色调
- 不要跳过 RAG 直接让 LLM 回答学术问题，防幻觉是赛题刚性要求
- 不要在路由层写业务逻辑，保持 API 层薄、service 层厚
