# Tutor 答疑闭环设计

## 1. 背景与目标

当前 EduAgent 已完成最小多资源学习包闭环：围绕同一 topic 串行生成 `document -> quiz -> code`，并通过 SSE 依次推送给前端。这已经验证了多 Agent 协同生成学习资源的主链路，但系统仍缺少一个关键闭环：学生拿到资源后，无法继续围绕这些资源追问、澄清、纠错与深入理解。

本阶段目标是新增 Tutor 答疑链路，让系统不仅能“生成学习内容”，还能“围绕学习内容继续辅导”。第一版聚焦最小可行闭环：先支持基于当前会话资源的继续追问，再兼容没有资源前置的自由问答。

## 2. 设计目标

### 2.1 要解决的问题
- 用户生成讲义、练习题、代码后，无法自然追问“这一段为什么这样写”“我还是没懂”“我选 B 对吗”
- 当前聊天主链路只有资源生成，没有持续辅导能力，Tutor 角色尚未落地
- 多 Agent 协同价值还停留在资源生产阶段，没有形成“生成 + 讲解 + 纠错”的学习闭环

### 2.2 第一版成功标准
- 用户可在当前聊天会话中针对最近资源继续追问
- Tutor 可对当前会话中最近 quiz 的作答做判断与讲解
- Tutor 支持流式输出，保持和现有 chat SSE 一致
- Tutor 不新增资源卡，不改变现有资源中心协议
- 自由问答在无会话资源时可回退到 Wiki 支撑的答疑

### 2.3 明确不做的事
- 不把 Tutor 回复存为新的 `tutor` 资源类型
- 不把 Tutor 纳入 Planner 统一编排
- 不做复杂教学状态机、长期教学记忆、错题本系统
- 不支持任意外部题目的批改，只支持当前会话最近 quiz 的纠错反馈

## 3. 推荐方案

推荐方案：**最小 Tutor 内联方案**。

### 3.1 方案摘要
- 扩展 `RouterAgent`，增加 Tutor 路由分支
- 新增 `TutorAgent`，专门负责生成答疑文本
- 在 `Orchestrator` 中新增 Tutor 分支，复用现有 SSE token 流式输出
- Tutor 优先读取当前会话最近资源，不足时补充 Wiki 上下文
- Tutor 回复只作为聊天消息，不生成 `resource_card`

### 3.2 为什么选这个方案
- 改动最小，能在现有稳定主链路上快速落地
- 边界清晰：资源生成仍归 Planner，追问讲解归 Tutor
- 最大化复用现有聊天 API、SSE、会话资源和 Wiki 能力
- 能最快形成“学习包生成 → 围绕资源继续辅导”的 MVP 闭环

### 3.3 暂不采用的方案
#### 显式 TutorContextBuilder 方案
优点是边界更清晰、适合长期演进；缺点是第一版偏重。当前先用轻量上下文组装方法，等 Tutor 复杂度上来后再抽离。

#### 把 Tutor 纳入 Planner 统一编排
长期可能更统一，但会让当前刚稳定的多资源链路再经历一次较大重构。对本阶段 MVP 来说不划算。

## 4. 用户体验与行为规则

### 4.1 支持的请求类型
Tutor 第一版支持三类请求：
1. **概念解释**：如“为什么反向传播要用链式法则？”
2. **基于资源的继续追问**：如“这段代码什么意思？”“这一题我还是不懂”
3. **当前会话 quiz 纠错反馈**：如“我选 B，对吗？”

### 4.2 回答风格
Tutor 第一版采用**混合型**回答策略：
- 先直接解释，解决用户眼前问题
- 再追加 1 个简短引导问题，帮助继续学习

示例风格：
- “我先基于刚才那道练习题解释。”
- “这里的关键是链式法则把多层导数拆成逐层相乘。”
- “如果你愿意，我可以再用一个更直观的数值例子说明。”

### 4.3 来源提示规则
Tutor 不做重型引用块，只做轻量来源提示：
- 命中会话资源时：说明“基于刚才的讲义/练习题/代码继续解释”
- 回退到 Wiki 时：说明“当前会话里没有相关资源，我先按知识库内容解释”

