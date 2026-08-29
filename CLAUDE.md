# CLAUDE.md - EduAgent 开发指南

## 基本要求

- **始终用中文回答**，包括代码注释、commit message、文档
- **前端界面全部适配中文**：所有 UI 文案、placeholder、toast、错误提示、按钮文字等必须使用中文，不出现英文 UI 文案

---

## 开发原则

**1. 先想清楚再动手，不隐藏困惑、不确定就提问**
- 不要默默选一种解释就往下做；有歧义时列出多种解读，不偷偷选一种
- 存在权衡或更简单的方案时直说；发现不清楚的地方就停下来要求澄清，不要为了显得确定而硬猜

**2. 简洁优先，不过度设计**
- 只实现需求要求的东西，不加"以后可能用到"的功能、抽象或可配置项
- 不为几乎不会发生的场景写防御代码；不为一次性代码建抽象
- 能写短就不写长；写完自问一句：资深工程师会觉得这过于复杂吗？是就简化

**3. 精准修改，只碰该碰的**
- 只改与本次请求直接相关的代码，不顺手"优化"相邻代码/注释/格式，不重构没坏的东西
- 匹配现有风格，即使你有更喜欢的写法
- 自己改动产生的孤儿 import / 变量 / 函数要清理；预先存在的死代码未经要求不要删，发现了提出来即可

**4. 目标驱动，先定义验收标准再执行**
- 把任务转成可验证目标：修 bug → 先写复现测试再让它通过；加功能 → 先写用例再让它们通过；重构 → 重构前后测试都要过
- 多步任务给出简短计划并逐步验证：`1. [步骤] → 验证: [检查]`

---

## 项目概述

EduAgent 是一个以 **LLM Wiki（知识中枢）** 为核心的个性化多 Agent 学习系统，面向高等教育场景。通过 10 个协同 Agent 为学生生成个性化、多模态学习资源，内置多门课程知识库（人工智能导论、计算机网络、算法设计与分析）。这是一个参赛项目，有两种运行形态：

1. **独立 Web 应用**（本仓库主体）：FastAPI 后端 + Next.js 前端
2. **remio aApp 移植版**（`remio/`）：10 个 Agent 重表达为 remio 平台的语义端点，运行在 remio 睿妙上（部署副本在平台侧 `aapps/eduagent/eduagent.aapp/`）

**核心文档：**
- `docs/competition-remio/` — remio 赛道方案说明书（需求 / 系统设计 / 验收口径）
- `remio/aapp/eduagent-aapp-spec.md` — remio aApp 开发规格（10 端点 E1–E10）
- `docs/DEPLOYMENT.md` — 部署运行说明
- `remio/mcp/README.md` — MCP 工具集说明（跨智能体宿主运行）

---

## 技术栈

### 后端 (backend/)
- **语言**: Python 3.12
- **框架**: FastAPI
- **Agent**: LangGraph（多 Agent 编排，见 `app/agents/orchestrator.py`）
- **LLM**: DeepSeek（主）+ OpenAI 兼容接口（备，可配置切换；开发模式 LLM_DEV_MODE=true 返回模拟内容）
- **ORM**: SQLAlchemy（async）+ Alembic (迁移)
- **数据库**: 默认 SQLite（`eduagent.db`，零配置启动），可通过 `DATABASE_URL` 切换 PostgreSQL
- **向量库**: 内置 numpy + JSON 持久化（默认），可切换 Chroma HTTP Server
- **Embedding**: BAAI/bge-small-zh-v1.5（中文）
- **缓存**: Redis（可选）
- **对象存储**: MinIO (S3 兼容，可选)

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
docker compose up -d             # 启动 PG + Redis + MinIO（可选基础设施）
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

### 10 个 Agent 角色

| Agent | 文件 | 职责 |
|-------|------|------|
| Router | `router_agent.py` | 意图识别，路由到正确 Agent |
| Planner | `planner_agent.py` | 复合任务分解，多 Agent 并行编排 |
| Profile | `profile_agent.py` | 对话式 8 维度学生画像构建/更新 |
| Doc | `doc_agent.py` | 讲解文档 + 思维导图 + 拓展材料 |
| Quiz | `quiz_agent.py` | 选择/填空/编程等多类型题目 |
| Code | `code_agent.py` | 可运行的 Python 代码实操案例 |
| Media | `media_agent.py` | PPT + 算法动画 + 教学视频 |
| Reading | `reading_agent.py` | 拓展阅读材料推荐 |
| Tutor | `tutor_agent.py` | 即时答疑 + 苏格拉底式引导 |
| Video | `video_agent.py` | 教学视频资源 |

公共设施：`common.py`（画像感知的 prompt 组装）、`content_guard.py`（输出过滤/防幻觉校验）、`resource_types.py`（资源类型定义）。

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
src/app/(main)/
├── chat/[sessionId]  — 核心对话界面（SSE 流式 + 多模态卡片）
├── profile/          — 学习画像仪表盘（雷达图）
├── resources/        — 资源中心
├── path/             — 学习路径可视化
├── wiki/             — 知识 Wiki 浏览
├── review/           — 复习
└── analytics/        — 学习分析
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

### UI 设计规则

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

