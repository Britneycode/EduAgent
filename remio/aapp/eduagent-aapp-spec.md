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
> 并对疑问做苏格拉底式引导答疑。学生自带资料（课堂笔记/课件）或任意主题在知识库
> 未覆盖时，按「知识库 → 会话材料 → 网络」三级来源兜底生成。

**赛道契合点**：把"多智能体融合"落在**教育个性化学习**这一个可感知痛点——
一个 Agent 只会回答问题，一组 Agent 才能"画像 → 规划 → 多模态产出 → 答疑"闭环协同。

---

## 1. 总体架构映射

| EduAgent 现有层 | remio 对应物 | 说明 |
| --- | --- | --- |
| 10 个 Agent（Router/Profile/Planner/Doc/Quiz/Code/Media/Reading/Tutor，含 Video） | 语义端点 + `run_prompt` 编排 | 每个 Agent 是一个语义端点，内部用 `run_prompt` 限定能力范围 |
| LLM Wiki 知识中枢（Chroma + BGE，混合检索 + Rerank） | remio `search_notes` + `read_note` | 知识库 md 导入为 remio notes，检索注入正文生成（平台 `rag`/`rag_stream` 为可选增强），防幻觉 |
| 8 维度学生画像 | remio note（结构化画像卡） | `read_note` 读画像，Agent 生成前注入画像 |
| 生成资源（讲义/题目/代码/导图/PPT） | remio UI 组件（card/list/choice/input/image/button） | 结构化结果用 UI 承载，非结构化讲解用对话 |
| SSE 流式输出 | `run_prompt` 生成 + UI 卡片即时渲染 | 推送用 `send_chat_message`；`rag_stream` 为平台侧修复后的可选流式增强 |
| 学习行为追踪 / 学习路径 | 内容事件订阅 `POST /_event` | 复习提醒、薄弱点回访自动化 |

**推荐开发顺序（按赛事官方指引）**：
1. 语义端点先行（第 3 节）
2. 对话覆盖主路径（第 4 节）
3. 必要处补 UI（第 5 节）
4. 订阅与系统调用自动化（第 6 节）
5. 安装、验证并发布（第 7 节）

---

## 2. 知识库导入（一次性的"知识底座"）

EduAgent 已内置结构化课程知识库：`knowledge/计算机网络知识库/`，含全课程
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
| 联网检索/抓取正文 | `web_search` / `web_get` | E9 拓展阅读（主通道）；E4–E8 生成与 E10 答疑在知识与材料层均未命中时的显式兜底 |

> 防幻觉三防线在新平台的落法：① 所有生成与答疑端点（E4–E10）一律
> `run_prompt(capabilities="none")` **物理禁止模型联网**，知识上下文由代码注入**正文**
> ——知识库与材料层经 `search_notes` + `read_note` 取回（不是只给标题），网络层由代码
> 显式 `web_search` + `web_get` 抓取后注入；② 提示词要求"只依据注入片段作答，不足则标注"，
> 各端点的覆盖层级由代码按各层检索命中判定，在结果卡片显式标注（📚/📎/🌐），升级到网络
> 必须显式发生；③ 来源分级标注：`[来源：章节>小节]`（知识库）、`📎 材料文件名`（会话材料）
> 与 `[网络来源](URL)`（仅引用实际抓取过的页面）分栏展示。

**知识库未命中时的兜底**：除了课程知识库与网络，支持学生上传**会话学习材料**（E11），
形成「课程知识库 → 会话材料 → 网络」三级覆盖。课程知识库只负责其内置课程内容，
学生自己带来的资料（课堂笔记、老师课件、外部讲义）不再是无处安放的"库外内容"，
而是作为可检索、可溯源、按会话隔离的兜底源，直接满足"知识库没有的内容也能基于材料生成"；
学生既没挂材料、知识库又不覆盖该主题时，最后由网络搜索兜底生成。

### 三级知识来源（公共机制，E4–E8 全部生成端点与 E10 答疑统一接入）

每个端点在 `run_prompt` 生成前按固定顺序获取知识上下文，**命中即停，层级由代码按
各层检索命中判定（不由模型自报）**：

