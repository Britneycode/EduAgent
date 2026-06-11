# EduAgent Optimization Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 EduAgent 从“满足赛题核心要求的演示系统”升级为更接近竞品重度用户可长期使用的个性化学习产品。

**Architecture:** 计划分为交付修复、资料导入与可信生成、学习闭环增强、产品化与运营能力四个迭代。优先补齐提交风险，再围绕“资料进入系统 -> 生成可信资源 -> 练习评估 -> 路径调整 -> 复习留存”形成可持续学习闭环。

**Tech Stack:** FastAPI, SQLAlchemy, LangGraph, RAG/Wiki, Xunfei Spark/Safety/TTS, Next.js, React, TypeScript, Tailwind CSS, Recharts, Mermaid, Vitest, Pytest.

---

## 总体排期表

| 阶段 | 优先级 | 时间建议 | 核心目标 | 完成标志 |
|---|---|---:|---|---|
| 迭代 0：提交风险修复 | P0 | 0.5-1 天 | 确保当前项目能干净通过质量检查，提交材料描述准确 | lint/build/test 全通过，README 与协议声明不夸大实现边界 |
| 迭代 1：竞品迁移关键能力 | P1 | 5-8 天 | 补齐资料导入、备考训练、Study Mode、可信引用和多模态资产 | 用户能上传课程资料并生成可追溯资源，能完成测验-错题-复习闭环 |
| 迭代 2：长期留存能力 | P2 | 4-6 天 | 强化教师视角、课程模板、Agent 可观测和评测体系 | 系统具备多课程扩展、运营观察和自动质量评估能力 |
| 迭代 3：交付与演示打磨 | P0/P1 | 1-2 天 | 固化演示路线、样例数据、部署说明和答辩材料 | 一条稳定演示链路可从注册跑到评估仪表盘 |

## 优化项计划表

