# EduAgent Demo - Design Spec

> Human-readable design narrative. Machine-readable execution contract: `spec_lock.md`.

## I. Project Information

| Item | Value |
| ---- | ----- |
| **Project Name** | EduAgent 演示 PPT |
| **Canvas Format** | PPT 16:9 (1280x720) |
| **Page Count** | 14 |
| **Design Style** | C) Top Consulting + warm tech education |
| **Target Audience** | 高校智能体应用赛事评委、答辩专家、技术评审 |
| **Use Case** | 8-10 分钟项目路演与技术答辩 |
| **Created Date** | 2026-06-12 |

## II. Canvas Specification

| Property | Value |
| -------- | ----- |
| **Format** | PPT 16:9 |
| **Dimensions** | 1280 x 720 px |
| **viewBox** | `0 0 1280 720` |
| **Margins** | left/right 56px, top/bottom 44px |
| **Content Area** | 1168 x 632 px |

## III. Visual Theme

### Theme Style

- **Style**: Top Consulting + warm tech education
- **Theme**: warm light theme with selective charcoal emphasis pages
- **Tone**: clear, trustworthy, education-focused, technically credible

### Color Scheme

| Role | HEX | Purpose |
| ---- | --- | ------- |
| **Background** | `#f5f4ed` | warm parchment canvas |
| **Secondary bg** | `#faf9f5` | card and panel surface |
| **Primary** | `#c96442` | EduAgent terracotta accent |
| **Accent** | `#1565C0` | AI and engineering signal |
| **Secondary accent** | `#6b8e6b` | education, progress, mastery |
| **Body text** | `#141413` | primary text |
| **Secondary text** | `#5e5d59` | body support text |
| **Tertiary text** | `#87867f` | captions and footers |
| **Border/divider** | `#e8e6dc` | warm structural lines |
| **Light border** | `#f0eee6` | subtle panel edges |
| **Dark surface** | `#30302e` | contrast bands and summary blocks |
| **White** | `#ffffff` | high-contrast inner fields |
| **Warning** | `#c4a35a` | caution and review queue |
| **PPT resource** | `#b07d62` | PPT and media resource chip |

### AI Image Strategy

- **Image Rendering**: vector-illustration
- **Image Palette**: warm-earth

### Gradient Scheme

Use SVG gradients only for subtle section depth. No `rgba()`. Use `stop-opacity`.

## IV. Typography System

### Font Plan

**Typography direction**: strong Chinese sans hierarchy with compact technical annotations.

| Role | Chinese | English | Fallback tail |
| ---- | ------- | ------- | ------------- |
| **Title** | SimHei, Microsoft YaHei | Arial | sans-serif |
| **Body** | Microsoft YaHei, PingFang SC | Arial | sans-serif |
| **Emphasis** | SimHei, Microsoft YaHei | Arial | sans-serif |
| **Code** | - | Consolas, Courier New | monospace |

**Per-role font stacks**

- Title: `SimHei, "Microsoft YaHei", Arial, sans-serif`
- Body: `"Microsoft YaHei", "PingFang SC", Arial, sans-serif`
- Emphasis: `SimHei, "Microsoft YaHei", Arial, sans-serif`
- Code: `Consolas, "Courier New", monospace`

### Font Size Hierarchy

**Baseline**: Body font size = 18px.

| Purpose | Size |
| ------- | ---- |
| Cover title | 70px |
| Section / hero number | 52px |
| Page title | 34px |
| Subtitle | 24px |
| Body | 18px |
| Annotation | 14px |
| Page number / footnote | 11px |

Formula policy: text-only. This deck contains light technical concepts but no formula-heavy teaching derivations.

## V. Layout Principles

### Page Structure

- **Header area**: 44-116px; includes page title, page number, and optional section tag.
- **Content area**: 500-560px; uses conclusion-first titles and one primary visual structure per slide.
- **Footer area**: 28-36px; includes source cue or one-line takeaway.

### Layout Pattern Library

Use a mix of conclusion-first consulting pages, radial systems, flow diagrams, vertical pillars, comparison rows, and negative-space hero pages. Avoid making every slide a card grid.

### Spacing Specification