### 4.4 模糊提问处理
当用户输入“还是不懂”“再讲一下”这类模糊问题时：
- 若最近资源与当前上下文足够明确，Tutor 直接接住并继续讲
- 若无法可靠判断对应的是哪一段内容，再发一个很短的澄清问题
- 第一版的分界规则是：只要资源定位、题目定位或用户答案提取中任一关键环节不可靠，且直接解释会明显依赖猜测上下文时，必须优先短澄清；只有在当前问题即使脱离精确定位也仍可安全回答为通用概念解释时，才允许直接退化为解释型答复

## 5. 路由设计

## 5.1 路由分类
`RouterAgent` 扩展后需要至少区分三类意图：
- `profile`：画像更新类请求
- `resource_generation`：讲义、练习题、代码、学习包生成类请求
- `tutor`：解释、追问、不会、再讲一下、答案判断类请求

### 5.2 路由规则
- 明显生成型请求：继续走 Planner 链路
- 明显答疑型请求：走 Tutor 链路
- 模糊学习型请求：优先按 Tutor 处理，避免误生成资源
- 第一版每条请求只允许一个主响应模式：`resource_generation` 或 `tutor`，不允许同一轮同时执行两条主分支
- 若同一条请求同时包含强画像信号，允许出现复合命中：
  - `profile + resource_generation`：先更新画像，再走资源生成
  - `profile + tutor`：先更新画像，再走 Tutor 答疑
- 若同一条请求同时出现“生成资源 + 提问讲解”，第一版按主意图二选一：
  - 只要包含明显生成诉求（如“给我讲义”“再出几题”“生成代码示例”），主响应模式固定为 `resource_generation`
  - 只有在不包含明确生成诉求时，才进入 `tutor`
- `profile + resource_generation + tutor` 在第一版不作为合法复合结果；Router 必须收敛为 `profile + resource_generation` 或 `profile + tutor`
- 第一版的强画像信号保持轻量，只在用户显式提供稳定背景信息时触发，例如“我是大三学生”“我准备考研”“我基础一般”“我更喜欢例子讲解”
- 若只是临时语气或当前理解状态，例如“我还是没听懂”“这题太难了”，默认视为 Tutor 上下文，不单独触发画像更新

### 5.3 RouteDecision 扩展建议
在现有 `RouteDecision` 基础上增加两个轻量字段，例如：
- `response_mode: Literal["resource_generation", "tutor", "none"]`
- `route_tags: list[Literal["profile", "resource_generation", "tutor"]]`

约束如下：
- `profile` 只是附加标签，不单独作为主响应模式
- 纯画像请求时：`route_tags == ["profile"]`，且 `response_mode == "none"`
- 画像 + 资源生成请求时：`route_tags == ["profile", "resource_generation"]`，且 `response_mode == "resource_generation"`
- 画像 + 答疑请求时：`route_tags == ["profile", "tutor"]`，且 `response_mode == "tutor"`

这里的 `response_mode` **只用于路由层主分支选择**，不承载 Tutor 内部答复类型。
Tutor 分支内部若需要区分“解释 / 继续追问 / 纠错”，应使用独立字段，例如：
- `tutor_mode: Literal["explanation", "follow_up", "correction", "clarification"]`

约束如下：
- `tutor_mode` 只在 `response_mode == "tutor"` 时存在语义
- `response_mode == "resource_generation" | "none"` 时，不要求设置 `tutor_mode`
- Tutor 自动判题只由 `tutor_mode == "correction"` 触发，不再使用 `response_mode == correction` 这类混合写法

这样 Orchestrator 可以在保持现有结构的基础上快速分支，不需要引入新编排层。

### 5.4 路由判定示例
| 用户输入示例 | 预期路由 |
|---|---|
| 帮我复习反向传播并给我练习题和代码示例 | resource_generation |
| 给我讲一下什么是链式法则 | tutor |
| 这道题我选 B，对吗 | tutor |
| 这段代码我没看懂 | tutor |
| 我是大三学生，准备考研，基础一般 | profile |
| 我是大三学生，帮我生成一份反向传播讲义 | profile + resource_generation |
| 我是大三学生，这道题我还是不会，能再讲一下吗 | profile + tutor |
| 帮我再出两道题，然后顺便讲一下上一题为什么选 B | resource_generation |

## 6. Orchestrator 主流程设计

### 6.1 总体流程
`Orchestrator.run()` 保持统一入口，按以下顺序处理：
1. `RouterAgent.route(user_message)`
2. 如命中画像更新，则沿用现有 `ProfileAgent + ProfileService` 逻辑
3. 若 `response_mode == "none"`，表示本轮只有画像更新，不进入资源生成或 Tutor 分支：
   - 发完 `profile_updated` 后直接发 `done`
   - 不发 `agent_status`
   - 不发 `resource_card`
   - 不补发 tutor 文本回复
