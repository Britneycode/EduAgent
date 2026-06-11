# 比赛演示版学习闭环 V2 设计（Tutor 驱动 + 互动小测 + 动态路径）

- 日期：2026-04-20
- 目标：在现有 EduAgent MVP 基础上，落地一条“看得见、讲得清、跑得稳”的比赛演示闭环：**Tutor 主讲解 → 3 题互动小测 → 效果评估 → 动态路径调整 → 下一步行动**。

## 1. 范围与原则

### 1.1 范围（本轮要做）

- 聊天页内完成一轮闭环：Tutor 主输出 + Quiz 互动 + Evaluation 摘要 + PathUpdate 卡 + NextActions。
- Media Agent 升级为“即时图解型资源”：新增 `diagram`（Mermaid 流程图/机制图解），保留 `mindmap`。
- 支持将评估与路径调整同步到独立的学习路径页（可复盘）。
- 轻量内容审核、缓存与降级策略，保证比赛现场稳定性。
- 轻量可观测性：在现有 AgentStatus 基础上补充耗时/降级原因；后端结构化回合日志。
- 最小评测与演示数据体系，保证可重复演示。

### 1.2 非目标（本轮不做）

- 视频/音频/动画渲染与重媒体文件链路。
- 复杂审核工作流、完整监控平台接入、独立推荐引擎。
- 长周期画像趋势建模与复杂学习分析。

### 1.3 核心原则

- **Tutor 必达**：Tutor 主回答必须先出且不中断；其他模块失败不得阻塞。
- **闭环即时**：作答后“评估 + 调路径”在同一聊天体验内即时可见。
- **降级可讲清**：所有失败都要有中文占位卡与明确原因。
- **结构化优先**：Quiz/Eval/Path 结果用结构化数据驱动 UI，而不是前端猜测。

## 2. 总体架构：学习回合 LearningTurn

### 2.1 概念

将一次 assistant 的“闭环响应”定义为一个 **LearningTurn**（`turn_id`）。Turn 内含多种输出与用户交互：

- Tutor 主输出（流式 token）
- Quiz 题目卡（3 题）
- 用户作答（提交接口）
- Evaluation 评估卡
- PathUpdate 路径调整卡
- NextActions 行动建议

### 2.2 调度策略

- Orchestrator 仍作为聊天入口，但引入 turn_id 并在日志与落库中贯穿。
- Tutor 输出优先；Quiz 题目卡尽量在 Tutor 开场后尽早下发。
- 作答提交后触发 EvaluationService 与 PathService 计算，并以 SSE 或同步响应方式回传。

## 3. SSE 事件与接口契约

### 3.1 新增 SSE 事件（最小可演示集合）

在现有 `token` / `agent_status` / `resource_card` / `done` 基础上新增：

- `quiz_presented`：下发本轮 3 题（无正确答案）。
- `quiz_answer_ack`：前端提交答案后的回执，用于 UI 锁定。
- `evaluation_update`：评估摘要（得分、薄弱点、掌握度变化、节奏建议、摘要）。
- `path_update`：路径调整结果（目标、已掌握/待巩固/下一步/目标分组 + 摘要原因）。
- `next_actions`：2-4 条下一步行动建议（可带跳转目标：资源 id / 知识点 / 路径页）。

`agent_status` 事件增强字段：

- `duration_ms`：该模块耗时
- `degraded`：是否降级
- `reason`：降级原因（中文）

### 3.2 新增 HTTP 接口（最少 1 个）

- `POST /api/quiz/answer`
  - 入参：`session_id`、`turn_id`、`answers[]`（题目 id + 用户答案）
  - 出参：`evaluation`、`path_update`、`next_actions`
  - 约定：服务端也可将同样内容通过 SSE 推送；前端以“谁先到用谁”为准。

### 3.3 降级规则

- Quiz 失败：不出题卡，仅出 next_actions，引导用户继续。
- Evaluation 失败：仍可出 PathUpdate 的“静态版”（基于 prerequisites + profile）。
- Path 失败：仅出 next_actions（文字版下一步替代路径卡）。

## 4. 数据模型与持久化（允许新增表）

