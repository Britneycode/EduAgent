# EduAgent

> 面向科大讯飞相关赛事的参赛作品：一个以 **LLM Wiki（知识中枢）** 为核心、面向高等教育场景的个性化多 Agent 学习系统。

EduAgent 不只是一个问答机器人，而是一个能够 **理解学生差异、动态构建学习画像、协同生成多模态学习资源、规划学习路径并持续陪伴学习** 的智能学习中枢。项目以《人工智能导论》课程为切入点，并已扩展出轻量多课程模板能力，围绕赛题中“因材施教、多智能体协同、资源个性化生成、防幻觉与流式交互”的关键要求进行设计与实现。

---

## 项目定位

在传统高校学习场景中，学生常常面临以下问题：

- 学习资源分散，难以快速找到适合自己当前基础的材料
- 通用型智能问答工具更擅长“回答问题”，但不擅长“理解学生”
- 缺少能够围绕学习目标持续生成讲义、题目、代码案例、路径建议的完整系统
- 缺少兼顾个性化、可解释性与可持续积累的知识中枢

EduAgent 希望解决的，不只是“给学生一个答案”，而是让系统具备“**先理解学生，再组织知识，再生成资源，再陪伴学习**”的能力。

---

## 与赛题要求的契合

EduAgent 从架构设计之初就围绕赛题硬性约束展开，重点覆盖以下能力：

- **多智能体协同**：采用 Router + Planner + 多专业 Agent 的协同模式，而非单一 Agent 生成
- **学生画像维度不少于 6 个**：设计为 8 维动态学习画像
- **资源类型不少于 5 种**：覆盖文档、思维导图、练习题、代码、PPT、动画分镜、拓展阅读等 7 类资源
- **使用讯飞相关工具**：主模型方案采用讯飞星火，并可按配置启用讯飞安全护栏与在线语音合成 TTS
- **防幻觉机制**：以 LLM Wiki、RAG 检索、知识图谱和内容过滤构成多层防线
- **流式交互体验**：核心对话接口采用 SSE 流式输出，并提供阶段状态提示
- **初始知识库构建**：以《人工智能导论》为主课程，自建课程知识体系与知识图谱，并提供 Python 程序设计基础样例课程用于多课程切换

---

## 核心亮点

### 1. 多 Agent 协同，而非单点问答

EduAgent 将学习任务拆解为意图识别、任务规划、画像更新、资源生成与即时辅导等多个阶段，由不同 Agent 分工协作完成，提升输出的针对性与系统可扩展性。

### 2. 对话式 8 维学生画像（LLM 抽取 + 动态更新）

系统通过自然语言交互、学习行为与任务反馈动态更新画像，不依赖静态问卷；画像更新支持 LLM 结构化抽取，并提供规则兜底，保证可用性。

### 3. LLM Wiki 作为共享知识中枢

所有 Agent 共享一套以知识图谱、RAG 检索与内容回写为核心的知识底座，既支撑检索增强，又保证系统具备知识沉淀与持续演化能力。

### 4. 多模态个性化资源生成（并行生成）

围绕同一学习目标，系统可组织讲义、练习题、代码实操、PPT、思维导图、拓展阅读等多种资源；后端支持并行生成以降低等待时间。

### 5. 面向比赛展示的完整链路

项目不仅强调技术实现，还强调从“问题识别 → 个性化生成 → 路径规划 → 学习支持”的完整闭环，便于评委理解系统价值与落地潜力。

---

## 典型使用流程

一个典型的 EduAgent 学习流程如下：

```text
学生提出学习问题或目标
   ↓
Router Agent 识别意图（答疑 / 讲解 / 练习 / 代码 / 路径规划）
   ↓
Planner Agent 进行任务拆解与多 Agent 编排
   ↓
Profile Agent 结合历史对话与行为数据更新学生画像
   ↓
Doc / Quiz / Code / Media / Tutor 等 Agent 协同生成资源
   ↓
LLM Wiki 提供知识检索、前置知识追踪、关联知识支撑
   ↓
输出个性化讲义、练习题、代码案例、学习路径或即时辅导结果
   ↓
优质内容回写 Wiki，形成可持续积累的知识资产
```

这意味着 EduAgent 的核心价值并不是“一次性回答”，而是围绕学生的目标构建 **持续学习支持链路**。