| Element | Current Project |
| ------- | --------------- |
| Safe margin from canvas edge | 56px |
| Content block gap | 24-36px |
| Icon-text gap | 10-14px |
| Card gap | 18-28px |
| Card padding | 18-28px |
| Card border radius | 8px |

## VI. Icon Usage Specification

### Source

- **Built-in icon library**: `chunk-filled`
- **Usage method**: SVG placeholder or native SVG shape. The final deck mostly uses native shapes for maximum PPT editability.

### Recommended Icon List

| Purpose | Icon Path | Page |
| ------- | --------- | ---- |
| Value / goal | `chunk-filled/target` | P03, P14 |
| AI capability | `chunk-filled/bolt` | P05 |
| Safety | `chunk-filled/shield-check` | P11 |
| Users / observability | `chunk-filled/users` | P10, P13 |
| Analytics | `chunk-filled/chart-bar` | P12 |
| Wiki | `chunk-filled/book-open` | P07 |
| Code | `chunk-filled/code` | P09 |
| Data layer | `chunk-filled/database` | P04 |
| Route | `chunk-filled/route` | P10 |
| Agent | `chunk-filled/robot` | P06 |

## VII. Visualization Reference List

Catalog read: 71 templates

| Page | Template | Path | Summary-quote (verbatim from `charts_index.json`) | Usage |
| ---- | -------- | ---- | ------------------------------------------------- | ----- |
| P04 | layered_architecture | `templates/charts/layered_architecture.svg` | "Pick for 3-4 horizontal architecture layers (presentation/service/data), 2-4 module cards per layer, each card = title + 1-line description (description required, even if source brief). Skip if no per-module descriptions (use icon_grid) or no horizontal layering (use module_composition)." | System architecture overview |
| P06 | hub_spoke | `templates/charts/hub_spoke.svg` | "Pick for 1 core capability + 4-8 surrounding capabilities (platform/ecosystem); each spoke = title or title + 1-2 line description. Skip if center is a system containing parts with their own descriptions (use module_composition), or surroundings exert inward pressure on the center (use hub_inward_arrows)." | Multi-agent collaboration model |
| P08 | radar_chart | `templates/charts/radar_chart.svg` | "Pick for 4-8 capability dimensions scored across 1-3 entities. Skip for >3 entities (becomes unreadable; use grouped_bar_chart) or <4 dimensions." | 8-dimensional learner profile |
| P10 | circular_stages | `templates/charts/circular_stages.svg` | "Pick for 4-6 stage closed loop where stages compose a cycle — PDCA, flywheel compounding loops (Attract → Engage → Delight), lifecycle, continuous improvement. Skip for linear flow (use process_flow), one-shot sequence (use numbered_steps), or wedge-based central topic (use segmented_wheel)." | Learning closed loop |
| P12 | kpi_cards | `templates/charts/kpi_cards.svg` | "Pick for 4-8 standalone numeric metrics shown as overview cards (2x2 or 1x4) — exec summary opener, dashboard headline, quarterly recap, results-at-a-glance. Skip if metrics have target baselines (use bullet_chart) or single hero number (use gauge_chart)." | Engineering implementation highlights |

**Runners-up considered**

- `module_composition` | rejected for P04: the architecture is layered across UI, API, agent, knowledge, and data, not a single parent module.
- `mind_map` | rejected for P06: Agent relation is a controlled orchestration hub, not a brainstorm map.
- `process_flow` | rejected for P10: the learning journey loops back through assessment and path update.

## VIII. Image Resource List

