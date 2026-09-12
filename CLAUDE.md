# CLAUDE.md - EduAgent 开发指南

## 基本要求

- **始终用中文回答**，包括代码注释、commit message、文档
- **作品界面与全部产出文案适配中文**：remio aApp 的 UI 文案、卡片、按钮、提示均使用中文，不出现英文 UI 文案

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

EduAgent 是一个以 **LLM Wiki（知识中枢）** 为核心的个性化多 Agent 学习系统，面向高等教育场景。通过 10 个协同 Agent 为学生生成个性化、多模态学习资源，内置多门课程知识库（计算机网络、算法设计与分析）。这是一个参赛项目（2026 智能体 OPC · 金漪湖论剑，remio 赛道），以 **remio aApp 为主体作品**，辅以 **MCP 工具集** 作为跨智能体产品运行的加分项：

1. **remio aApp**（`remio/`）：10 个 Agent 重表达为 remio 平台的语义端点（合计 18 个端点），已上架 remio 应用市场（id `eduagent-pro`），开发副本在 remio 客户端 aapps-dev 目录
2. **MCP 工具集**（`backend/app/mcp_server.py`）：同一引擎封装为 16 个 MCP 工具（含 create_session/list_sessions 会话管理），可在任何支持 MCP 的宿主中注册调用

**核心文档：**
- `docs/competition-remio/` — remio 赛道方案说明书（需求 / 系统设计 / 验收口径）
- `remio/aapp/eduagent-aapp-spec.md` — remio aApp 开发规格（18 个端点：核心 E1–E11 + 扩展）
- `remio/mcp/README.md` — MCP 工具集说明（跨智能体宿主运行）

---

## 技术栈

### 多 Agent 引擎 (backend/)
- **语言**: Python 3.12
- **Agent**: LangGraph（多 Agent 编排，见 `app/agents/orchestrator.py`）
- **LLM**: DeepSeek（主）+ OpenAI 兼容接口（备，可配置切换；开发模式 LLM_DEV_MODE=true 返回模拟内容）
- **ORM**: SQLAlchemy（async）+ Alembic (迁移)
- **数据库**: 默认 SQLite（`eduagent.db`，零配置启动），可通过 `DATABASE_URL` 切换 PostgreSQL
- **向量库**: 内置 numpy + JSON 持久化（默认），可切换 Chroma HTTP Server
- **Embedding**: BAAI/bge-small-zh-v1.5（中文）
- **跨宿主输出**: MCP stdio 服务（`app/mcp_server.py`，16 个工具，零三方依赖）

---

## 关键命令

### 引擎 (backend/)
```bash
cd backend

# 依赖管理 (uv)
uv sync                          # 安装依赖
uv add <package>                 # 添加依赖

# 数据库迁移
uv run alembic upgrade head      # 应用迁移
uv run alembic revision --autogenerate -m "描述"  # 生成迁移

# MCP 自检 / 启动
uv run python -m app.mcp_server --self-test   # 离线自检（不加载模型，只验证导入+工具清单）
uv run python -m app.mcp_server               # 以 MCP stdio 服务启动（供 remio/Claude Desktop 等宿主调用）

# 测试
uv run pytest                    # 全部测试
uv run pytest tests/test_agents/ # Agent 测试
uv run pytest -x -v              # 详细输出，失败即停

# 代码质量
uv run ruff check .              # lint
uv run ruff format .             # format
```

---

## 架构要点

### 引擎目录约定