1. **📚 一级 · 课程知识库**：`search_notes`（folder=计算机网络知识库）定位候选 →
   `read_note` 注入笔记正文，来源行标 `[来源：笔记标题]`；
2. **📎 二级 · 会话学习材料**：一级未命中且学生已挂载材料（E11）时，
   `search_notes`（collection=EduAgent 学习材料）→ `read_note` 注入正文，
   来源行标 `📎 材料文件名`；
3. **🌐 三级 · 网络**：一、二级均未命中时，`web_search(topic)` 取前 3~5 条 →
   `web_get` 抓正文（每页截断注入，避免超长）→ 只引用实际抓取成功的 URL，
   来源行标 `[网络来源](URL)`。

三层均未命中（或 `web_search` 不可用——未配置商业搜索源/额度耗尽，由 try/except
捕获）时，降级为"谨慎作答"并标注"⚠️ 未经课程知识库与学习材料锚定，请核对教材"。
生成一律 `run_prompt(capabilities="none")`：模型物理禁网，联网由代码显式抓取后注入。
结果卡片 subtitle 标注来源层级（📚/📎/🌐），**禁止静默切换**。

---

## 3. 语义端点清单（核心）

共 **18 个端点**（与平台侧 `api.json` 对齐）：11 个核心语义端点（E1–E11，与 10 个 Agent 对应——Media Agent 承担思维导图与 PPT 两个端点，E11 会话材料由 SessionMaterial 服务承担）+ 5 个扩展端点（判题、PPT 配图、薄弱点复习、动画分镜、视频搜索）+ 主入口 `GET /` 与内容事件订阅 `POST /_event`。

| # | 端点路径 | 对应 Agent | 主能力 | 输入 | 输出 UI 组件 |
| --- | --- | --- | --- | --- | --- |
| E1 | `POST /route_intent` | Router | `run_prompt`（关键词正则兜底） | 学生原话 | —（内部路由） |
| E2 | `GET /build_profile_ui` | Profile | `run_prompt` + `read_note` | 学生自我描述 | card（画像确认） |
| E3 | `GET /plan_learning_ui` | Planner | `search_notes` + `run_prompt` | 主题（画像从画像 note 加载） | list（资源计划） |
| E4 | `GET /generate_document_ui` | Doc | `search_notes` + `read_note` + `web_search` + `web_get` + `run_prompt`（三级来源） | 主题 | card（讲义） |
| E5 | `GET /generate_quiz_ui` | Quiz | `search_notes` + `read_note` + `web_search` + `web_get` + `run_prompt`（三级来源） | 主题 | choice / input + button |
| E6 | `GET /generate_code_ui` | Code | `search_notes` + `read_note` + `web_search` + `web_get` + `run_prompt`（三级来源） | 主题 | card（代码块） |
| E7 | `GET /generate_mindmap_ui` | Media | `search_notes` + `read_note` + `web_search` + `web_get` + `run_prompt`（三级来源） | 主题 | card（Markdown 结构） |
| E8 | `GET /generate_ppt_ui` | Media | `search_notes` + `read_note` + `web_search` + `web_get` + `run_prompt`（三级来源） | 主题 | list（大纲）+ button |
| E9 | `GET /generate_reading_ui` | Reading | `web_search` + `web_get` + `run_prompt` | 主题 | list（拓展阅读） |
| E10 | `GET /tutor_answer_ui` | Tutor | `search_notes` + `read_note` + `run_prompt`（三级兜底） | 问题（画像注入） | card（解答 + 来源层级） |
| E11 | `POST /attach_material_ui` | SessionMaterial | `create_note` + `add_note_to_collection` | 材料文件名 + 文本 | card（材料摘要） |

**扩展端点（5 个）**：`POST /grade_quiz_ui`（E5 判题——逐题对错 + 苏格拉底式提示，答错知识点自动写入画像 `weak_points`）、`GET /generate_ppt_images_ui`（E8 配图——大纲确认后逐页给出配图主题与作图提示词）、`GET /review_quiz_ui`（薄弱点复习——读画像 `weak_points` 生成自测题）、`GET /generate_animation_ui`（动画分镜脚本）、`GET /search_video_ui`（B 站视频搜索——`web_search` 定位 + `prepare_video` 取视频元数据）。

