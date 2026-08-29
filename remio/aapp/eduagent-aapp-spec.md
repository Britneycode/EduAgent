# 金漪湖 · 个性化学习智能体 — remio aApp 开发规格

> 作品名：**EduAgent 个性化学习智能体**（aApp / skill）
> 赛道：**智能体融合创新赛道**（2026 智能体 OPC 创新大会 · 金漪湖论剑）
> 平台：remio 睿妙（配合《remio 参赛规则》的"语义端点 → 对话为主 → UI 为辅"开发范式）

本规格把 EduAgent 现有的 **10 个协同 Agent** 引擎，重表达为 remio 可执行的
**语义端点 + 能力调用 + 对话编排 + UI 组件 + 订阅自动化**。逐节按 aapp-studio
的自然语言开发流程可落地，也可配合同目录 `eduagent-aapp-manifest.json` 机器可读清单使用。

---

## 0. 一句话定位

> 面向高校学生的**个性化多智能体学习助手**：先理解"你是谁、哪里薄弱、要学什么"，
> 再从结构化课程知识库（默认内置《计算机网络》全课程知识库）中检索**抗幻觉**的知识，
> 由 10 个分工明确的 Agent 协同产出讲义、题目、代码、思维导图、PPT、拓展阅读、动画脚本，
> 并对疑问做苏格拉底式引导答疑。

**赛道契合点**：把"多智能体融合"落在**教育个性化学习**这一个可感知痛点——
一个 Agent 只会回答问题，一组 Agent 才能"画像 → 规划 → 多模态产出 → 答疑"闭环协同。

---

## 1. 总体架构映射

| EduAgent 现有层 | remio 对应物 | 说明 |
| --- | --- | --- |
| 10 个 Agent（Router/Profile/Planner/Doc/Quiz/Code/Media/Reading/Tutor，含 Video） | 语义端点 + `run_prompt` 编排 | 每个 Agent 是一个语义端点，内部用 `run_prompt` 限定能力范围 |
| LLM Wiki 知识中枢（Chroma + BGE，混合检索 + Rerank） | remio `search_notes` / `rag` / `rag_stream` | 知识库 md 导入为 remio notes，`rag` 负责"基于知识库回答"，防幻觉 |
| 8 维度学生画像 | remio note（结构化画像卡） | `read_note` 读画像，Agent 生成前注入画像 |
| 生成资源（讲义/题目/代码/导图/PPT） | remio UI 组件（card/list/choice/input/image/button） | 结构化结果用 UI 承载，非结构化讲解用对话 |
| SSE 流式输出 | `rag_stream` + `send_chat_message` | 答疑用流式，卡片展示用 UI |
| 学习行为追踪 / 学习路径 | 内容事件订阅 `POST /_event` | 复习提醒、薄弱点回访自动化 |

**推荐开发顺序（按赛事官方指引）**：
1. 语义端点先行（第 3 节）
2. 对话覆盖主路径（第 4 节）
3. 必要处补 UI（第 5 节）
4. 订阅与系统调用自动化（第 6 节）
5. 安装、验证并发布（第 7 节）

---

## 2. 知识库导入（一次性的"知识底座"）

EduAgent 已内置结构化课程知识库：`backend/knowledge/计算机网络知识库/`，含全课程
章节文档、事实卡、习题解析、代码案例、实验文档（约 160 篇 Markdown）。

**导入 remio 的步骤**：把它们逐文件写入 remio notes，标题携带章节前缀，便于
`search_notes` 按 `chapter` / `section` 过滤：

- 标题命名：`[计算机网络] 05_运输层/TCP连接管理`
- 正文：Markdown 原文
- 元数据（若 aapp-studio 支持）：`course_id=cn-net`、`chapter=运输层`、`section=TCP`

导入后，remio 能力分工：

| 需求 | remio 能力 | 用途 |
| --- | --- | --- |
| 已知 note ID 直接读 | `read_note` | 读学生画像卡、读知识库笔记正文（注入生成上下文） |
| 先找候选内容 | `search_notes` | 意图路由后定位知识点、习题、代码案例 |
| 直接基于知识库回答/总结/对比 | `rag` / `rag_stream` | 可选增强：平台侧问答语料就绪后再启用 |
| 需要真正语义理解/生成/判断 | `run_prompt` | 各 Agent 的生成与编排，`capabilities` 限定工具范围 |
| 联网检索/抓取正文 | `web_search` / `web_get` | E9 拓展阅读（主通道）；E10 答疑在知识库不足时的显式升级 |

> 防幻觉三防线在新平台的落法：① 锚定型端点（E4–E8、E10 一级）用
> `run_prompt(capabilities="none")` **物理禁止联网**，由 `search_notes` + `read_note`
> 注入知识库**正文**（不是只给标题）；② 提示词要求"只依据检索片段作答，不足则标注"，
> E10 以首行 `GROUNDED` / `INSUFFICIENT` 标记显式上报覆盖度，升级联网必须显式发生；
> ③ 来源分级标注：`[来源：章节>小节]`（知识库）与 `[网络来源](URL)`（仅引用实际
> 抓取过的页面）分栏展示。