---

## 核心功能总览

为避免展示与实现边界不清，以下内容明确区分为“当前已实现”与“规划中能力”。

### 当前已实现

- 用户注册、登录与基于 JWT 的认证流程
- 聊天会话创建、历史会话查看与 SSE 流式对话输出
- 多轮上下文：Tutor 答疑可携带最近对话历史
- Router LLM 路由：支持结构化决策输出，并提供规则兜底
- Profile LLM 画像抽取：支持从自然语言中提取画像更新，并提供规则兜底
- 资源生成并行化：文档先行，其余资源并行生成
- Agent 可观测面板：编排节点和资源 Agent 运行事件会写入事件表，`/api/learning/agent-observability` 聚合展示耗时、状态、资源类型、LLM 调用、token 估算与错误信息；学习分析页已接入该面板
- 自动评测集：`backend/tests/evals` 用固定样例覆盖画像抽取、路由、RAG 命中、题目结构和内容安全；`docs/evaluation.md` 说明评测命令、样例文件和扩展规则
- 稳定演示脚本与样例数据：`docs/demo-script.md` 固化 10 分钟演示路线，`backend/knowledge/ai_intro/demo_scenario.json` 固化演示账号、画像输入、生成主题、测验答案和页面检查点
- 课程资料上传入库：支持 Markdown/TXT/PDF/PPTX 上传、解析、切分、向量化和 Wiki 检索
- 多课程模板：后端自动发现 `backend/knowledge/*/metadata.json` 课程目录，Wiki 检索、章节树、资料上传和学习路径生成支持按 `course_id` 隔离；当前内置《人工智能导论》和《Python 程序设计基础》两门课程
- 练习题结构化输出 + 前端训练模式（题型、题量、难度、限时、章节混合、成绩报告）
- 错题本与间隔复习：答错客观题自动进入复习队列，仪表盘展示待复习数量
- Study Mode 辅导模式：Tutor 支持分步提示、理解检查和错误归因，避免直接给最终答案
- 教师/助教分析视图：汇总学生进度、班级薄弱点、测验表现、待复习错题和教学建议
- 前端能力：会话搜索、快捷键（新建/聚焦输入）、流式中断（Esc）、最后一条助手消息“重新生成”
- 学生画像接口与画像驱动的对话编排能力
- Wiki 检索、知识树、关联知识、前置知识查询与内容回写接口
- 可信引用：资源卡展示来源覆盖率、相关度、来源片段和低置信度提示，可跳转 Wiki 搜索来源
- 资源局部重生成：可只重生成单张资源卡，不必重跑整轮资源包
- 本地资产存储：导出的 Markdown/PPTX 可生成持久访问 URL，后续可替换为 MinIO/S3 适配器
- 讯飞能力：星火 LLM 真实调用 / 开发模式回退、安全护栏内容审核（未启用时使用本地规则）、TTS 资源朗读（未启用时朗读接口返回不可用）
- 多模态展示：Mermaid 思维导图、PPTX 导出、前端动画分镜播放器、动画导出包与资源 TTS 朗读；当前导出的是 HTML 播放页 + 字幕 + 可选旁白音频，不生成完整 MP4/WebM 视频文件
- 前端聊天页、学习画像页、资源中心、知识 Wiki、学习路径页等核心页面框架；Wiki 和学习路径页支持课程切换
- 教师视图页：用于观察多用户学习情况和助教干预重点
- 以《人工智能导论》为核心、以《Python 程序设计基础》为样例扩展的课程知识库初始化能力

### 规划中 / 持续完善中

- 完整 MP4/WebM 视频文件导出、OCR 图片资料导入与 MinIO/S3 生产级对象存储适配
- 更细粒度的学习路径动态调整与效果评估
- 更丰富的资源展示样式与资源间联动
- 更完善的内容审核、缓存策略与生产级部署能力
- 更细的评测样例覆盖和 CI 质量门禁

---

## 系统架构概览

EduAgent 的核心设计可以概括为：**多 Agent 编排 + LLM Wiki 知识中枢 + 个性化学生画像**。

```text
学生输入
   ↓
Router Agent（意图识别）
   ↓
Planner Agent（任务分解与编排）
   ↓
Profile / Doc / Quiz / Code / Media / Tutor 等专业 Agent 协同
   ↓
LLM Wiki（知识图谱 + RAG 检索 + 内容回写）
   ↓
个性化学习资源 / 学习路径 / 智能辅导结果
```