4. 若 `response_mode == resource_generation`，继续走现有 `Planner -> document -> quiz -> code`
5. 若 `response_mode == tutor`，进入 Tutor 分支

### 6.2 Tutor 分支行为
Tutor 分支的标准流程：
1. 发 `agent_status(TutorAgent, working, 正在辅导讲解)`
2. 组装答疑上下文
3. 调用 `TutorAgent.generate_reply(...)`
4. 将返回文本按现有 token 逻辑流式输出，同时在 `Orchestrator` 内用本轮局部缓冲区聚合完整 assistant 文本
5. 若文本成功输出完成，则由 `Orchestrator` 在流结束前调用现有 `ChatService.save_message(session_id, role="assistant", content=full_text)` 持久化完整回复
6. 若持久化成功，则发 `done`

补充约束：
- `tutor_mode == "clarification"` 不作为特殊控制流处理，仍按上述标准 Tutor 成功链路执行：输出 `agent_status -> token... -> done`，并在流结束后持久化为一条 assistant message

这里明确约束：
- 第一版的 Tutor 全文聚合与 assistant message 持久化都放在 `Orchestrator` 内完成，不放在 `api/chat.py` 额外二次处理
- `api/chat.py` 继续只负责保存 user message、创建 orchestrator、透传 orchestrator 产出的 SSE 事件
- `Orchestrator` 对 Tutor 分支需要区分“流式阶段异常”和“流式完成后的持久化异常”，以匹配 6.3 的失败语义

### 6.3 Tutor 分支失败语义
第一版统一采用与现有聊天主链路一致的简化失败策略：
- 若在 **首个 token 发出前** 发生异常：
  - 直接发 `error`
  - 不发 `done`
  - 不持久化 assistant message
  - 第一版统一由 `Orchestrator` 直接产出该 `error` 事件，不再把这类 Tutor 分支失败继续向上抛给 `api/chat.py` 二次转换；这样可保证失败责任边界单一，客户端最终只看到一次失败型 SSE 事件
- 若在 **部分 token 已发出后** 才发生异常：
  - 第一版视为不可完美补偿的流式失败
  - 服务端记录错误日志
  - 不再补发新的 `error` 或 `done`
  - 不持久化截断后的 assistant message
  - 前端按连接中断/流异常处理当前半条回答
  - 为避免现有 `api/chat.py` 外层异常兜底再次补发 `error`，`Orchestrator` 在该场景下必须在内部吞掉异常并结束流式生成器，不再继续向上抛出
- 若 token 全部发送完成，但最终 assistant message 持久化失败：
  - 仍发 `done`
  - 前端本轮视为成功结束
  - 服务端记录持久化失败日志
  - 不回滚已发送 token，也不补发新的失败型 SSE 事件

### 6.4 Tutor 分支明确不做的事
- 不发 `resource_card`
- 不新增 tutor 专属 SSE 事件
- 不修改现有 `resource_card` 协议
- 不改变多资源生成链路的行为

## 7. Tutor 上下文组装设计

### 7.1 上下文优先级
Tutor 获取上下文时，按下面优先级处理：
1. 当前用户消息中的显式线索
2. 当前会话最近资源（按 7.3 的唯一选择规则确定）
3. Wiki 补充上下文
4. 推断失败时的短澄清

当资源定位与答案提取都不可靠时，第一版优先短澄清，不强行用 Wiki 替代具体题目讲解；只有在问题本身是通用概念问答、且当前会话资源不足时，才优先走 Wiki 兜底。

### 7.2 上下文字段建议
第一版不单独创建复杂 Builder 类，先使用轻量上下文容器，包含：
- `topic`
- `profile`
- `recent_document`
- `recent_quiz`
- `recent_code`
- `wiki_context`
- `tutor_mode`（`explanation / follow_up / correction / clarification`）
- `quiz_answer_guess`（如果用户在答题）

### 7.3 当前会话最近资源的数据源与选取规则
第一版统一从当前 `session_id` 对应的 `generated_resources` 表读取上下文，不从聊天消息里的 `resource_card` 回放中二次推断，避免出现 SSE 展示层与持久化层不一致的问题。

资源选择按两层优先级执行：