1. 在 `frontend/src/app/(main)/` 下创建页面目录
2. 默认写 Server Component，交互部分拆成 Client Component
3. 复用 `components/ui/` 中的 shadcn 基础组件
4. 业务组件放对应的 `components/<feature>/` 目录
5. API 调用通过 `lib/api.ts` 封装

### 知识库结构与更新

知识库在 `backend/knowledge/` 下，**多课程**结构，`backend/app/wiki/courses.py` 会自动发现每个含 `metadata.json` 的子目录并将其注册为课程模板（首个为默认课程）：

- `ai_intro/` — 人工智能导论（AI101，13 章，默认课程）
- `计算机网络知识库/` — 计算机网络（最完整，含总纲/习题/代码案例/实验/媒体资源/附录）
- `算法设计与分析/` — 算法设计与分析（ALG101，10 章 + 习题/代码案例/实验/媒体资源配套）

**每门课程的约定：**
- `metadata.json` — 课程信息与章节定义（`course_id`、`chapters` 列表，章节 ID 如 `ch01`/`al01`）
- `knowledge_graph.json` — 概念图谱（节点/边）
- 章节讲解文档放在 `NN_章节名/` 子目录

**章节文件解析规则（重要）**：`ingestion.py` 的 `_resolve_chapter_file` 在章节未显式指定 `file` 字段时，按 `chapter_{NN}_` 或 `chapter{N}_` 前缀兜底匹配章节文件。因此：

- 新增章节文件必须使用 `chapter_{NN}_<主题>.md` 命名（如 `chapter_01_ai_overview.md`），不要用 `chapter1_xxx.md` 旧命名——旧命名会因字母序抢先匹配到错误章节，导致 RAG 喂错内容（2026-08 已清理过一次 ai_intro 的旧文件）
- 配套资源目录约定（参照计算机网络知识库）：`00_课程总纲`（索引/学习路径）、`08_实验与工具`、`09_习题与解析`（按 选择/判断/计算/简答/综合 分题型子目录）、`10_代码案例`、`11_媒体资源`（PPT大纲/动画脚本/图示说明）
- 资源文档建议带 frontmatter（`doc_id`/`doc_type`/`owner_agent`/`rag` 等，参照现有文件），后端不强制解析，但保持库内风格一致

---

## remio aApp 移植版

`remio/` 目录是本项目在 remio 睿妙平台上的运行形态：10 个 Agent 重表达为 10 个语义端点（E1–E10），实际代码在平台侧 `aapps/eduagent/eduagent.aapp/logic.py`。

**关键机制**（改 aApp 代码前必读 `remio/aapp/eduagent-aapp-spec.md` 和平台 `dev-guide/开发者指南.md`）：

- **知识锚定**：`search_notes` 定位候选 + `read_note` 注入笔记**正文**（不能只给标题）；锚定型端点一律 `run_prompt(capabilities="none")`——纯 LLM 推理，物理禁止联网，防止静默混入网络内容
- **联网双通道**：E9 拓展阅读联网优先（`web_search` + `web_get`，只引用实际抓取成功的 URL）；E10 答疑两级——知识库锚定为一级（模型首行 `GROUNDED`/`INSUFFICIENT` 自报覆盖度），仅 `INSUFFICIENT` 或 `deep=true` 时显式升级联网，来源按 `📚 课程知识库` / `🌐 网络` 分级标注
- **rag 能力的坑**：平台 `rag` 对批量导入的 File 类型笔记可能返回空（问答语料与检索索引是两条管线），项目实际走 `search_notes → run_prompt` 链路，rag 仅作平台侧修复后的可选增强
- **降级纪律**：所有 web 调用必须 try/except 降级到知识库作答并提示（`web_search` 依赖用户配置商业搜索源，且可能额度耗尽）

另外，`backend/app/mcp_server.py` 把 10 个 Agent 封装为 12 个 MCP 工具（stdio JSON-RPC，零三方依赖），可在 remio MCP 外部工具、Claude Desktop 等任何 MCP 宿主中注册运行，见 `remio/mcp/README.md`。

---

## 环境变量

后端环境变量放 `backend/.env`，不提交到 git。**数据库默认 SQLite（`eduagent.db`），本地开发可以完全不配**；需要 PostgreSQL/Redis/MinIO 时才配置对应项：

```
# 可选：切换数据库（默认 sqlite+aiosqlite:///./eduagent.db）
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/eduagent
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# 知识库目录（默认 ./knowledge，多课程自动发现）
WIKI_KNOWLEDGE_DIR=./knowledge

# LLM：DeepSeek（主）
DEEPSEEK_ENABLED=true
DEEPSEEK_API_KEY=xxx

# LLM：OpenAI 兼容接口（备用，可接 qwen 等；主模型失败时自动回退）
OPENAI_COMPATIBLE_ENABLED=true
OPENAI_COMPATIBLE_API_KEY=xxx
OPENAI_COMPATIBLE_API_BASE_URL=https://xxx/v1
OPENAI_COMPATIBLE_MODEL=qwen3.6-plus

# 开发模式（true 时 LLM 返回模拟内容，仅用于本地调试）
LLM_DEV_MODE=false

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
- 不要给 UI 加冷蓝灰色，严格遵守暖色调视觉约定
- 不要跳过 RAG 直接让 LLM 回答学术问题，防幻觉是赛题刚性要求
- 不要在路由层写业务逻辑，保持 API 层薄、service 层厚