### Agent 角色划分

- **Router Agent**：识别用户意图并路由到最合适的处理流程
- **Planner Agent**：处理复合任务，进行多 Agent 编排
- **Profile Agent**：构建与更新学生画像
- **Doc Agent**：生成个性化讲义、思维导图、拓展材料
- **Quiz Agent**：生成练习题、解析与针对性训练内容
- **Code Agent**：生成可运行的代码实操案例
- **Media Agent**：面向 PPT、思维导图、动画分镜与后续视频导出等多模态内容扩展
- **Tutor Agent**：进行即时答疑与苏格拉底式学习引导

---

## 学生画像设计

系统当前采用 **8 维动态学生画像**，满足赛题对画像维度的要求，并作为个性化生成的核心依据：

1. 知识基础
2. 认知风格
3. 学习目标
4. 易错点偏好
5. 学习节奏
6. 兴趣方向
7. 编程能力
8. 时间投入

画像会随着对话、答题情况、学习行为与任务反馈持续更新，用于调整：

- 内容讲解深度
- 题目难度与题型结构
- 资源组织方式
- 学习路径推进节奏
- 辅导方式与提示粒度

---

## 资源生成能力

EduAgent 面向高校学习过程，支持或规划支持以下资源类型：

- 课程讲解文档
- 知识点思维导图
- 个性化练习题
- 代码实操案例
- PPT 学习资料
- 教学动画分镜（前端播放器 + ZIP 动画导出包：HTML 播放页、字幕、可选 TTS 旁白；完整 MP4/WebM 视频文件导出仍属增强项）
- 拓展阅读材料

相比单一答案输出，EduAgent 更关注“**围绕同一学习目标组织一组资源**”，以满足不同学生对内容深度、形式与节奏的差异化需求。

---

## LLM Wiki：知识中枢

LLM Wiki 不是普通文档库，而是所有 Agent 的共享知识底座，包含三层能力：

1. **知识图谱**：组织章节、知识点、概念及其依赖关系
2. **RAG 检索**：在生成前检索相关知识、前置知识与关联主题
3. **内容管理**：支持用户上传课程资料与 Agent 生成内容回写，形成可复用知识资产
4. **可信引用**：生成资源时保留来源片段、相关度和覆盖率，前端以引用面板展示

当前后端已提供的 Wiki 相关接口包括：

- `/api/wiki/courses`：列出可切换课程模板
- `/api/wiki/chapters?course_id=...`：按课程列出章节
- `/api/wiki/search`：语义检索知识库
- `/api/wiki/upload`：上传课程资料并写入指定课程的检索库
- `/api/wiki/tree/{chapter_id}`：获取章节知识树，支持 `course_id` 过滤
- `/api/wiki/prerequisites/{topic}`：获取前置知识
- `/api/wiki/related/{topic}`：获取关联知识
- `/api/wiki/write-back`：回写 Agent 生成内容

---

## 页面展示

以下页面用于展示 EduAgent 从对话交互到知识组织、画像更新与路径规划的完整学习体验。

### 1. 对话学习页

- 展示流式对话输出
- 展示学习讲义、练习题、代码案例等资源卡片
- 支持基于会话持续更新学习上下文

> 截图占位：`docs/images/chat-page.png`

### 2. 学习画像页

- 展示学生画像维度与变化趋势
- 辅助说明系统如何实现“因材施教”

> 截图占位：`docs/images/profile-page.png`

### 3. 资源中心

- 展示系统生成的多类型学习资源
- 体现资源沉淀与复用能力

> 截图占位：`docs/images/resources-page.png`

### 4. 知识 Wiki 页

- 展示课程知识结构、知识树与知识点关联关系
- 支持在《人工智能导论》和《Python 程序设计基础》等课程之间切换，检索结果按课程隔离
- 体现系统的知识中枢设计

> 截图占位：`docs/images/wiki-page.png`

### 5. 学习路径页

- 展示个性化学习路径规划与阶段进度
- 创建路径时可选择课程模板，路径候选知识点来自当前课程图谱
- 体现系统不仅能回答问题，也能推进学习过程

> 截图占位：`docs/images/path-page.png`