**入口与订阅（2 个）**：`GET /` 主视图（画像感知问候 + 画像/规划/答疑入口按钮）；`POST /_event` 内容事件处理器（画像 note 创建/修改 → 读取薄弱点 → 推送自测题）。

> **E4–E8 生成与 E10 答疑的知识来源均为三级兜底**，层级由代码按各层检索命中逐级判定：
> 课程知识库（📚）→ 会话学习材料（📎）→ 网络（🌐），层级标注在结果卡片上并附来源行，
> 任何一层切换都必须显式告知学生来源，禁止静默切换。

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
  认知风格、可投入时长、偏好资源类型）；读取画像 note《EduAgent 学生画像》合并历史画像
  后写回同一 note（画像存续）。
- **输出**：card 展示「已更新画像」的维度摘要，让学生确认。

### E3 · 资源规划 `plan_learning`

- **逻辑**：`search_notes` 定位主题所在章节与前置知识；`run_prompt` 依据画像与主题拆解
  本轮要产出的资源类型（document/quiz/code/mindmap/reading 默认；明确要求时加 ppt/animation/video）。
  规划本身不依赖知识命中——主题在知识库与材料均未覆盖时计划照常产出，
  由 E4–E8 各生成端点按三级来源自行兜底。
- **输出**：list「本轮学习计划」，逐项可点击触发 E4–E9。

### E4 · 讲义生成 `generate_document_ui`

- **逻辑**：
  1. 按**三级知识来源**（第 2 节公共机制）获取知识上下文：课程知识库（📚）→
     会话材料（📎，需 E11 挂载）→ 网络搜索（🌐，`web_search` + `web_get` 抓正文注入），
     命中即停，层级由代码判定；
  2. `run_prompt(capabilities="none")` 用 DocAgent 人设 + 知识上下文生成中文讲义
     （主题概览→核心概念→学习步骤→常见误区→复习建议）；
  3. 三层均未命中或网络不可用时，谨慎作答并标注
     "⚠️ 未经课程知识库与学习材料锚定，请核对教材"。
- **输出**：card（讲义正文，subtitle 为来源层级，末尾附来源引用行）。

### E5 · 出题 `generate_quiz_ui`（判题 `grade_quiz_ui`）

- **逻辑**：按**三级知识来源**（第 2 节公共机制）获取知识上下文 →
  `run_prompt(capabilities="none")` 生成 4–6 道混合题型（choice 承载选择/判断，
  input 承载填空/简答）；基于材料（📎）或网络（🌐）出题时，题目卡片提示学生
  核对原始来源。
- **输出**：choice / input + button「提交并解析」；提交后 `POST /grade_quiz_ui` 判分并
  逐题给出对错与苏格拉底式提示，答错/未答的知识点自动写入画像 `weak_points`。

### E6 · 代码实操 `generate_code`

- **逻辑**：按**三级知识来源**获取上下文（知识库代码案例/实验文档优先，材料次之，
  网络兜底）→ `run_prompt(capabilities="none")` 生成可运行 Python 案例。
- **输出**：card 展示可运行 Python 案例 + button「复制代码」；附运行说明与预期输出。

### E7 · 思维导图 `generate_mindmap`

- **逻辑**：按**三级知识来源**获取上下文 → `run_prompt(capabilities="none")` 生成
  Markdown 层级结构（≤3 层）。
- **输出**：card 展示 Markdown 层级结构；如 aapp-studio 支持，转 `image` 渲染。

### E8 · PPT `generate_ppt_ui`（配图 `generate_ppt_images_ui`）

- **逻辑**：按**三级知识来源**获取上下文 → `run_prompt(capabilities="none")` 生成
  6–8 页大纲（每页标题 + 要点）。
- **输出**：list（6–8 页大纲，每页标题 + 要点）+ button「🎨 生成配图建议」；
  确认后进入配图端点，逐页输出配图主题与作图提示词。

