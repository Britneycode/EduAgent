# EduAgent 个性化学习智能体

> 以 **LLM Wiki（知识中枢）** 为核心、面向高等教育场景的个性化多 Agent 学习系统。
> 参赛作品：2026 智能体 OPC 创新大会 · 金漪湖论剑（remio 赛道），前身为科大讯飞相关赛事作品。

EduAgent 不只是问答机器人，而是"**先理解学生，再组织知识，再生成资源，再陪伴学习**"的完整闭环：通过对话式 8 维学生画像理解学习者差异，以内置课程知识库做检索增强与防幻觉锚定，协同生成讲义、练习题、代码实操、思维导图、PPT、拓展阅读等多模态学习资源，并提供苏格拉底式答疑与学习路径规划。

---

## 核心特性

- **多 Agent 协同**：Router / Planner / Profile / Doc / Quiz / Code / Media / Reading / Tutor / Video 共 10 个 Agent，LangGraph 编排，画像串行优先、资源并行生成
- **对话式 8 维学生画像**：专业、年级、知识基础、学习目标、编程水平、认知风格、可投入时长、偏好资源类型；LLM 结构化抽取 + 规则兜底，随交互持续更新
- **LLM Wiki 知识中枢**：知识图谱（概念 DAG 依赖）+ 向量/BM25 混合检索（bge-small-zh 中文向量）+ 内容回写，所有 Agent 共享
- **多课程知识库**：人工智能导论（13 章）、计算机网络（160+ 篇全栈资源）、算法设计与分析（10 章 + 习题/代码/实验/媒体全套配套），多课程自动发现与切换
- **防幻觉三防线**：RAG 检索锚定 → 生成约束（只依据检索片段、不足则标注）→ 输出过滤（`content_guard` 校验来源引用）
- **流式交互**：SSE 流式输出 + 阶段状态提示，前端 Next.js 多模态卡片渲染
- **讯飞工具链**：星火 LLM 主模型、讯飞内容审核护栏、讯飞 TTS 资源朗读

## 两种运行形态

| 形态 | 位置 | 说明 |
|---|---|---|
| 独立 Web 应用 | `backend/` + `frontend/` | FastAPI + Next.js，本仓库主体 |
| remio aApp | `remio/`（规格）+ 平台侧 `aapps/eduagent/eduagent.aapp/` | 10 Agent 重表达为 10 个语义端点（E1–E10），运行在 remio 睿妙：知识库锚定答疑、联网拓展阅读、两级可信来源标注 |
| MCP 工具集 | `backend/app/mcp_server.py` | 10 个 Agent 封装为 12 个 MCP 工具（stdio JSON-RPC，零三方依赖），可在 remio / Claude Desktop 等任何 MCP 宿主注册调用 |

---

## 项目结构

```
EduAgent/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── agents/          # 10 个 Agent + LangGraph 编排（orchestrator.py）
│   │   ├── api/             # 路由薄层（auth/chat/profile/resources/wiki/...）
│   │   ├── services/        # 业务逻辑层
│   │   ├── wiki/            # LLM Wiki：多课程发现、摄取、向量检索、知识图谱
│   │   ├── models/          # SQLAlchemy 模型（默认 SQLite，可切 PostgreSQL）
│   │   ├── core/            # 配置、LLM 客户端、认证
│   │   └── mcp_server.py    # MCP 工具集（12 个工具）
│   ├── knowledge/           # 多课程知识库（见下）
│   └── tests/               # pytest（agents/api/core/evals）
├── frontend/                # Next.js 15 (App Router) + React 19 + Tailwind
│   └── src/app/(main)/      # chat / profile / resources / path / wiki / review / analytics
├── remio/                   # remio aApp 规格、赛道文档、MCP 说明
├── docs/                    # 赛事文档（competition / competition-remio）
└── docker-compose.yml       # 可选基础设施：PostgreSQL + Redis + MinIO
```

### 知识库（`backend/knowledge/`）

| 课程 | 目录 | 规模 |
|---|---|---|
| 人工智能导论（AI101） | `ai_intro/` | 13 章，默认课程 |
| 计算机网络 | `计算机网络知识库/` | 8 章讲解 + 总纲 + 习题解析 + 代码案例 + 实验工具 + 媒体资源 + 附录（事实卡/图谱/模板） |
| 算法设计与分析（ALG101） | `算法设计与分析/` | 10 章 + 选择/判断/计算/简答/综合五类习题 + 9 个代码案例 + 4 个实验 + PPT/动画/图示 |

每个课程目录含 `metadata.json`（课程信息与章节定义）和 `knowledge_graph.json`（概念图谱），后端自动发现并注册为课程模板。新增课程的目录与命名约定见 `CLAUDE.md`（注意章节文件必须用 `chapter_{NN}_` 前缀命名）。

---

## 快速开始

### 后端

```bash
cd backend
uv sync                                   # 安装依赖

cp .env.example .env 2>/dev/null || true  # 配置 LLM 凭证（星火 / DeepSeek / OpenAI 兼容，任选其一）
# 数据库默认 SQLite，本地开发零配置

uv run uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev          # http://localhost:3000
```

### 可选基础设施

```bash
docker compose up -d      # PostgreSQL + Redis + MinIO（按需，默认不启用也可运行）
```

### MCP 自检

```bash
cd backend && uv run python -m app.mcp_server --self-test
```

测试：`cd backend && uv run pytest`；前端：`pnpm build && pnpm type-check`。

---

## 文档索引

| 文档 | 内容 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 开发约束、架构要点、代码风格、知识库维护约定（**改代码前必读**） |
| [DEPLOYMENT.md](DEPLOYMENT.md) | 部署运行说明 |
| [remio/aapp/eduagent-aapp-spec.md](remio/aapp/eduagent-aapp-spec.md) | remio aApp 规格：10 端点定义、能力分工、防幻觉与联网双通道设计 |
| [remio/mcp/README.md](remio/mcp/README.md) | MCP 工具集：12 个工具清单与宿主注册方法 |
| [docs/competition-remio/](docs/competition-remio/) | remio 赛道：方案文档、演示脚本、视频分镜、合规说明 |
| [docs/competition/](docs/competition/) | 原赛事（科大讯飞）文档 |
| [frontend/README.md](frontend/README.md) | 前端说明 |

---

## 技术栈

- **后端**：Python 3.12 · FastAPI · LangGraph · SQLAlchemy (async) · SQLite/PostgreSQL · numpy/Chroma 向量检索 · bge-small-zh-v1.5 Embedding
- **前端**：Next.js 15 (App Router) · React 19 · TypeScript · Tailwind CSS · shadcn/ui · SSE
- **LLM**：讯飞星火（主）· DeepSeek · OpenAI 兼容接口（均可配置）
- **平台移植**：remio aApp（语义端点 + run_prompt/search_notes/web_search 编排）· MCP stdio