| ID | 优先级 | 优化项 | 用户价值 | 关键改动 | 主要文件/模块 | 验收标准 | 测试方式 | 依赖 |
|---|---|---|---|---|---|---|---|---|
| O-01 | P0 | 修复前端 ESLint 失败 | 降低交付风险，保证质量检查闭环 | 调整画像历史面板 `useEffect` 内同步 `setLoading(true)` 的写法，避免触发 `react-hooks/set-state-in-effect` | `frontend/src/app/(main)/profile/page.tsx` | `pnpm lint` 无错误 | `pnpm lint`; `pnpm type-check`; `pnpm test` | 无 |
| O-02 | P0 | 补全开源协议声明 | 满足赛题“开源项目需显著标注名称、来源及协议”要求 | 在协议清单中补齐新增依赖和实际使用工具 | `OPEN_SOURCE_LICENSES.md`; `backend/pyproject.toml`; `frontend/package.json` | 清单覆盖 LangGraph、Redis、websockets、Mermaid、Vitest、Testing Library、Chroma client 等当前依赖 | 人工核对依赖文件；链接抽查 | 无 |
| O-03 | P0 | 明确讯飞工具启用说明 | 避免评委认为讯飞安全/TTS 只是代码占位 | 在 README 和 `.env.example` 中补充星火、安全护栏、TTS 的配置、启用条件和降级行为 | `README.md`; `backend/.env.example`; `backend/app/core/config.py` | 文档能解释 LLM、安全审核、TTS 是否启用，以及未启用时的回退行为 | 人工按 README 配置本地启动；访问 `/health` 查看 warning | 讯飞账号与接口权限 |
| O-04 | P0 | 校准多模态实现描述 | 防止“动画/视频”表述超过实际能力 | README 中明确当前 animation 是分镜播放器和 TTS 朗读，不是完整视频文件生成 | `README.md`; `GAP_ANALYSIS.md` | 文档对“已实现/规划中”边界准确，演示说法与源码一致 | 人工审阅 README 与路演稿 | 无 |
| O-05 | P1 | 课程资料上传入库 | 迁移 NotebookLM/Quizlet 用户的关键入口，让用户带自己的课件进入系统 | 新增文件上传、文档解析、切分、向量化、Wiki 写入、来源元数据 | `backend/app/api/wiki.py`; `backend/app/wiki/ingestion.py`; `backend/app/models/wiki.py`; `frontend/src/app/(main)/wiki/page.tsx` | 用户上传 Markdown/PDF/PPTX 后，可在 Wiki 搜索命中并被 Agent 作为来源引用 | 后端 API 测试；上传样例文件后搜索；生成讲义检查来源 | 文件解析库；对象存储可选 |
| O-06 | P1 | 图片/OCR 资料导入 | 覆盖课堂板书、截图、扫描笔记等高频学习资料 | 接入讯飞 OCR 或预留 OCR 适配器，OCR 文本进入 ingestion 管道 | `backend/app/core/xunfei_ocr.py`; `backend/app/wiki/ingestion.py`; `backend/app/api/wiki.py` | 上传图片后生成可检索文本，来源标记为 OCR | 单元测试 mock OCR；真实图片手测 | 讯飞 OCR 权限 |
| O-07 | P1 | 错题本与间隔复习 | 从“做一次题”升级为“持续备考” | 保存错题、知识点、错误答案、复习状态；生成每日复习队列 | `backend/app/models/learning.py`; `backend/app/services/learning_path_service.py`; `backend/app/api/learning.py`; `frontend/src/app/(main)/analytics/page.tsx` | 答错题自动进入错题本；复习后可标记掌握；仪表盘显示待复习数量 | Pytest API 测试；Vitest 复习队列组件测试 | Quiz 提交流程 |
| O-08 | P1 | 考试/训练模式 | 对齐 Quizlet 高频使用场景 | 支持题型筛选、题量、难度、限时、章节混合训练和成绩报告 | `backend/app/agents/quiz_agent.py`; `backend/app/schemas/learning.py`; `frontend/src/components/chat/InteractiveQuiz.tsx` | 用户能选择“10 题限时训练”，提交后看到得分、用时、薄弱点 | QuizAgent 测试；交互组件测试 | O-07 可并行 |
| O-09 | P1 | Study Mode 辅导模式 | 让 Tutor 更像教练，减少直接给答案 | 新增模式状态：诊断目标、分步提示、理解检查、错误归因、最终总结 | `backend/app/agents/tutor_agent.py`; `backend/app/agents/orchestrator.py`; `frontend/src/app/(main)/chat/[sessionId]/page.tsx` | 用户提问后系统先判断基础和目标，可逐步提示并检查理解 | TutorAgent prompt 测试；端到端手测 | 现有 TutorAgent |
| O-10 | P1 | 资源局部重生成 | 降低等待成本，提升可控性 | 支持对单个资源卡重生成：题目、代码、PPT、导图、阅读材料 | `backend/app/api/resources.py`; `backend/app/agents/orchestrator.py`; `frontend/src/components/chat/ResourceCard.tsx` | 点击“重生成题目”只调用 QuizAgent，不重跑整轮资源包 | API 测试；前端交互测试 | Agent 入参需可复用 |
| O-11 | P1 | 可信引用增强 | 增强防幻觉说服力，形成竞品差异 | 每段资源显示来源覆盖率、低置信度提示、可点击来源片段、报告错误入口 | `backend/app/wiki/rag_engine.py`; `backend/app/agents/content_guard.py`; `frontend/src/components/chat/ResourceCard.tsx`; `frontend/src/app/(main)/wiki/page.tsx` | 生成内容包含来源列表、相关度、置信提示；用户可跳转查看来源片段 | RAG 测试；手动生成低置信主题检查 UI | Wiki 来源元数据 |
| O-12 | P1 | 多模态资产库与对象存储 | 从“卡片展示”升级为可复用学习资产 | 接入 MinIO 或本地对象存储抽象，保存 PPTX、音频、导出文件和后续视频文件 | `backend/app/core/storage.py`; `backend/app/api/resources.py`; `backend/app/models/resource.py`; `docker-compose.yml` | PPTX/音频导出文件有持久 URL；资源中心可再次打开 | API 测试；本地 docker compose 手测 | MinIO 或本地存储策略 |
| O-13 | P1 | 视频/动画真实导出 | 提升多模态评分和演示冲击力 | 在现有分镜基础上导出字幕、音频和简单视频；优先使用 TTS + 图片序列/HTML capture | `backend/app/agents/media_agent.py`; `backend/app/core/xunfei_tts.py`; `backend/app/core/video_export.py`; `frontend/src/components/ui/AnimationPlayer.tsx` | 动画资源可导出 mp4 或 webm，至少包含字幕和旁白音频 | 单元测试脚本解析；手动播放导出文件 | O-12；FFmpeg 或浏览器导出方案 |
| O-14 | P2 | 教师/助教分析视图 | 从个人学习工具扩展到教学辅助平台 | 汇总多用户画像、薄弱点、测验表现和推荐讲解资源 | `backend/app/api/learning.py`; `backend/app/services/learning_path_service.py`; `frontend/src/app/(main)/teacher/page.tsx` | 教师可查看班级薄弱知识点 Top N 和学生进度分布 | API 聚合测试；前端图表测试 | 角色/权限模型可后置简化 |
| O-15 | P2 | 多课程模板 | 让系统摆脱单一《人工智能导论》课程限制 | 将知识库目录、元数据、图谱、课程选择抽象为 Course | `backend/app/wiki/__init__.py`; `backend/app/models/wiki.py`; `frontend/src/app/(main)/wiki/page.tsx`; `frontend/src/app/(main)/path/page.tsx` | 可切换至少两门课程；路径规划和检索按课程隔离 | Wiki 单元测试；手动切课生成资源 | 课程数据准备 |
| O-16 | P2 | Agent 可观测面板 | 让多智能体协同可解释、可优化 | 记录每个 Agent 的耗时、资源类型、错误、LLM 调用状态和 token 估算 | `backend/app/agents/orchestrator.py`; `backend/app/models/learning.py`; `frontend/src/app/(main)/analytics/page.tsx` | 一次对话后可看到 Router/Planner/Doc 等节点耗时和结果状态 | Orchestrator 测试；前端面板测试 | 日志表或事件表 |
| O-17 | P2 | 自动评测集 | 建立生成质量和防幻觉的工程基线 | 增加画像抽取、路由、RAG 命中、题目结构、内容安全的固定评测样例 | `backend/tests/evals/`; `backend/tests/test_agents/`; `docs/evaluation.md` | 每次改动可跑评测，输出通过率和失败样例 | `uv run pytest tests/evals -q` | 样例数据 |
| O-18 | P0/P1 | 稳定演示脚本与样例数据 | 确保路演时一条链路可重复成功 | 固化注册用户、画像输入、生成主题、测验提交、路径调整、仪表盘展示流程 | `README.md`; `docs/demo-script.md`; `backend/knowledge/ai_intro/` | 10 分钟内能稳定演示“画像 -> 资源 -> 测验 -> 路径 -> 评估” | 按脚本完整手测一次 | 前述 P0 修复 |

