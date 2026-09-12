# EduAgent 个性化学习智能体

> 以 **LLM Wiki（知识中枢）** 为核心、面向高等教育场景的个性化多 Agent 学习系统。
> 参赛作品：2026 智能体 OPC 创新大会 · 金漪湖论剑（remio 赛道）。

EduAgent 不只是问答机器人，而是"**先理解学生，再组织知识，再生成资源，再陪伴学习**"的完整闭环：通过对话式 8 维学生画像理解学习者差异，以内置课程知识库做检索增强与防幻觉锚定，协同生成讲义、练习题、代码实操、思维导图、PPT、拓展阅读等多模态学习资源，并提供苏格拉底式答疑与学习路径规划。

---

## 运行形态

| 形态 | 位置 | 说明 |
|---|---|---|
| remio aApp（主力作品） | 已上架市场（id `eduagent-pro`，v6），规格 `remio/`，开发副本在 remio 客户端 aapps-dev | 10 Agent 重表达为 18 个端点（核心 E1–E11 + 判题/配图/复习/动画/视频扩展），内置 146 个文件的计算机网络知识库（data/kb/），运行在 remio 睿妙：三级可信来源标注（同步文件夹 → 内置知识库 → 网络） |
| MCP 工具集 | `backend/app/mcp_server.py` | 10 个 Agent 封装为 16 个 MCP 工具（含 create_session/list_sessions 会话管理，stdio JSON-RPC，零三方依赖），可在 remio / Claude Desktop 等任何 MCP 宿主注册调用 |

---

## 核心特性

- **多 Agent 协同**：Router / Planner / Profile / Doc / Quiz / Code / Media / Reading / Tutor / Video 共 10 个 Agent，LangGraph 编排，画像串行优先、资源并行生成
- **对话式 8 维学生画像**：专业、年级、知识基础、学习目标、编程水平、认知风格、可投入时长、偏好资源类型；LLM 结构化抽取 + 规则兜底，随交互持续更新
- **LLM Wiki 知识中枢**：知识图谱（概念 DAG 依赖）+ 向量/BM25 混合检索（bge-small-zh 中文向量）+ 内容回写，所有 Agent 共享
- **多课程知识库**：计算机网络（13 章全栈资源：总纲/讲解/实验/题库/代码案例/媒体/事实卡/知识图谱，默认课程）、算法设计与分析（10 章 + 习题/代码/实验/媒体配套），多课程自动发现与切换。计算机网络知识库已内置到 aApp（`data/kb/`，146 个文件），随 aApp 安装即用，无需用户手动配置。
- **防幻觉三防线**：RAG 检索锚定 → 生成约束（只依据检索片段、不足则标注）→ 输出过滤（`content_guard` 校验来源引用）

---

## 项目结构

```
EduAgent/
├── backend/                 # 多 Agent 引擎 + MCP 服务（纯引擎，无 HTTP Web 层）
│   ├── app/
│   │   ├── agents/          # 10 个 Agent + LangGraph 编排（orchestrator.py）
│   │   ├── services/        # 业务逻辑层
│   │   ├── wiki/            # LLM Wiki：多课程发现、摄取、向量检索、知识图谱
│   │   ├── models/          # SQLAlchemy 模型（默认 SQLite，可切 PostgreSQL）
│   │   ├── core/            # 配置、LLM 客户端
│   │   └── mcp_server.py    # MCP 工具集（16 个工具）
│   └── tests/               # pytest（agents/core/evals）
├── knowledge/               # 多课程知识库（见下）
├── remio/                   # remio aApp 规格、参赛文档、MCP 说明
└── docs/competition-remio/  # 赛事工程文档（方案说明书 / 技术方案 PDF / 路演 PPT）
```

### 知识库（`knowledge/`）

| 课程 | 目录 | 规模 |
|---|---|---|
| 计算机网络（CN101） | `计算机网络知识库/` | 13 章（总纲 + 12 讲 + 附录），含事实卡/实验/题库/代码案例/PPT/动画/图示/知识图谱，默认课程 |
| 算法设计与分析（ALG101） | `算法设计与分析/` | 10 章 + 选择/判断/计算/简答/综合五类习题 + 代码案例 + 实验 + PPT/动画/图示 |

每个课程目录含 `metadata.json`（课程信息与章节定义）和 `knowledge_graph.json`（概念图谱），引擎自动发现并注册为课程模板。新增课程的目录与命名约定见 `CLAUDE.md`（注意章节文件必须用 `chapter_{NN}_` 前缀命名）。

---

## 快速开始

### 引擎依赖

```bash
cd backend
uv sync                                  # 安装依赖
cp .env.example .env 2>/dev/null || true # 配置 LLM 凭证（DeepSeek / OpenAI 兼容，任选其一）
# 数据库默认 SQLite，本地开发零配置
```

### MCP 自检

```bash
cd backend && uv run python -m app.mcp_server --self-test
```

测试：`cd backend && uv run pytest`。

### remio aApp

aApp 已在 remio 市场发布（id `eduagent-pro`）。开发副本位于 remio 客户端 `aapps-dev` 目录，改 `logic.py` / `api.json` 后在 aapp-studio 重新加载生效；开发规格见 `remio/aapp/eduagent-aapp-spec.md`。

---

## 文档索引

| 文档 | 内容 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 开发约束、架构要点、代码风格、知识库维护约定（**改代码前必读**） |
| [remio/aapp/eduagent-aapp-spec.md](remio/aapp/eduagent-aapp-spec.md) | remio aApp 规格：18 个端点定义、能力分工、防幻觉与联网双通道设计 |
| [remio/mcp/README.md](remio/mcp/README.md) | MCP 工具集：16 个工具清单与宿主注册方法 |
| [docs/competition-remio/](docs/competition-remio/) | remio 赛道：方案说明书（需求 / 系统设计 / 验收口径） |

---

## 技术栈

- **引擎**：Python 3.12 · LangGraph · SQLAlchemy (async) · SQLite/PostgreSQL · numpy/Chroma 向量检索 · bge-small-zh-v1.5 Embedding
- **LLM**：DeepSeek（主）· OpenAI 兼容接口（备，均可配置）
- **平台移植**：remio aApp（语义端点 + run_prompt/search_notes/web_search 编排，18 个端点）· MCP stdio（16 个工具）