### 6. 学习分析页

- 展示学习时长、测验均分、路径进度、错题复习队列和近期活动
- 新增 Agent 可观测面板，可查看最近对话的 Router/Profile/Planner/Doc/Quiz/Code/Media/Tutor 等节点耗时、状态、LLM 调用和错误信息

> 截图占位：`docs/images/analytics-page.png`

### 7. 教师分析页

- 汇总学生路径进度、测验表现、错题复习负担和班级薄弱知识点
- 输出面向助教备课和课后提醒的教学建议

> 截图占位：`docs/images/teacher-page.png`

---

## 技术栈

### 前端

- Next.js 15 / 16（App Router）
- React 19
- TypeScript
- Tailwind CSS
- shadcn/ui（设计方向）
- SSE 流式输出

### 后端

- Python 3.12
- FastAPI
- LangGraph（多 Agent 编排）
- SQLAlchemy
- PostgreSQL
- Redis
- MinIO
- Chroma / Milvus（向量检索）

### 模型与 AI 工具

- **讯飞星火**：主 LLM 能力提供方，贴合赛事要求
- **DeepSeek**：辅助模型能力
- Sentence Transformers：向量化检索相关能力

---

## 快速开始（开发环境）

### 3 分钟启动摘要

```bash
# 1) （可选但推荐）启动基础设施：PostgreSQL / Redis / MinIO
docker compose up -d

# 2) 后端：安装依赖 + 迁移 + 启动（Python 3.12）
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# 3) 前端：安装依赖 + 启动
cd ../frontend
pnpm install
pnpm dev
```

本 README 同时面向两类读者：

- **评委/路演**：快速理解系统价值，并看到可运行演示链路
- **开发者/队友**：快速完成本地启动，并定位常见开发问题

### 环境前置

- Python 3.12（后端强依赖）
- Node.js + pnpm（前端开发）
- uv（后端依赖与运行环境）
- Docker（可选但推荐，用于 PostgreSQL / Redis / MinIO）

### 1. 克隆项目

```bash
git clone <你的仓库地址>
cd EduAgent
```

### 2. 启动基础设施（可选，但推荐）

如果你打算使用 **PostgreSQL / Redis / MinIO**（更贴近比赛与部署形态），先启动基础设施：

```bash
docker compose up -d
```

如需停止：

```bash
docker compose down
```

> 不启动 Docker 也可以开发运行（默认会回落到本地 SQLite），但涉及部分能力与数据一致性时，建议使用 PostgreSQL。

### 3. 配置后端环境变量

在 `backend/.env` 中配置：

```env
# 数据库：二选一
# 1) 推荐：PostgreSQL（贴近比赛/部署）
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/eduagent

# 2) 可选：SQLite（零依赖快速跑通）
# DATABASE_URL=sqlite+aiosqlite:///./eduagent.db

REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# 本地资产存储（当前用于导出文件持久 URL；后续可替换为 MinIO/S3）
ASSET_STORAGE_DIR=./storage/assets
ASSET_PUBLIC_URL_PREFIX=/api/assets

# 讯飞星火
SPARK_APP_ID=xxx
SPARK_API_KEY=xxx
SPARK_API_SECRET=xxx
SPARK_API_PASSWORD=xxx
SPARK_MODEL=lite
SPARK_API_BASE_URL=https://spark-api-open.xf-yun.com/v1
SPARK_DEV_MODE=false

# 讯飞安全护栏（可选；未启用时仅使用本地规则）
XUNFEI_SAFETY_ENABLED=false
XUNFEI_SAFETY_APP_ID=xxx
XUNFEI_SAFETY_ACCESS_KEY_ID=xxx
XUNFEI_SAFETY_ACCESS_KEY_SECRET=xxx
XUNFEI_SAFETY_API_BASE_URL=http://audit-api-spark-dx.iflyaisol.com
XUNFEI_SAFETY_TEMPLATE_ID=

# 讯飞 TTS（可选；未单独配置时复用 SPARK_* 凭证）
XUNFEI_TTS_ENABLED=false
XUNFEI_TTS_APP_ID=xxx
XUNFEI_TTS_API_KEY=xxx
XUNFEI_TTS_API_SECRET=xxx
XUNFEI_TTS_URL=wss://tts-api.xfyun.cn/v2/tts
XUNFEI_TTS_VOICE=xiaoyan

# DeepSeek（备用）
DEEPSEEK_ENABLED=false
DEEPSEEK_API_KEY=xxx

# JWT
JWT_SECRET_KEY=xxx
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

前端开发环境建议在 `frontend/.env.local` 中配置：

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

说明：

- 后端默认开发数据库为 `sqlite+aiosqlite:///./eduagent.db`，如未配置 `DATABASE_URL` 会回落到 SQLite
- 前端默认请求 `http://localhost:8000`，如需改地址，请在 `frontend/.env.local` 中设置 `NEXT_PUBLIC_API_URL`
- 默认允许的前端开发来源包含 `http://localhost:3000` 与 `http://127.0.0.1:3000`
- `/health` 会返回 `llm_warning`、`safety_warning`、`tts_warning`。星火未配置且未启用 `SPARK_DEV_MODE=true` / `DEEPSEEK_ENABLED=true` 时，真实聊天会失败；安全护栏未启用时回退本地规则；TTS 未启用时资源朗读接口返回不可用。