## 执行进度记录

> 文档维护约定：每完成一项优化，必须同步更新本节、`README.md` 和 `GAP_ANALYSIS.md`，并记录主要验证命令。

| 日期 | ID | 状态 | 完成摘要 | 验证 |
|---|---|---|---|---|
| 2026-05-01 | O-01 | ✅ 已完成 | 修复画像历史面板 hooks lint 问题 | `pnpm lint`; `pnpm type-check`; `pnpm test`; `pnpm build` |
| 2026-05-01 | O-02 | ✅ 已完成 | 补全直接依赖和新增工具的开源协议声明 | 人工核对依赖清单 |
| 2026-05-01 | O-03 | ✅ 已完成 | README 与 `.env.example` 明确星火、安全护栏、TTS 配置和回退行为 | `uv run pytest -q`; `/health` 文档核对 |
| 2026-05-01 | O-04 | ✅ 已完成 | 校准多模态说明，明确动画是分镜播放器 + TTS，不夸大为完整视频文件生成 | README/GAP 文档审阅 |
| 2026-05-01 | O-05 | ✅ 已完成 | 新增 Markdown/TXT/PDF/PPTX 课程资料上传、解析、切分、向量化和 Wiki 入库 | `uv run pytest tests/test_wiki.py tests/test_api/test_wiki_api.py -q`; `pnpm lint`; `pnpm type-check` |
| 2026-05-01 | O-07 | ✅ 已完成 | 答错客观题自动进入错题本，支持间隔复习队列和掌握状态 | `uv run pytest tests/test_api/test_learning_api.py -q`; `pnpm lint`; `pnpm type-check` |
| 2026-05-01 | O-09 | ✅ 已完成 | Tutor 新增 Study Mode，支持分步提示、理解检查和错误归因 | `uv run pytest tests/test_agents/test_tutor_agent.py tests/test_agents/test_orchestrator.py tests/test_api/test_chat_api.py -q`; `pnpm test` |
| 2026-05-01 | O-11 | ✅ 已完成 | 资源卡展示可信引用面板、来源覆盖率、低置信提示、来源片段和报告入口 | `uv run pytest tests/test_wiki.py tests/test_agents/test_content_guard.py tests/test_agents/test_orchestrator.py tests/test_agents/test_doc_agent.py -q`; `pnpm lint`; `pnpm type-check` |
| 2026-05-01 | O-08 | ✅ 已完成 | 练习卡升级为训练模式，支持题型、题量、难度、限时、章节混合和薄弱点报告 | `uv run pytest tests/test_agents/test_quiz_agent.py tests/test_api/test_learning_api.py -q`; `pnpm lint`; `pnpm type-check` |
| 2026-05-01 | O-10 | ✅ 已完成 | 单张资源卡支持局部重生成，只更新目标资源，不重跑整轮资源包 | `uv run pytest tests/test_api/test_resources_api.py -q`; `pnpm lint`; `pnpm type-check` |
| 2026-05-01 | O-12 | ✅ 已完成 | 新增本地资产存储抽象、资产访问路由和资源导出持久 URL | `uv run pytest tests/test_storage.py tests/test_api/test_resources_api.py -q`; `pnpm lint`; `pnpm type-check` |
| 2026-05-02 | O-13 | ✅ 阶段完成 | 动画资源可导出 ZIP 动画包，包含 HTML 播放页、WebVTT/SRT 字幕、原始脚本；启用 TTS 时附带旁白 MP3 | `uv run pytest tests/test_video_export.py tests/test_api/test_resources_api.py -q`; `pnpm lint`; `pnpm type-check` |
| 2026-05-02 | O-14 | ✅ 已完成 | 新增教师/助教分析 API 与前端页面，汇总学生进度、薄弱知识点、测验表现、待复习错题和教学建议 | `uv run pytest tests/test_api/test_learning_api.py -q`; `pnpm lint`; `pnpm type-check` |
| 2026-05-02 | O-15 | ✅ 已完成 | 新增课程模板发现、`course_id` 元数据和 Python 基础样例课程；Wiki 课程列表、章节树、检索、上传入库与学习路径生成均支持课程隔离 | `uv run pytest tests/test_wiki.py tests/test_api/test_wiki_api.py tests/test_services/test_learning_path_service.py tests/test_api/test_learning_api.py -q`; `pnpm lint`; `pnpm exec tsc --noEmit` |
| 2026-05-02 | O-16 | ✅ 已完成 | 新增 Agent 运行事件表、编排节点埋点、`/api/learning/agent-observability` 聚合接口和学习分析页 Agent 可观测面板，展示节点耗时、状态、资源类型、LLM 调用和 token 估算 | `uv run pytest tests/test_agents/test_orchestrator.py tests/test_api/test_learning_api.py tests/test_services/test_learning_path_service.py -q`; `pnpm lint`; `pnpm type-check`; `pnpm build` |
| 2026-05-02 | O-17 | ✅ 已完成 | 新增 `backend/tests/evals` 自动评测集和 `docs/evaluation.md`，用固定样例覆盖画像抽取、路由、RAG 命中、题目结构和内容安全，pytest 失败时直接暴露样例 ID 与偏差字段 | `uv run pytest tests/evals -q` |
| 2026-05-02 | O-18 | ✅ 已完成 | 新增 `docs/demo-script.md` 10 分钟稳定演示脚本和 `backend/knowledge/ai_intro/demo_scenario.json` 样例数据，固化注册账号、画像输入、资源生成、测验提交、路径、Wiki、仪表盘和教师视图检查点 | `uv run pytest tests/evals/test_demo_scenario.py -q` |
| 2026-05-02 | 回归验证 | ✅ 已完成 | 当前已完成项进行后端全量测试和前端生产构建 | `uv run pytest -q`（166 passed）；`pnpm type-check`; `pnpm lint`; `pnpm build` |