#### 第一步：先确定资源类型优先级
- 若用户消息中包含显式线索，则按线索锁定主资源类型：
  - “这题 / 这道题 / 我选 A/B/C/D / 答案是不是 ...” → `quiz`
  - “这段代码 / 这行代码 / 运行结果为什么 ...” → `code`
  - “这个概念 / 这一段讲义 / 为什么会这样” → `document`
- 若没有显式线索，则按 `quiz > code > document` 的顺序尝试匹配最近资源

#### 第二步：再在该类型内选择最近资源
- 按当前 `session_id` 下对应资源类型的创建时间倒序选择第一条，作为“最近资源”
- 若主类型下无资源，则退回到下一优先类型继续按创建时间倒序选择
- 若三类资源都不存在，则进入 Wiki 兜底或澄清分支

#### quiz 内部定位规则
- 第一版默认只关联“最近一个 quiz 资源”
- 若该 quiz 资源内包含多道题，则**固定只取最后一题**作为当前纠错目标，不再使用“最后一组题”等并列表述
- “最后一题”按 quiz 文本中最后一个可识别题目块确定；题目块至少应包含 `question` 与 `answer` 线索
- 若无法从 recent quiz 中稳定定位出最后一题的题干与参考答案，则不进入判对错分支，而是先发一个很短的澄清问题

### 7.4 Quiz 纠错范围与判分输入规则
第一版的 quiz 纠错只支持**当前会话最近 quiz 中具备明确标准答案的客观题**，不支持开放问答题、主观简答题、编程题自动批改。

判分边界约束如下：
1. 只处理可进入白名单题型的题目：单选题、多选题、可直接字符串比对的填空题
2. 题型识别不依赖额外模型推理，只依赖 recent quiz 中可直接解析的结构化字段或固定文本标记：
   - 有 `options` 且参考答案为单个选项字母 → 单选题
   - 有 `options` 且参考答案为多个选项字母集合 → 多选题
   - 无 `options` 且存在明确短答案文本 → 填空题
   - 其余情况一律视为不可可靠判分，不进入自动纠错
3. 若最近 quiz 内容中能明确解析出题干、选项、参考答案与解析，则 Tutor 才进入纠错判断分支
4. 若最近 quiz 只有题目文本但缺少可识别参考答案，Tutor 不做“对/错”判定，只做基于题目内容的讲解与引导
5. 若用户答案无法可靠提取，Tutor 不猜测答案，而是先发一个很短的澄清问题
6. 若用户表达属于开放性自然语言理解，例如“我觉得是链式法则为什么”，但最近题目不是可直接比对的填空题，则默认退化为解释型答复，不进入自动判分

第一版建议的输入提取方式：
- `quiz_answer_guess`：从用户消息中提取并归一化后的答案表达
  - 单选题：提取单个大写字母，如 `A` / `B` / `C` / `D`
  - 多选题：提取多个大写字母，去重后按字母序排序，例如用户输入 `CA`、`A C`、`c,a` 都归一化为 `AC`
  - 填空题：提取去首尾空格后的字符串，并做大小写无关比较；若存在标点或助词差异但无法安全归一化，则视为不可可靠提取
- `tutor_mode == "correction"`：仅在“我选 B，对吗”“答案是不是 A”“我觉得应该选 C”这类明显判题请求时启用
- `recent_quiz`：需包含最近题目内容；若实现侧已能结构化出 `question / options / answer / explanation`，则优先使用结构化字段；否则 quiz 文本必须至少能按 7.5 中唯一固定协议稳定切分出最后一题的 `question / options / answer / explanation`
- “无法可靠提取”的判定标准：
  - 单选题未能提取出唯一选项字母
  - 多选题提取结果包含题目范围外字符，或无法唯一确定选项集合
  - 填空题答案长度过长、包含整句解释性文本，或与题目要求的短答案形式明显不匹配
  - 一旦命中以上任一情况，Tutor 直接短澄清，不进入自动判分

第一版的判分规则保持轻量：
- 单选题：答案全等才判定正确
- 多选题：答案集合完全一致才判定正确，先不做“部分正确”细分
- 填空题：仅在 recent quiz 中存在明确标准答案文本且可直接比对时才判定，否则退化为解释型答复

### 7.5 Quiz 文本切分前提
为保证第一版在非结构化 quiz 文本下仍可实现基础纠错，recent quiz 的内容格式至少需要满足以下最小约束之一：
1. 已存在结构化字段：`question / options / answer / explanation`
2. 或者自由文本中存在唯一固定标记协议，可切分出最后一题的四段信息，固定为：
   - `题目：...`
   - `选项：...`
   - `答案：...`
   - `解析：...`