| Filename | Dimensions | Ratio | Purpose | Type | Layout pattern | Acquire Via | Status | Reference | text_policy | page_role |
| -------- | ---------- | ----- | ------- | ---- | -------------- | ----------- | ------ | --------- | ----------- | --------- |
| cover_bg.png | 1280x720 | 16:9 | Atmospheric cover backdrop with calm center for SVG title | Background | #1 Full-bleed background with floating title + #29 Two-stop scrim — opaque on text side, transparent on focal side | ai | Generated | Warm educational AI learning hub, abstract knowledge graph and student journey, calm center | none | hero_page |
| architecture_bg.png | 1280x720 | 16:9 | System architecture atmosphere behind native layered diagram | Diagram | #44 Background image + native network/architecture diagram + #65 Image with NO text — labels added as native SVG | ai | Generated | Abstract multi-layer software architecture, UI, API, agents, wiki, data stores as clean symbolic zones | none | local |
| agents_hub.png | 900x560 | 1.61 | Multi-agent hub illustration supporting P06 native labels | Diagram | #44 Background image + native network/architecture diagram + #65 Image with NO text — labels added as native SVG | ai | Generated | Central agent orchestrator with surrounding specialist agents, all text left to SVG | none | local |
| wiki_graph.png | 900x520 | 1.73 | Knowledge graph and RAG retrieval atmosphere | Diagram | #45 Background image + numbered hotspots with sidebar legend + #65 Image with NO text — labels added as native SVG | ai | Generated | Course knowledge nodes, vector retrieval paths, citations and source fragments represented visually | none | local |
| learning_loop.png | 1000x560 | 1.79 | Closed-loop learning journey visual for P10 | Diagram | #39 Background image + flow nodes drawn over the scene + #65 Image with NO text — labels added as native SVG | ai | Generated | Student profile to resources to quiz feedback to path update to agent observability as a continuous loop | none | local |
| multimodal_resources.png | 1000x560 | 1.79 | Resource gallery atmosphere for P09 | Illustration | #47 Small multiples — 3-6 same-kind images in an evenly spaced row + #65 Image with NO text — labels added as native SVG | ai | Generated | Six educational resource tiles represented as visual objects: document, quiz, code, mindmap, PPT, animation | none | local |

Image2 assets were generated through the Codex built-in image2 path and saved under `images/`; exact slide text remains native SVG for editability.

## IX. Content Outline

### Part 1: Project Value

#### Slide 01 - Cover
- **Layout**: Full-bleed warm abstract background, large conclusion title, three proof tags.
- **Title**: EduAgent 个性化多 Agent 学习系统
- **Core message**: EduAgent 把单轮 AI 问答升级为面向学习全过程的智能学习中枢。
- **Content**: LLM Wiki / 多 Agent 协同 / 8 维学生画像 / 多模态资源闭环。

#### Slide 02 - 教育痛点
- **Layout**: Left problem statement, right three pain cards.
- **Title**: 高等教育的关键矛盾不是缺资源，而是缺匹配
- **Core message**: 海量资源与学生差异之间缺少可持续、可解释、可个性化的组织机制。
- **Content**: 资源繁杂难筛选；标准课堂难适配节奏；通用问答不理解学生；缺少资源到评估的闭环。

#### Slide 03 - 一句话价值
- **Layout**: Four-step horizontal value chain.
- **Title**: 先理解学生，再组织知识，再生成资源，再陪伴学习
- **Core message**: 系统价值来自从画像到知识到资源到反馈的连续协作，而不是一次回答。
- **Content**: 理解学生 / 组织知识 / 生成资源 / 陪伴学习。

### Part 2: Technology Fusion

#### Slide 04 - 系统全景
- **Layout**: Layered architecture.
- **Title**: 系统以 LLM Wiki 为中枢，用 LangGraph 编排学习任务
- **Core message**: EduAgent 的架构把前端体验、Agent 编排、知识检索和数据沉淀连接成一条工程链路。
- **Visualization**: layered_architecture
- **Content**: Frontend / FastAPI / LangGraph Orchestrator / LLM Wiki / DB and storage.

#### Slide 05 - 前沿 AI 融合
- **Layout**: Six capability tiles around a central claim.
- **Title**: 前沿 AI 能力被拆成可控组件，而不是堆在一个大模型调用里
- **Core message**: 讯飞星火、RAG、知识图谱、TTS、安全护栏和 image2 多模态共同服务教学闭环。
- **Content**: Spark LLM, RAG, knowledge graph, multi-agent, safety and TTS, image2.

#### Slide 06 - 多 Agent 协同
- **Layout**: Hub-spoke Agent map.
- **Title**: 多 Agent 不是概念展示，而是一次请求中的真实分工
- **Core message**: Router 识别意图，Planner 拆解任务，专业 Agent 并行产出资源并持续记录状态。
- **Visualization**: hub_spoke
- **Content**: Router / Profile / Planner / Doc / Quiz / Code / Media / Video / Tutor.