---

## 3. 语义端点清单（核心）

共 10 个端点，与 10 个 Agent 对应（Media Agent 承担思维导图与 PPT 两个端点；VideoAgent 作为可选端点，联网搜 B 站视频）。

| # | 端点名 | 对应 Agent | 主能力 | 输入 | 输出 UI 组件 |
| --- | --- | --- | --- | --- | --- |
| E1 | `route_intent` | Router | `run_prompt` | 学生原话 | —（内部路由） |
| E2 | `build_profile` | Profile | `run_prompt` + `read_note` | 学生自我描述 | card（画像确认） |
| E3 | `plan_learning` | Planner | `run_prompt` + `search_notes` | 主题 + 画像 | list（资源计划） |
| E4 | `generate_document` | Doc | `rag` + `run_prompt` | 主题 + 画像 | card（讲义） |
| E5 | `generate_quiz` | Quiz | `rag` + `run_prompt` | 主题 + 讲义 | choice / input + button |
| E6 | `generate_code` | Code | `rag` + `run_prompt` | 主题 + 讲义 | card（代码块）+ button |
| E7 | `generate_mindmap` | Media | `rag` + `run_prompt` | 主题 + 讲义 | card（Markdown 结构） |
| E8 | `generate_ppt` | Media | `rag` + `run_prompt` | 主题 + 讲义 | list（大纲）/ image（成图） |
| E9 | `generate_reading` | Reading | `rag` + `run_prompt` | 主题 + 讲义 | list（拓展阅读） |
| E10 | `tutor_answer` | Tutor | `rag_stream` + `run_prompt` | 问题 + 画像 | 对话 + card（来源） |

> `generate_animation`（动画分镜脚本）与 `search_video`（B 站视频）为可选增强端点，逻辑
> 与 E8/E9 一致，评委演示时可作为"资源类型 > 5"的加分展示。

### E1 · 意图路由 `route_intent`

- **触发**：用户每轮输入后最先调用。
- **输入**：`{text: 学生原话}`
- **逻辑**：`run_prompt` 让模型输出 JSON 路由决策；失败时回退规则路由（关键词正则）。
- **输出**：
  ```json
  {"topic": "TCP", "update_profile": false, "is_tutor_question": true,
   "generate_document": false, "resource_types": [], "quiz_only": false}
  ```
- **编排**：`update_profile=true → E2`；`is_tutor_question=true 且不生成资料 → E10`；
  否则 `→ E3`。

### E2 · 画像构建 `build_profile`

- **触发**：学生提到专业/年级/基础/目标/编程水平/学习风格。
- **逻辑**：`run_prompt` 抽取 8 维度画像（专业、年级、知识基础、学习目标、编程水平、
  认知风格、可投入时长、偏好资源类型）；用 `read_note("student_profile")` 合并历史画像，
  再写回同一 note（画像存续）。
- **输出**：card 展示「已更新画像」的维度摘要，让学生确认。

### E3 · 资源规划 `plan_learning`

- **逻辑**：`search_notes` 定位主题所在章节与前置知识；`run_prompt` 依据画像与主题拆解
  本轮要产出的资源类型（document/quiz/code/mindmap/reading 默认；明确要求时加 ppt/animation/video）。
- **输出**：list「本轮学习计划」，逐项可点击触发 E4–E9。

### E4 · 讲义生成 `generate_document`

- **逻辑**：
  1. `search_notes` 定位候选 → `read_note` 取知识库正文，拼装带来源的知识上下文；
  2. `run_prompt(capabilities="none")` 用 DocAgent 人设 + 画像 + 上下文，生成中文讲义（主题概览→核心概念→学习步骤→常见误区→复习建议）；
  3. 文末附 `[来源：章节>小节]`；未命中知识库时明确标注"未经课程知识库锚定，请核对教材"。
- **输出**：card（讲义正文）+ 折叠的来源引用。

### E5 · 出题 `generate_quiz`

- **逻辑**：知识上下文（`search_notes` + `read_note`）→ `run_prompt(capabilities="none")` 按画像难度生成多题型（选择/判断/填空/简答）。
- **输出**：choice（选择题，可判别对错）/ input（填空、简答）+ button「提交并解析」；
  提交后 `run_prompt` 判分并逐题讲解（苏格拉底式给提示）。

### E6 · 代码实操 `generate_code`

- **输出**：card 展示可运行 Python 案例 + button「复制代码」；附运行说明与预期输出。

### E7 · 思维导图 `generate_mindmap`

- **输出**：card 展示 Markdown 层级结构；如 aapp-studio 支持，转 `image` 渲染。

### E8 · PPT `generate_ppt`

- **输出**：先给 list（分页大纲），用户确认后可选生成配图（`image`）。

### E9 · 拓展阅读 `generate_reading`（联网优先）

- **逻辑**：`web_search(topic)` → 取前 3~5 条用 `web_get` 抓正文 →
  `run_prompt(capabilities="none")` 基于抓到的正文生成"标题 + URL + 一句话中文导读"，
  **只允许引用实际抓取成功的 URL**；卡片附"本次抓取并核实的网页"清单。
