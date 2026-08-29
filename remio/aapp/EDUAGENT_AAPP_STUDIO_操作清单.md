# aapp-studio 逐步操作清单（EduAgent 个性化学习智能体）

> 用途：拿到 remio 桌面客户端后，按本清单逐条在 **aapp-studio** 内落地
> `eduagent-aapp-spec.md`。每条给出"要说什么 / 要做什么"和"验证点"，照着走即可。
> 前提：已登录 remio、已下载并打开 remio 客户端，能找到 aapp-studio 入口。

---

## 阶段 0 · 准备知识库笔记（一次性）

1. 把 `backend/knowledge/计算机网络知识库/` 下的 Markdown 逐篇导入为 remio notes。
   - 标题统一加前缀：`[计算机网络] 章节/标题`，例如 `[计算机网络] 05_运输层/TCP连接管理`。
   - 若 aapp-studio 支持元数据，补 `course_id=cn-net`、`chapter`、`section`。
2. **验证点**：在对话里问 remio"搜一下 TCP 三次握手"，能通过 `search_notes` 返回知识库片段。

## 阶段 1 · 声明语义端点（核心）

对 aapp-studio 说明（可整体粘贴）：

> 我要做一个面向高校学生的个性化学习智能体，包含以下语义端点：
> 1) route_intent：识别意图；2) build_profile：构建 8 维画像；3) plan_learning：拆解资源任务；
> 4) generate_document：生成讲义；5) generate_quiz：出题；6) generate_code：代码案例；
> 7) generate_mindmap：思维导图；8) generate_ppt：PPT 大纲；9) generate_reading：拓展阅读；
> 10) tutor_answer：苏格拉底式答疑。
> 每个端点的输入输出、能力映射和 UI 组件按附上的规格文件实现。

然后逐端点确认，尤其：

| 端点 | 关键说明 | 验证点 |
| --- | --- | --- |
| route_intent | `run_prompt` 输出 JSON 路由；失败回退关键词正则 | 输入"给我出几道 TCP 的题"→ 返回 `resource_types=["quiz"]` |
| build_profile | 读写画像 note（`read_note`/写回） | 输入"我是大一计算机专业"→ 弹出画像确认卡 |
| generate_document | `rag` 取上下文 + `run_prompt` 生成；文末带 `[来源：章>节]` | 生的讲义末尾有来源引用 |
| generate_quiz | 选择题用 `choice`，填空/简答用 `input`+`button` | 判断题可自动判对错 |
| tutor_answer | 用 `rag_stream`；`study_mode=true` 走引导式 | 输出逐字流式 + 来源卡 |

## 阶段 2 · 对话覆盖主路径

在 aapp-studio 里把"路由 → 画像 → 规划 → 并行生成 → 答疑"的编排串起来，确认
Profile 串行优先，Doc/Quiz/Code/Media 并行。

**验证点**（用一句话走通全链路）：

> 我是计算机专业大一学生，基础一般，帮我复习一下 TCP 三次握手

预期：先出画像确认卡 → 再出资源计划 list → 讲义/题/代码/导图/拓展阅读同时出现 → 每项带来源。

## 阶段 3 · 补 UI（对话为主，UI 为辅）

- 讲义 → `card`；题 → `choice`/`input`+`button`；代码 → `card`+复制按钮；
  导图/PPT → `card` 或 `image`；来源/拓展阅读 → `list`。
- 快捷菜单 / overlay 只做入口，不做第二层导航。
- **验证点**：固定字段和互斥选项都在 UI 上点得动，解释说明在对话里。

## 阶段 4 · 订阅与自动化

对 aapp-studio 说：

> 加一个内容事件订阅：每天定时（或按我设定的节奏）触发 POST /_event，先 search_notes 找
> 学生最近答错的知识点，再 run_prompt 生成一道自测题，最后 send_chat_message 推送给学生。

**验证点**：手动触发一次事件，能收到自测题推送。

## 阶段 5 · 安装、验证、发布

1. 开发环境联调通过后，说："帮我把 EduAgent 应用安装到正式环境"。
2. 发布前完成版本验证、填开发者信息、避免版本号冲突。
3. 发布到应用市场（启用完整性签名 / 加密授权，按客户端提示）。

**验证点**：正式环境跑通阶段 2 的同一句触发语，结果一致。

---

## 常见踩坑

| 现象 | 处理 |
| --- | --- |
| `rag` 答的内容与知识库不符 | 确认 notes 导入完成、标题前缀统一；端点在 `run_prompt` 里要求"只依据检索片段作答，不足则标注" |
| 画像不生效 | 确认 `build_profile` 写回的画像 note 被后续端点通过 `read_note` 读到 |
| 流式没效果 | 答疑端点确定用 `rag_stream`，而不是 `rag` |

> 完整端点定义见同目录 `eduagent-aapp-spec.md`；机器可读清单见 `eduagent-aapp-manifest.json`。
> 若 aapp-studio 某处界面英文且与本清单术语对不上，按功能（端点=endpoint/能力=capability/订阅=subscription）对应即可。