该约束不是 Tutor 侧的临时兼容假设，而是第一版 quiz 资源与 Tutor 自动纠错之间的前置契约：
- 若实现侧选择结构化 quiz 资源，则 QuizAgent 或持久化层必须稳定提供 `question / options / answer / explanation`
- 若第一版继续输出自由文本 quiz，则 QuizAgent prompt 与对应单测必须共同锁定上述唯一固定文本协议，至少保证“最近一题”可被稳定切分
- 结合当前代码基线，`backend/app/agents/quiz_agent.py` 与 `backend/tests/test_agents/test_quiz_agent.py` 尚未提供该契约，因此在 Tutor 自动纠错实现前，必须先补齐上游协议收敛；否则第一版只能退化为解释型答复或短澄清
- 若上游 quiz 资源未满足上述任一契约，Tutor 不得进入自动判分，只能退化为解释型答复或短澄清

第一版实现只支持以上这一种固定文本协议，不要求兼容多种自由格式；如果 recent quiz 不满足上述任一约束，则 Tutor 不进入自动判分，只退化为解释型答复或短澄清。

## 8. TutorAgent 设计

### 8.1 职责边界
`TutorAgent` 只负责一件事：**基于已组装好的上下文生成中文答疑文本**。

不负责：
- 查询数据库
- 读取会话资源
- 决定 SSE 事件顺序
- 落库资源

### 8.2 输入建议
`TutorAgent.generate_reply(...)` 可接受：
- `user_message`
- `topic`
- `profile`
- `recent_document`
- `recent_quiz`
- `recent_code`
- `wiki_context`
- `tutor_mode`
- `quiz_answer_guess`

### 8.3 输出建议
返回单一中文文本字符串，由 Orchestrator 负责切 token 流式发送。

### 8.4 Prompt 约束
Tutor prompt 需要体现这些要求：
- 必须用中文回答
- 优先围绕当前会话资源解释
- 资源不足时再补 Wiki
- 先直接解释，再补一个简短引导问题
- 若是 quiz 纠错，需明确说明判断结果、原因与正确思路
- 不输出英文小节标题，不输出多余协议文本

## 9. 数据与存储设计

### 9.1 数据边界
第一版不新增 tutor 资源，不改 `generated_resources` 的资源类型集合。

保持现状：
- `document / quiz / code` 继续作为资源落库
- Tutor 回复不写入 `generated_resources`
- Tutor 输出的 `agent_status / token / done` 只作为 SSE 传输事件，不直接逐条持久化
- 在一次 Tutor 流式输出结束后，由现有聊天消息链路将最终聚合后的完整回复保存为一条 assistant chat message

### 9.2 持久化规则
- `agent_status`：仅用于前端展示当前执行阶段，不单独落库
- `token`：仅用于流式传输，不逐 token 落库
- `done`：仅表示本轮流式输出完成，不作为独立消息落库
- Tutor 最终正文：仅在完整文本已成功生成且流式阶段未中断时，才在流结束后由 `Orchestrator` 聚合为完整 assistant 回复，再按现有 chat message 方式持久化
- 若在首个 token 发出前报错：不写入 assistant message；由 `Orchestrator` 直接输出一次 `error` 事件，不发 `done`，且不再将该异常继续向 `api/chat.py` 外层传播，避免客户端收到重复失败型 SSE 事件
- 若在部分 token 已发出后流式中断：不生成 tutor 资源卡，不持久化截断后的 assistant message，也不补写半条回复；同时 `Orchestrator` 必须在内部结束流并吞掉异常，避免 `api/chat.py` 外层兜底再次补发 `error`
- 若流式 token 已全部发送，但最终 assistant message 持久化失败，第一版以“流式成功”为准：
  - 前端本轮仍视为回答成功结束
  - 服务端记录持久化失败日志，便于排查
  - 不回滚已发送 token，也不补发新的失败型 SSE 事件
  - 该场景作为可接受的一致性风险，在后续版本再补偿修复

### 9.3 为什么不新增 tutor 资源
- Tutor 回复本质上是对话过程，而不是可复用的独立学习资源卡
- 现在强行把 Tutor 变成资源，会让资源中心与聊天记录职责混淆
- 如果后续验证有价值沉淀点，再单独抽象“错题讲解卡”等新资源即可

## 10. SSE 设计