- **降级**：`web_search` 不可用（未配置商业搜索源/额度耗尽，平台会显式报错）时
  回退为模型推荐经典材料，并标注"⚠️ 未经链接核实"。
- **输出**：card（推荐列表）+ text（已核实网页来源）。

### E10 · 答疑 `tutor_answer`（两级，禁止静默切换）

- **一级（知识库）**：`search_notes` + `read_note` 锚定 → `run_prompt(capabilities="none")`
  苏格拉底式解答；模型首行输出 `GROUNDED` / `INSUFFICIENT` 显式上报知识库覆盖度。
- **二级（网络）**：仅当一级 `INSUFFICIENT` 或用户传 `deep=true` 时触发：
  `web_search` → `web_get` 抓正文 → 基于抓取内容作答；回答前明确告知
  "课程知识库未充分覆盖此问题，以下来自网络"。
- **来源分级**：`📚 课程知识库`（`[来源：章节>小节]`）与 `🌐 网络`（`[网络来源](URL)`，
  仅引用实际抓取过的页面）分栏展示；联网不可用时诚实降级为知识库作答 + 覆盖度提示。
- **输出**：card（解答）+ text（分级来源）。

---

## 4. 对话主路径（覆盖主链路的示例编排）

以学生一句话触发完整闭环为例：

```
学生："我是计算机专业大一学生，基础一般，帮我复习一下 TCP 三次握手"
   │
   ├─ E1 route_intent  →  {update_profile:true, generate_document:true, topic:"TCP三次握手"}
   ├─ E2 build_profile →  写回画像 note，card 展示"已更新：专业=计算机、年级=大一、基础=一般"
   ├─ E3 plan_learning →  list：讲义 / 练习题 / 代码案例 / 思维导图 / 拓展阅读
   ├─ E4 document      →  card「TCP三次握手 个性化学习讲义」
   ├─ E5 quiz (并行)   →  choice「TCP 第三次握手的作用是？」
   ├─ E6 code (并行)   →  card「socket 建立连接的最小示例」
   ├─ E7 mindmap (并行)→  card「三次握手状态流转图」
   └─ E9 reading (并行)→  list 拓展阅读
```

并行原则沿用原设计：**Profile 串行优先（其余依赖画像）→ Doc/Quiz/Code/Media 并行生成**。

---

## 5. UI 组件使用规范（对话为主，UI 为辅）

固定字段、互斥选项、结构化结果交给 UI；解释、协商、取舍交给对话：

| 内容 | 组件 |
| --- | --- |
| 画像维度确认 | card + list |
| 资源计划 | list |
| 讲义正文 | card |
| 选择题 | choice |
| 填空/简答 | input + button |
| 代码 | card（代码块）+ button |
| 思维导图/图片 | card 或 image |
| 来源引用/拓展阅读 | list |

快捷菜单/overlay 只做入口，不做第二层深层导航（遵守官方指引，避免体验割裂）。

---

## 6. 订阅与系统调用自动化

| 自动化场景 | 实现方式 |
| --- | --- |
| 每日/每周复习提醒 | 内容事件订阅：`POST /_event`，触发条件 = 定时用户订阅内容；动作 = `search_notes` 找薄弱点 + `send_chat_message` 推送 |
| 薄弱知识点回访 | 画像 note 中记录「最近答错知识点」，触发后让 `tutor_answer` 出 1 道自测题 |
| 生成结果落地 | 讲义/题目写回 remio note（用系统调用写回笔记），实现"学习资产沉淀" |

需要用户可见反馈时，一律显式调用 `send_chat_message`。

---

## 7. 发布与版本说明

1. **调试**：在 aapp-studio 完成端点联调，验证 10 端点 + 主路径闭环。
2. **安装到正式环境**：向 aapp-studio 说"帮我把 EduAgent 应用安装到正式环境"。
3. **发布到应用市场**：通过版本验证、填写开发者信息、避免版本号冲突；市场版启用完整性签名。

### 跨产品运行（加分项，配合 MCP）

同一套引擎已封装为 **MCP 工具集**（见 `../mcp/README.md`，实现文件
`backend/app/mcp_server.py`），可在 remio 及其他支持 MCP 的智能体宿主中注册调用，
直接回应赛事"如能在其他智能体产品中正常运行更佳"的加分要求。

---

## 8. 与赛题刚性约束的对照自检

| 约束 | 满足方式 |
| --- | --- |
| 画像维度 >= 6 | 8 维度画像（E2） |
| 资源类型 >= 5 | 讲义/题目/代码/导图/PPT/拓展阅读/动画（7 类） |
| 多智能体架构 | 10 个 Agent 独立端点、明确分工、Router→Profile→并行生成 协同编排 |
| 防幻觉 | `rag` 知识锚定 + 来源引用 + 输出过滤三重防线 |
| 流式输出 | `rag_stream` 答疑流式，UI 卡片即时渲染 |
| 初始知识库 | 内置《计算机网络》全课程知识库（md → notes） |
| AI 辅助工具 | remio 平台能力 + DeepSeek/OpenAI 兼容（MCP 引擎侧）双轨 |