### E9 · 拓展阅读 `generate_reading`（联网优先）

- **逻辑**：`web_search(topic)` → 取前 3~5 条用 `web_get` 抓正文 →
  `run_prompt(capabilities="none")` 基于抓到的正文生成"标题 + URL + 一句话中文导读"，
  **只允许引用实际抓取成功的 URL**；卡片附"本次抓取并核实的网页"清单。
- **降级**：`web_search` 不可用（未配置商业搜索源/额度耗尽，平台会显式报错）时
  回退为模型推荐经典材料，并标注"⚠️ 未经链接核实"。
- **输出**：card（推荐列表）+ text（已核实网页来源）。

### E10 · 答疑 `tutor_answer_ui`（三级兜底，禁止静默切换）

覆盖层级由代码按各层检索命中判定（不由模型自报），学生画像从画像 note 加载并注入，
三级逻辑同第 2 节公共机制：

- **一级（📚 课程知识库）**：`search_notes`（folder=计算机网络知识库）+ `read_note`
  注入正文 → `run_prompt(capabilities="none")` 苏格拉底式解答，末尾附 `[来源：笔记标题]`。
- **二级（📎 会话材料）**：仅当一级检索未命中、且学生已通过 E11 挂载材料时触发：
  `search_notes`（collection=EduAgent 学习材料）→ 基于材料作答；明确告知
  "课程知识库未充分覆盖此问题，以下基于你上传的材料"，并标注材料文件名。
- **三级（🌐 网络）**：仅当一、二级均未命中时触发：`web_search` → `web_get` 抓正文 →
  基于抓取内容作答；明确告知"课程知识库与已上传材料均未覆盖此问题，以下来自网络"，
  仅引用实际抓取过的 URL。
- **兜底**：三层均未覆盖时，明确说明"课程知识库、学习材料与网络均未充分覆盖此问题，
  以下为谨慎作答"。
- **输出**：card（解答，subtitle 为来源层级）+ 末尾来源行。

### E11 · 挂载学习材料 `attach_material_ui`

- **触发**：学生上传自己的笔记/课件/讲义（md/txt/pdf/pptx 提取文本）。
- **逻辑**：`create_note` 写入标题带 `[EduAgent材料]` 前缀的 note，并加入独立集合
  `EduAgent 学习材料`（`add_note_to_collection`）。
- **隔离**：课程知识库检索限定 folder（`计算机网络知识库`），材料检索限定 collection，
  两个来源互不串扰。
- **输出**：card 展示已挂载文件名、字符数、段落块数与挂载状态。
- **后续**：E4–E8 全部生成端点与 E10 答疑在知识库未命中时自动基于材料生成并标注来源。

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
| 薄弱点复习推送 | 平台静态订阅：画像 note《EduAgent 学生画像》创建/修改 → `POST /_event` 读取 `weak_points` → 生成一道自测题 → `send_chat_message` 推送 |
| 每日/每周复习提醒 | 可配置 remio 定时自动化触发 `GET /review_quiz_ui`，或从聊天菜单「🔁 每日复习自测」手动进入 |
| 薄弱知识点回访 | 画像 note 中记录「最近答错知识点」，触发后让 `tutor_answer` 出 1 道自测题 |
| 学习资产沉淀 | 画像与薄弱点持久化到画像 note（`update_note`），判题后自动回写 |

需要用户可见反馈时，一律显式调用 `send_chat_message`。

---

## 7. 发布与版本说明

1. **调试**：在 aapp-studio 完成端点联调，验证 18 个端点 + 主路径闭环。
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
| 防幻觉 | `search_notes`→`read_note` 正文锚定 + 三级来源（知识库/材料/网络）全端点显式标注 + 仅引用实际抓取的 URL |
| 流式输出 | `run_prompt` 生成 + UI 卡片即时渲染（`rag_stream` 为平台侧修复后的可选流式增强） |
| 初始知识库 | 内置《计算机网络》全课程知识库（md → notes） |
| AI 辅助工具 | remio 平台能力 + DeepSeek/OpenAI 兼容（MCP 引擎侧）双轨 |