新增 3 张表即可支持闭环复盘：

### 4.1 quiz_attempts

字段建议：

- `session_id`, `turn_id`, `knowledge_point`
- `quiz_payload` (JSONB)：题面/选项/标准答案/解析快照
- `answers` (JSONB)
- `score`, `correct_count`
- `submitted_at`

### 4.2 learning_evaluations

字段建议：

- `session_id`, `turn_id`, `knowledge_point`
- `score`
- `weak_points` (JSONB)
- `mastery_delta` (JSONB)
- `pace_suggestion`
- `summary`
- `created_at`

### 4.3 learning_path_versions

字段建议：

- `session_id`, `turn_id`, `goal_topic`
- `path_data` (JSONB)：`mastered / strengthen / next / target`
- `reason_summary`
- `created_at`

## 5. 后端模块拆分

### 5.1 QuizService

- 负责生成 3 题小测（可复用 QuizAgent 生成能力，但输出结构化 JSON）。
- 负责答案校验与打分，落库 quiz_attempts。

### 5.2 EvaluationService

输入：quiz_attempt + 用户反馈文本（可选）+ profile + topic

输出：learning_evaluations（掌握度变化、薄弱点、节奏建议、摘要），并驱动画像的中等粒度更新。

### 5.3 PathService

输入：topic + profile + evaluation（可选）

输出：learning_path_versions（四组节点 + 摘要原因）。

- evaluation 缺失时：回退为静态版（prerequisites + profile 阈值）。

### 5.4 ContentGuard（审核 + 缓存）

- 结构校验：Mermaid 代码块存在性、过长截断、中文输出约束。
- 轻量安全过滤：敏感词/明显违规内容拦截。
- 缓存：`topic + resource_type + profile粗粒度` 为 key，短 TTL（10-30 分钟）。

## 6. 前端：学习回合 UI（聊天页）

### 6.1 卡片分区

在一轮 streaming 区域内，按顺序展示：

1. Tutor 主回答（StreamingText）
2. Quiz 互动卡（3 题作答 + 提交）
3. 评估摘要卡（得分/薄弱点/掌握度变化/节奏建议）
4. 路径调整卡（目标/已掌握/待巩固/下一步）
5. NextActions（按钮/链接）

### 6.2 资源联动（最小版）

- ResourceCard 显示关联知识点徽标。
- 路径卡点击“下一步节点”：在当前回合资源里高亮匹配 `knowledge_point` 的资源；不存在则触发生成该知识点资源（作为 next_action）。

## 7. Media：即时图解型资源

- 新增资源类型 `diagram`：Mermaid flowchart/graph 图解 + 中文说明。
- 保留 `mindmap`：Mermaid mindmap。
- `ppt` 降为次级，不作为比赛版主展示资源。
- Mermaid 渲染失败：前端降级为显示原始代码块。

## 8. 稳定性：超时与并发

- 生成类模块硬超时（8-12s），可取消。
- Tutor 优先；其他模块并行但允许失败。
- 对同一 session 新消息到来时，旧 turn 的后台任务应中止或结果作废。

## 9. 可观测性（比赛版）

- SSE `agent_status` 增强：耗时/降级/原因。
- 后端结构化回合日志：`session_id + turn_id` 汇总本轮调用模块、耗时、缓存命中与降级点。

## 10. 评测与演示数据

### 10.1 最小自动化评测

- EvaluationService / PathService：单元测试验证字段齐全与分组规则正确。
- chat/[sessionId]：一条关键交互测试覆盖“出题→作答→评估卡+路径卡”。

### 10.2 演示脚本（可复现）

- 场景 1：反向传播（diagram + 3题小测 + 掌握度变化 + 下一步路径）
- 场景 2：A* 搜索（diagram + mindmap + 小测 + 路径调整）
- 场景 3：用户反馈“太难/没听懂”（节奏建议 + 路径回退到前置知识）

## 11. 设计自检

- 无 TBD/TODO 占位。
- 目标聚焦比赛演示闭环，不引入重媒体与重平台能力。
- 与现有架构兼容：在 Orchestrator/SSE/前端 store 基础上增量扩展。