```
backend/app/
├── agents/       # LangGraph Agent 定义 — 每个 Agent 一个文件（含 orchestrator.py 编排）
├── wiki/         # LLM Wiki 知识中枢 — RAG、向量化、知识图谱
├── models/       # SQLAlchemy 模型
├── schemas/      # 领域模型 / 数据契约（agents/services 复用）
├── services/     # 业务逻辑层
├── core/         # 基础设施（DB、LLM 客户端、配置）
└── mcp_server.py # MCP 工具集（16 个工具，stdio JSON-RPC）
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

默认 SQLite（`eduagent.db`，零配置），可通过 `DATABASE_URL` 切换 PostgreSQL。核心表：
- `student_profiles` — 8 维度学生画像（JSONB）
- `chat_sessions` / `chat_messages` — 对话
- `session_materials` — 会话学习材料（知识库未命中的兜底锚定源）
- `generated_resources` — 生成的多模态资源
- `learning_paths` / `learning_activities` — 个性化学习路径与行为追踪
- `wiki_entries` — 知识 Wiki 条目

---

## 代码风格与约定

### Python (引擎)

- **格式化**: ruff format（行宽 88）
- **lint**: ruff check
- **类型标注**: 所有函数签名必须有类型标注
- **异步优先**: service / Agent 方法用 `async def`
- **Pydantic**: 数据契约用 Pydantic v2 BaseModel
- **命名**: snake_case（函数/变量），PascalCase（类），UPPER_SNAKE_CASE（常量）
- **导入顺序**: stdlib → 第三方 → 本地，各组间空行

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

---

## 开发工作流

### 添加新 Agent

1. 在 `backend/app/agents/` 创建 `xxx_agent.py`
2. 实现核心 `generate()` 或 `process()` 异步方法
3. 在 `orchestrator.py` 中注册到 LangGraph 图
4. 写测试 `tests/test_agents/test_xxx_agent.py`

### 知识库结构与更新

知识库在 `knowledge/` 下（仓库根目录，已从 `backend/knowledge/` 迁出），**多课程**结构，`backend/app/wiki/courses.py` 会自动发现课程模板：`WIKI_KNOWLEDGE_DIR` 指向的目录为默认课程，同级含 `metadata.json` 的目录一并注册为其他课程模板（默认指向计算机网络）：

- `计算机网络知识库/` — 计算机网络（CN101，13 章：总纲 + 12 讲 + 附录，含事实卡/实验/题库/代码案例/媒体资源/知识图谱，默认课程）
- `算法设计与分析/` — 算法设计与分析（ALG101，10 章 + 习题/代码案例/实验/媒体资源配套）

**每门课程的约定：**
- `metadata.json` — 课程信息与章节定义（`course_id`、`chapters` 列表，章节 ID 如 `ch01`/`al01`）
- `knowledge_graph.json` — 概念图谱（节点/边）
- 章节讲解文档放在 `NN_章节名/` 子目录

**章节文件解析规则（重要）**：`ingestion.py` 的 `_resolve_chapter_file` 在章节未显式指定 `file` 字段时，按 `chapter_{NN}_` 或 `chapter{N}_` 前缀兜底匹配章节文件。因此：

- 新增章节文件必须使用 `chapter_{NN}_<主题>.md` 命名（如 `chapter_01_网络概述.md`），不要用 `chapter1_xxx.md` 旧命名——旧命名会因字母序抢先匹配到错误章节，导致 RAG 喂错内容
- 配套资源目录约定（参照计算机网络知识库）：`00_课程总纲`（索引/学习路径）、`08_实验与工具`、`09_习题与解析`（按 选择/判断/计算/简答/综合 分题型子目录）、`10_代码案例`、`11_媒体资源`（PPT大纲/动画脚本/图示说明）
- 资源文档建议带 frontmatter（`doc_id`/`doc_type`/`owner_agent`/`rag` 等，参照现有文件），引擎不强制解析，但保持库内风格一致

---

## remio aApp 移植版

`remio/` 目录是本项目在 remio 睿妙平台上的运行形态：10 个 Agent 重表达为 11 个核心语义端点（E1–E11）+ 判题 / PPT 配图 / 薄弱点复习 / 动画 / 视频 5 个扩展端点，连同主入口与内容事件订阅合计 18 个端点（与平台侧 `api.json` 对齐）。aApp 已上架市场（id `eduagent-pro`），开发副本在 remio 客户端 aapps-dev 目录（本机绝对路径，改 aApp 代码直接来这里）：

```
D:\App\remiocn\Users\B60CFB8513AF4288DF6E5A688248A005\agent\remio\aapps-dev\eduagent-pro\eduagent-pro\
├── logic.py      # 运行时逻辑（E1–E11 + 扩展端点实现，改动主战场）
├── api.json      # 平台侧端点声明（须与 logic.py 路由保持一致）
├── manifest.json # 应用元数据（订阅 / 快捷菜单 / chatMenu）
├── SKILL.md      # 端点语义契约说明（须与 logic.py 行为保持一致）
└── data/kb/      # 内置知识库（计算机网络 Markdown 文件，随 aApp 分发，146 个文件约 0.44 MB）
```

改 logic.py 后需在 aapp-studio 重新加载才生效；若路径中用户哈希变化，在 `D:\App\remiocn\Users\<用户哈希>\agent\remio\aapps-dev\` 下找 `eduagent-pro`。

**关键机制**（改 aApp 代码前必读 `remio/aapp/eduagent-aapp-spec.md` 和平台 `dev-guide/开发者指南.md`）：

- **知识锚定**：`search_notes` 定位候选 + `read_note` 注入笔记**正文**（不能只给标题）；锚定型端点一律 `run_prompt(capabilities="none")`——纯 LLM 推理，物理禁止联网，防止静默混入网络内容
- **Tier 1 双路径**：优先查 remio 同步文件夹（`计算机网络知识库`）；未命中则回退到内置 `data/kb/` 关键词匹配（文件级搜索，无需 remio 索引）。内置知识库已随 aApp 分发，其他用户安装后即可使用 Tier 1b 作为兜底锚定源。
- **联网双通道**：E9 拓展阅读联网优先（`web_search` + `web_get`，只引用实际抓取成功的 URL）；E10 答疑三级兜底——覆盖层级由代码按各层检索命中判定（同步文件夹 → 内置知识库 → 课程知识库 → 会话学习材料 → 网络），每次层级以 `📚 课程知识库` / `📎 会话材料` / `🌐 网络` 在解答卡片显式标注，禁止静默切换
- **rag 能力的坑**：平台 `rag` 对批量导入的 File 类型笔记可能返回空（问答语料与检索索引是两条管线），项目实际走 `search_notes → run_prompt` 链路，rag 仅作平台侧修复后的可选增强
- **降级纪律**：所有联网调用必须 try/except 降级到知识库作答并提示（`web_search` 依赖用户配置商业搜索源，且可能额度耗尽）

另外，`backend/app/mcp_server.py` 把 10 个 Agent 封装为 16 个 MCP 工具（stdio JSON-RPC，零三方依赖；含 create_session/list_sessions 会话管理工具），可在 remio MCP 外部工具、Claude Desktop 等任何 MCP 宿主中注册运行，见 `remio/mcp/README.md`。

---

## 环境变量

引擎环境变量放 `backend/.env`，不提交到 git。**数据库默认 SQLite（`eduagent.db`），本地开发可以完全不配**；需要 PostgreSQL 等时才配置对应项：

```
# 可选：切换数据库（默认 sqlite+aiosqlite:///./eduagent.db）
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/eduagent

# 知识库目录（默认指向计算机网络课程并作为默认课程，同级算法课程自动发现）
WIKI_KNOWLEDGE_DIR=../knowledge/计算机网络知识库

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
```

---

## 不要做的事

- 不要在 Agent 中硬编码知识内容，所有知识走 LLM Wiki 检索
- 不要用同步阻塞调用 LLM，全部用 async
- 不要跳过 RAG 直接让 LLM 回答学术问题，防幻觉是赛题刚性要求
- 不要在 MCP 工具 / Service 层叠业务胶水，保持工具薄、服务层承载编排