### 4. 安装后端依赖并执行数据库迁移（必须）

后端要求 **Python 3.12**，并建议使用 `uv` 管理依赖与运行环境。

```bash
cd backend
uv sync
uv run alembic upgrade head
```

首次启动或拉取到新的数据库结构变更后，都应先执行迁移。

### 5. 启动后端

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

### 6. 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

默认情况下：

- 前端运行在 `http://localhost:3000`
- 后端运行在 `http://localhost:8000`

---

## 常用开发命令

### 后端

```bash
cd backend

uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# 测试
uv run pytest
uv run pytest -x -v
uv run pytest tests/evals -q

# 代码质量
uv run ruff check .
uv run ruff format .
```

### 前端

```bash
cd frontend

pnpm install
pnpm dev

# 构建与质量
pnpm build
pnpm lint
pnpm type-check

# 测试
pnpm test
```

## 常见问题排查

### 1) 登录后又跳回登录页 / 页面一直在“正在准备学习环境...”

最常见原因不是登录接口失败，而是登录后首页会请求会话列表：`GET /api/chat/sessions`。

最短定位路径：

1. 浏览器 DevTools → Network，确认 `GET /api/chat/sessions` 的状态码（通常会看到 500）
2. 查看后端日志堆栈（一般会指向数据库字段不存在/迁移缺失）
3. 在后端执行迁移并重启

常见根因是本地数据库没有执行最新迁移，导致缺少字段（例如 `chat_sessions.is_pinned` / `chat_sessions.pinned_at`），从而触发 500。

处理方式：

```bash
cd backend
uv run alembic upgrade head
```

### 2) 浏览器提示 CORS（No 'Access-Control-Allow-Origin' header）

优先检查两件事：

1. 前端打开地址是否为 `http://localhost:3000` 或 `http://127.0.0.1:3000`
2. 后端是否正确启动，并且 `backend_cors_origins` 已包含对应来源

说明：

- 当后端发生 500 等异常时，你可能会同时看到 CORS 报错，这通常是“后端异常”的表象
- 建议先在后端日志中确认真实错误堆栈

### 3) 后端启动失败（ImportError: cannot import name 'UTC' from 'datetime'）

后端要求 Python 3.12。请确保使用项目方式启动：

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

```text
EduAgent/
├─ backend/                 # FastAPI 后端与多 Agent 编排核心
│  ├─ app/
│  │  ├─ api/               # API 路由（chat / auth / wiki / resources）
│  │  ├─ agents/            # Router、Planner、Doc、Quiz、Code、Tutor、Media 等 Agent
│  │  ├─ core/              # 配置、数据库、认证、LLM 客户端
│  │  ├─ models/            # SQLAlchemy 数据模型
│  │  ├─ schemas/           # Pydantic 数据结构
│  │  ├─ services/          # 业务服务层
│  │  └─ wiki/              # Wiki、RAG、图谱、向量存储
│  └─ tests/                # 后端测试
├─ frontend/                # Next.js 前端应用
├─ docs/                    # 设计稿、计划、规格与后续补充文档
├─ PLAN.md                  # 系统完整架构设计
├─ DESIGN.md                # 前端视觉与交互设计规范
└─ 项目要求.md               # 比赛原始需求说明
```