#### Slide 07 - LLM Wiki 知识中枢
- **Layout**: Knowledge graph left, three trust mechanisms right.
- **Title**: LLM Wiki 让生成内容有边界、有来源、可沉淀
- **Core message**: 所有 Agent 共享课程图谱、RAG 检索和内容回写机制，降低幻觉并积累知识资产。
- **Content**: 课程隔离 / 向量检索 / 来源片段 / 内容回写。

#### Slide 08 - 8 维学习画像
- **Layout**: Radar-like profile diagram plus personalization rules.
- **Title**: 学生画像从对话中生成，并驱动后续每一次资源编排
- **Core message**: 8 维画像把个体差异转成可执行的内容深度、题目难度和路径节奏。
- **Visualization**: radar_chart
- **Content**: 知识基础、认知风格、学习目标、易错点、学习节奏、兴趣、编程能力、时间投入。

### Part 3: Function and Implementation

#### Slide 09 - 多模态资源生成
- **Layout**: Resource gallery with eight resource chips.
- **Title**: 同一学习目标可以生成一组互补资源，而不是一段孤立文本
- **Core message**: EduAgent 支持至少 8 类资源，覆盖理解、练习、实践、展示和拓展。
- **Content**: 讲义 / 导图 / 题目 / 代码 / PPT / 动画 / 拓展阅读 / B站视频。

#### Slide 10 - 学习闭环演示
- **Layout**: Circular learning loop.
- **Title**: 演示链路覆盖学生学习闭环，过程完整可复现
- **Core message**: 学习结果会反哺错题、路径、仪表盘和画像确认，而不是停留在聊天窗口。
- **Visualization**: circular_stages
- **Content**: 画像 / 资源 / 测验 / 错题 / 路径 / 评估 / 可观测。

#### Slide 11 - 可信与安全
- **Layout**: Three defense layers with evidence panel.
- **Title**: 可信输出来自检索约束、引用核验和安全过滤的组合防线
- **Core message**: 系统在生成前、中、后分别约束事实、展示来源并过滤风险内容。
- **Content**: RAG 优先 / 可信来源 / 低置信提示 / 讯飞安全 / 自动评测。

#### Slide 12 - 工程实现亮点
- **Layout**: KPI cards plus implementation notes.
- **Title**: 工程实现围绕可运行、可观测、可回退来设计
- **Core message**: 流式体验、并行生成、资源导出和 Agent 可观测让系统具备演示稳定性。
- **Visualization**: kpi_cards
- **Content**: SSE / 并行资源 / 可观测事件 / 局部重生成 / PPTX 与动画导出。

### Part 4: Innovation and Close

#### Slide 13 - 创新价值
- **Layout**: Before/after transformation.
- **Title**: 创新点不是多一个聊天窗口，而是重构学习资源的生产方式
- **Core message**: EduAgent 将知识、画像、Agent 和评估组合为可持续演化的学习操作系统。
- **Content**: 学生侧个性化；学习侧洞察；知识侧沉淀；工程侧可扩展。

#### Slide 14 - 总结
- **Layout**: Requirement coverage matrix and closing statement.
- **Title**: EduAgent 已覆盖核心要求，并保留清晰的增强路径
- **Core message**: 当前系统可完整展示比赛核心链路，后续可增强视频导出、OCR 和生产级存储。
- **Content**: 核心需求覆盖 / 已实现能力 / 后续增强。

## X. Speaker Notes Requirements

- **Total duration**: 8-10 minutes.
- **Style**: formal but conversational; conclusion first.
- **Filename**: `notes/total.md`, split into per-slide files by `total_md_split.py`.
- **Purpose**: persuade judges that the system is both valuable and actually implemented.

## XI. Technical Constraints Reminder

### SVG Generation Must Follow

1. viewBox: `0 0 1280 720`
2. Background uses `<rect>` elements.
3. Text wrapping uses `<tspan>`; `<foreignObject>` forbidden.
4. Transparency uses `fill-opacity` or `stroke-opacity`; `rgba()` forbidden.
5. Forbidden: `<style>`, `class`, `<foreignObject>`, `textPath`, animation, script, mask.
6. PPT compatibility: no group opacity; use child opacity values.