## 迭代 0：提交风险修复清单

| 步骤 | 任务 | 命令/验收 |
|---:|---|---|
| 1 | ✅ 修复 `frontend/src/app/(main)/profile/page.tsx` 的 lint 错误 | `pnpm lint` 通过 |
| 2 | ✅ 补全 `OPEN_SOURCE_LICENSES.md` | 依赖清单与 `pyproject.toml`、`package.json` 一致 |
| 3 | ✅ 更新 README 中讯飞工具与多模态边界说明 | README 不再把分镜播放器描述成完整视频生成 |
| 4 | ✅ 跑完整质量检查 | `uv run pytest -q`; `pnpm test`; `pnpm type-check`; `pnpm lint`; `pnpm build` 全通过 |

## 迭代 1：竞品迁移能力清单

| 步骤 | 任务 | 验收 |
|---:|---|---|
| 1 | ✅ 增加资料上传和入库管道 | 上传课程资料后能被 `/api/wiki/search` 命中 |
| 2 | ✅ 增加错题本和复习队列 | 答错题自动进入待复习列表 |
| 3 | ✅ 增加考试/训练模式 | 用户能配置题量、题型、限时并获得报告 |
| 4 | ✅ 增加 Study Mode | Tutor 支持分步提示、理解检查和错误归因 |
| 5 | ✅ 增强可信引用 | 资源卡展示来源、相关度和低置信提示 |
| 6 | ✅ 增加对象存储与资产管理 | 导出的 PPTX/Markdown 可生成持久 URL；音频资产接口已预留，需 TTS 凭证启用 |