Tutor 第一版复用现有 chat SSE 机制。

### 10.1 事件顺序
Tutor 请求的理想事件顺序：
1. `agent_status`
2. `token` 若干
3. `done`

补充约束：
- 纯画像请求（`response_mode == "none"`）只允许输出 `profile_updated -> done`
- Tutor 请求成功时只允许输出 `agent_status -> token... -> done`
- `tutor_mode == "clarification"` 仍视为 Tutor 成功回复，不新增特殊事件序列，继续按 `agent_status -> token... -> done` 输出
- Tutor 请求失败且发生在首个 token 前时，只输出 `agent_status -> error`
- Tutor 请求若在部分 token 已发出后中断，第一版不再补发 `error` 或 `done`
- 为满足上一条约束，部分 token 后失败必须在 `Orchestrator` 内部被记录并截断流，不再继续向 `api/chat.py` 外层传播；否则现有 API 兜底逻辑会再次补发 `error`，与本设计冲突

### 10.2 不新增的协议
第一版不新增：
- `tutor_card`
- `tutor_context`
- `tutor_done`
- 其他 tutor 专属事件

这样 API 层无需引入新 SSE 编码逻辑。

## 11. 测试设计

### 11.1 TutorAgent 单测
新增 `backend/tests/test_agents/test_tutor_agent.py`，覆盖：
- prompt 包含用户问题、资源上下文、Wiki 上下文
- prompt 包含“中文解释 + 简短引导”要求
- quiz 纠错模式下 prompt 包含用户答案与题目内容
- 当 `tutor_mode == "correction"` 且 recent quiz 可稳定解析时，prompt 明确要求输出“判断结果 + 原因 + 正确思路”
- 返回文本结构符合预期

### 11.2 Orchestrator 单测
扩展 `backend/tests/test_agents/test_orchestrator.py`，覆盖：
- 纯画像请求在 `profile_updated` 后直接 `done`
- Tutor 请求事件顺序为 `agent_status -> token... -> done`
- Tutor 请求不产生 `resource_card`
- Tutor 请求在首个 token 前失败时，事件顺序为 `agent_status -> error`
- Tutor 请求在部分 token 发出后中断时，不再补发 `error` 或 `done`，且 `Orchestrator.run()` 不再继续向外抛出异常
- 有会话资源时优先把资源内容传给 TutorAgent
- 无会话资源时：
  - 通用概念问答允许回退到 Wiki
  - 题目定位失败时优先返回短澄清
- quiz 纠错请求只针对当前会话最近 quiz
- 若 recent quiz 不满足 7.5 的固定协议或缺少标准答案，则不进入自动判分分支

### 11.3 Chat API SSE 测试
扩展 `backend/tests/test_api/test_chat_api.py`，覆盖：
- Tutor 请求返回 `text/event-stream`
- 成功响应中包含 `agent_status`、`token`、`done`
- 不包含 `resource_card`
- 最后一个事件为 `done`
- 纯画像请求只返回 `profile_updated` 与 `done`
- Tutor 首 token 前失败时，SSE 最后一个事件为 `error`
- Tutor 部分 token 后中断时，响应流中不存在补发的 `error` 或 `done`，从而验证 API 外层未再次补发失败事件
- Tutor 成功流式完成但 assistant message 持久化失败时，SSE 仍以 `done` 结束

## 12. 风险与后续演进

### 12.1 当前可接受风险
- 第一版的“最近资源匹配”是启发式规则，复杂会话中可能不够精确
- quiz 纠错只支持最近相关 quiz，覆盖范围有限
- Orchestrator 继续承担一部分上下文组装责任，后续可能需要拆分

### 12.2 后续演进方向
本版完成后，可以自然扩展到：
- 更精确的题号/题目定位
- 独立 `TutorContextBuilder`
- Tutor 与学习路径联动
- 高价值 Tutor 输出沉淀为新资源卡
- 更细粒度的来源引用与解释定位

## 13. 结论

本设计选择以最小改动落地 Tutor 第一版，核心原则是：
- 保持资源生成链路稳定
- 将 Tutor 作为独立答疑分支接入
- 优先复用当前会话资源，再按需使用 Wiki
- 复用现有 SSE 流式能力
- 不过早引入 tutor 资源协议或复杂状态机

这能在当前多资源学习包闭环基础上，最快补齐“生成 + 讲解 + 纠错”的学习体验闭环，为后续前端联调与更强教学能力打下基础。