---

## 当前完成度说明

从当前仓库状态看，EduAgent 已完成从“系统骨架”到“核心演示链路”的关键搭建：

- 已具备前后端分离的基础应用结构
- 已具备用户认证、聊天会话、流式输出与 Wiki 相关接口
- 已具备多 Agent 基础编排与画像驱动能力
- 已具备多课程模板、课程资料导入、可信引用、训练测验、错题复习、资源局部重生成、本地资产导出、Agent 可观测链路、自动评测基线和稳定演示脚本
- 已具备前端主页面框架，可用于展示核心学习流程

与此同时，完整 MP4/WebM 视频文件导出、OCR 图片资料导入、MinIO/S3 生产级对象存储适配、评测体系与演示物料仍在持续完善中。因此 README 明确区分“已实现”和“规划中”，避免将系统描述为一个已经完全封闭完成的产品。

---

## 防幻觉与内容安全设计

为满足赛题要求并提升学习内容可信度，EduAgent 在设计上强调生成质量与安全边界：

- **RAG 检索优先**：学术内容生成优先基于课程知识库召回
- **可信来源面板**：资源卡展示来源覆盖率、相关度、低置信提示和可核对片段
- **知识图谱约束**：通过章节、知识点和依赖关系组织知识
- **前置知识追踪**：在生成内容时考虑学生是否具备必要先修知识
- **内容回写与复用**：优质内容可回写知识库，提升一致性与积累能力
- **流式状态反馈**：让用户感知系统当前处理阶段，降低黑盒感
- **内容过滤设计**：可启用讯飞安全护栏进行输入/输出审核；未启用或凭证缺失时保留本地规则回退

---

## 与赛题要求的对应关系

| 赛题要求 | EduAgent 方案 |
|---|---|
| 画像维度 ≥ 6 | 设计 8 维动态学生画像 |
| 至少 5 类个性化资源 | 支持文档、导图、题目、代码、PPT、动画分镜、拓展阅读等 7 类 |
| 必须体现多智能体 | 采用 Router + Planner + 多专业 Agent 协同架构 |
| 使用讯飞相关工具 | 星火 LLM 为主；安全护栏和 TTS 可按凭证启用 |
| 防幻觉与内容安全 | 采用 LLM Wiki + RAG + 知识图谱 + 讯飞安全护栏/本地规则 |
| 流式输出 | 聊天核心接口基于 SSE 输出 |
| 初始知识库 | 以《人工智能导论》为切入，自建课程知识库，并提供 Python 基础样例课程验证多课程模板 |
| 开源协议声明 | 已在 `OPEN_SOURCE_LICENSES.md` 标注主要第三方依赖与协议 |

---

## 后续规划

- 增加完整 MP4/WebM 视频文件导出、OCR 图片资料导入和 MinIO/S3 对象存储适配
- 增强资源之间的联动关系与展示体验
- 强化学习路径动态调整与学习效果评估
- 扩充自动评测样例并接入 CI 质量门禁
- 补充演示截图、答辩材料与更完整的比赛展示材料
- 强化内容审核、缓存、监控与部署能力
- 补充第三方依赖与许可证说明

---

## 开源与第三方说明

根据赛题要求，若项目中使用开源框架、模型或工具，应在提交材料中显著标注名称、来源与协议。当前项目涉及但不限于以下技术生态：

- FastAPI
- Next.js
- React
- TypeScript
- Tailwind CSS
- SQLAlchemy
- PostgreSQL
- Redis
- MinIO
- LangGraph
- Sentence Transformers

当前仓库已提供 `OPEN_SOURCE_LICENSES.md` 作为第三方依赖与许可证清单；正式提交前仍应按最终依赖版本做一次核对。

---

## 参考文档

- `PLAN.md`：完整架构设计与模块拆解
- `DESIGN.md`：前端视觉与交互设计规范
- `docs/demo-script.md`：10 分钟稳定演示脚本和现场异常处理口径
- `docs/evaluation.md`：自动评测基线、运行命令和扩展规则
- `项目要求.md`：比赛原始需求说明

---

## 项目愿景

EduAgent 希望把“资源搜索”和“单轮问答”升级为“面向学习全过程的智能协作”，让系统不只是生成内容，而是能够真正理解学生、组织知识、规划路径，并提供连续的学习支持。