## 迭代 2：长期留存能力清单

| 步骤 | 任务 | 验收 |
|---:|---|---|
| 1 | ✅ 增加教师/助教分析视图 | 可查看用户群体薄弱点和路径进度 |
| 2 | ✅ 增加多课程模板 | 至少支持第二门课程知识库切换 |
| 3 | ✅ 增加 Agent 可观测面板 | 每轮对话可看到 Agent 耗时和状态 |
| 4 | ✅ 增加自动评测集 | CI 或本地命令可输出质量基线 |

## 迭代 3：交付与演示打磨清单

| 步骤 | 任务 | 验收 |
|---:|---|---|
| 1 | ✅ 固化稳定演示脚本与样例数据 | 10 分钟内可按脚本从注册跑到评估仪表盘 |

## 推荐执行顺序

1. 先做 O-01 到 O-04，保证当前成果能提交、能构建、能解释清楚。
2. 再做 O-05、O-07、O-09、O-11，这四项最能影响竞品重度用户是否留下。
3. 然后做 O-08、O-10、O-12、O-13，增强“学习效率”和“资源资产”体验。
4. 最后做 O-14 到 O-17，形成平台化、可运营、可评测的长期壁垒。

## 风险与取舍

| 风险 | 影响 | 建议处理 |
|---|---|---|
| 资料上传解析范围过大 | 容易拖慢迭代 1 | 先支持 Markdown/PDF 文本，PPTX 和 OCR 分两步做 |
| 真视频生成耗时和环境依赖高 | 本地演示不稳定 | 先做 TTS + 分镜播放器 + 可下载字幕，视频导出作为增强项 |
| 内容安全依赖外部讯飞接口 | 凭证或权限不足会影响演示 | 保留本地规则 fallback，并在 `/health` 清楚展示状态 |
| 多课程抽象改动面较大 | 可能影响现有 Wiki | 先用 course_id 做轻量隔离，不重写现有 Wiki 架构 |
