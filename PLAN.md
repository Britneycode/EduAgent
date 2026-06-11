# EduAgent - 个性化多 Agent 学习系统架构设计

## 一、系统定位与核心理念

### 1.1 一句话定义

**EduAgent** 是一个以 **LLM Wiki（知识中枢）** 为核心，通过 **多 Agent 协同** 为高校学生提供个性化、多模态学习资源生成与智能辅导的系统。

### 1.2 核心理念：LLM Wiki 知识中枢

```
传统方式：学生 → 搜索资源 → 自己筛选 → 学习
EduAgent：学生 → 对话 → Agent 协同 → 个性化资源自动生成 → 学习
                              ↑
                         LLM Wiki（知识中枢）
                     RAG 检索 + Wiki 式组织 + 动态扩展
```

**LLM Wiki 不是一个简单的文档库**，它是：
- **结构化知识图谱**：课程知识按章节→知识点→概念三级组织，带依赖关系
- **RAG 检索层**：向量化索引，Agent 可按语义检索相关知识
- **Wiki 式协作**：Agent 生成的内容可回写到知识库，持续积累
- **所有 Agent 的共享大脑**：统一知识源，避免各 Agent 各自为政

### 1.3 切入课程：人工智能导论

选择理由：
- 与赛题主题高度契合，评委易产生认同感
- 知识体系清晰：搜索/推理/学习/感知四大板块
- 天然适合多模态：算法可视化、模型动画、代码实操
- 代码类实操案例丰富：Python ML/DL 生态成熟

---

## 二、技术架构总览

### 2.1 技术选型

| 层级 | 技术 | 理由 |
|------|------|------|
| **前端** | Next.js 15 + React 19 + TypeScript | SSR/流式渲染、AI 产品最佳实践 |
| **UI 框架** | Tailwind CSS + shadcn/ui | 高度可定制，适配 DESIGN.md 的 Claude 风格 |
| **后端** | Python 3.12 + FastAPI | AI/ML 生态最好，LangChain/LangGraph 原生支持 |
| **Agent 框架** | LangGraph | 多 Agent 编排、状态管理、可观测性 |
| **LLM 提供商** | 讯飞星火（主） + DeepSeek（辅） | 赛题要求使用科大讯飞工具 |
| **向量数据库** | Chroma（MVP）→ Milvus（生产） | RAG 检索，知识库向量化。MVP 阶段用 Chroma（嵌入式单进程，零基础设施），生产环境按需切换 Milvus |
| **关系数据库** | PostgreSQL | 用户画像、学习记录、元数据 |
| **缓存** | Redis | 会话状态、热点缓存 |
| **对象存储** | MinIO | 生成的 PPT/视频/文档存储 |
| **实时通信** | SSE（主）+ WebSocket（预留） | SSE 用于 Agent 流式输出（POST + StreamingResponse）；WebSocket 预留给后续多用户实时通知与协作场景 |

### 2.2 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js 15)                       │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌────────────────────┐  │
│  │  对话界面  │ │ 学习路径   │ │ 资源中心   │ │  学习画像仪表盘    │  │
│  │ (流式输出) │ │ (可视化)   │ │ (多模态)   │ │  (雷达图/进度)    │  │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └────────┬───────────┘  │
│        └─────────────┼─────────────┼────────────────┘              │
│                      │  REST + WebSocket + SSE                      │
└──────────────────────┼──────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      API Gateway (FastAPI)                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Auth API │ │ Chat API │ │ Resource │ │ Profile  │ │ Path API │  │
│  │          │ │ (SSE流式) │ │   API    │ │   API    │ │          │  │
│  └──────────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│                    └────────────┼────────────┼────────────┘         │
│                                │                                    │
│                                ▼                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Agent Orchestrator (LangGraph)                  │   │
│  │                                                              │   │
│  │   ┌─────────┐    ┌──────────┐    ┌──────────────────────┐   │   │
│  │   │ Router  │───→│ Planner  │───→│ Agent 调度与编排      │   │   │
│  │   │ Agent   │    │ Agent    │    │ (并行/串行/条件分支)   │   │   │
│  │   └─────────┘    └──────────┘    └──────────┬───────────┘   │   │
│  │                                             │               │   │
│  │         ┌───────────────┬───────────────┬───┴────────┐      │   │
│  │         ▼               ▼               ▼            ▼      │   │
│  │   ┌──────────┐   ┌──────────┐   ┌──────────┐ ┌──────────┐  │   │
│  │   │ 画像构建 │   │ 资源生成 │   │ 路径规划 │ │ 智能辅导 │  │   │
│  │   │  Agent   │   │ Agent群  │   │  Agent   │ │  Agent   │  │   │
│  │   └────┬─────┘   └────┬─────┘   └────┬─────┘ └────┬─────┘  │   │
│  │        └──────────────┼──────────────┼────────────┘         │   │
│  │                       │              │                      │   │
│  └───────────────────────┼──────────────┼──────────────────────┘   │
│                          ▼              ▼                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   LLM Wiki（知识中枢）                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │   │
│  │  │  知识图谱层   │  │  RAG 检索层  │  │  Wiki 内容管理层  │  │   │
│  │  │ (章节→知识点  │  │ (向量索引 +  │  │ (版本管理/协作   │  │   │
│  │  │  →概念依赖)   │  │  语义搜索)   │  │  编辑/回写)      │  │   │
│  │  └──────────────┘  └──────────────┘  └───────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└──────────────────────────────────────────────────────────────────────┘
                       │              │              │
                       ▼              ▼              ▼
              ┌──────────────┐ ┌───────────┐ ┌─────────────┐
              │  PostgreSQL  │ │   Redis   │ │    MinIO    │
              │ (元数据/画像 │ │ (缓存/    │ │ (生成的资源 │
              │  /学习记录)  │ │  会话状态) │ │  文件存储)  │
              └──────────────┘ └───────────┘ └─────────────┘
              ┌──────────────┐
              │ Milvus/Chroma│
              │ (向量检索)    │
              └──────────────┘
```

---

## 三、多 Agent 架构设计（核心）

### 3.1 Agent 角色全景

系统包含 **2 个核心编排 Agent** + **6 个专业 Agent**，满足赛题"多智能体协同"要求：

```
                    ┌───────────────────┐
                    │   Router Agent    │  意图识别与路由
                    │   (入口调度器)     │  判断用户需求类型
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │  Planner Agent    │  任务分解与编排
                    │   (任务规划器)     │  拆解为子任务分配给专业 Agent
                    └────────┬──────────┘
                             │
          ┌──────────┬───────┼───────┬──────────┬──────────┐
          ▼          ▼       ▼       ▼          ▼          ▼
    ┌──────────┐┌────────┐┌──────┐┌────────┐┌────────┐┌────────┐
    │ Profile  ││ Doc    ││ Quiz ││ Code   ││ Media  ││ Tutor  │
    │ Agent    ││ Agent  ││Agent ││ Agent  ││ Agent  ││ Agent  │
    │ 画像构建 ││ 文档   ││ 题库 ││ 代码   ││ 多媒体 ││ 辅导   │
    │          ││ 生成   ││ 生成 ││ 实操   ││ 生成   ││ 答疑   │
    └──────────┘└────────┘└──────┘└────────┘└────────┘└────────┘
```

### 3.2 各 Agent 详细设计

#### Agent 0: Router Agent（路由分发）

```yaml
名称: RouterAgent
职责: 理解用户意图，路由到正确的处理流程
输入: 用户消息 + 会话上下文
输出: 路由决策 (intent + 参数)
LLM: 讯飞星火 Lite（快速推理）

路由规则:
  - "我是大三学生..." → ProfileAgent (画像构建/更新)
  - "帮我生成一份...笔记/PPT" → Planner → DocAgent
  - "出几道...练习题" → Planner → QuizAgent
  - "给我写一个...代码示例" → Planner → CodeAgent
  - "我不理解..." → TutorAgent (智能辅导)
  - "帮我规划学习路径" → Planner → PathPlanning
  - 复合请求 → Planner (多 Agent 协同)
```

#### Agent 1: Profile Agent（画像构建）⭐ 必选功能

```yaml
名称: ProfileAgent
职责: 通过对话自动构建/更新 6+ 维度学生画像
输入: 对话内容 + 历史画像
输出: 结构化学生画像 JSON

画像维度 (≥6个):
  1. 知识基础: 各知识模块掌握程度 (0-100)
  2. 认知风格: 视觉型/听觉型/读写型/动手型
  3. 学习目标: 考试/科研/竞赛/就业
  4. 易错点偏好: 高频错误知识点标记
  5. 学习节奏: 快速/适中/深入
  6. 兴趣方向: 偏好的子领域
  7. 编程能力: Python/数学/算法基础评估
  8. 时间投入: 每周可用学习时间

对话式构建流程:
  1. 首次对话: 引导性提问获取基础信息
  2. 学习过程: 从交互行为隐式更新画像
  3. 测试反馈: 根据答题情况调整知识掌握度
  4. 主动更新: 学生可随时告知变化
```

#### Agent 2: Doc Agent（文档资源生成）⭐ 必选功能

```yaml
名称: DocAgent
职责: 生成个性化学习文档资源
输入: 知识点 + 学生画像 + 资源类型
输出: Markdown 文档 / 思维导图 / PPT

生成的资源类型:
  ① 课程讲解文档: Markdown 格式，深度/广度根据画像调整
  ② 知识点思维导图: Mermaid/Markmap 格式，可交互展示
  ③ 拓展阅读材料: 根据学习目标推荐方向

特性:
  - 根据"知识基础"调整内容深度
  - 根据"认知风格"调整呈现方式（图多/文多/示例多）
  - 生成内容回写 LLM Wiki，供后续检索复用
```

#### Agent 3: Quiz Agent（题库生成）⭐ 必选功能

```yaml
名称: QuizAgent
职责: 生成个性化练习题目
输入: 知识点范围 + 难度要求 + 学生画像
输出: 结构化题目 JSON (题目/选项/答案/解析)

题目类型:
  ① 选择题: 单选/多选
  ② 填空题: 关键概念
  ③ 判断题: 易混淆概念辨析
  ④ 简答题: 原理阐述
  ⑤ 编程题: 代码实现（关联 CodeAgent）

特性:
  - 根据"易错点偏好"针对性出题
  - 难度自适应：答对 → 提升难度，答错 → 巩固基础
  - 自动生成详细解析
  - 答题结果反馈给 ProfileAgent 更新画像
```

#### Agent 4: Code Agent（代码实操）⭐ 必选功能

```yaml
名称: CodeAgent
职责: 生成可运行的代码实操案例
输入: 知识点/算法名 + 学生编程能力
输出: 完整代码 + 注释 + 运行说明

生成内容:
  ① 算法实现: 如 A*搜索、神经网络前向传播
  ② 实验项目: 完整的 ML 实验代码（数据→训练→评估）
  ③ 代码填空: 关键部分挖空让学生补全
  ④ Debug 练习: 包含 Bug 的代码让学生修复

特性:
  - 根据"编程能力"调整代码复杂度
  - 所有代码保证可运行（Python + 标准 ML 库）
  - 渐进式学习：从简单到复杂的代码序列
```

#### Agent 5: Media Agent（多媒体生成）⭐ 必选功能

```yaml
名称: MediaAgent
职责: 生成多模态教学内容
输入: 知识点 + 呈现形式需求
输出: 动画/视频/图解

生成内容:
  ① 算法可视化动画: 用 Manim/D3.js 生成算法执行过程动画
  ② 概念图解: 用 Mermaid/SVG 生成流程图、架构图
  ③ PPT 幻灯片: 用 python-pptx 生成结构化 PPT
  ④ 教学短视频: 图文合成解说视频（讯飞 TTS + 图片序列）

技术方案:
  - Manim: 数学/算法动画生成
  - python-pptx: PPT 自动生成
  - 讯飞 TTS: 文字转语音旁白
  - FFmpeg: 音视频合成
  - Mermaid: 图表/流程图
```

#### Agent 6: Tutor Agent（智能辅导）⭐ 加分项

```yaml
名称: TutorAgent
职责: 即时答疑、学习引导
输入: 学生问题 + 上下文 + 画像
输出: 多模态解答（文字 + 图解 + 代码示例）

模式:
  ① 直接解答: 明确问题给出详细解释
  ② 苏格拉底式引导: 通过反问引导学生思考
  ③ 多模态解答: 文字解释 + 图解 + 代码示例组合

特性:
  - 从 LLM Wiki 检索相关知识确保准确性
  - 根据画像中的"认知风格"选择解答方式
  - 防幻觉: RAG + 知识验证双重保障
  - 解答内容可沉淀为 FAQ 写入 Wiki
```

#### Planner Agent 详细设计补充

```yaml
名称: PlannerAgent
职责: 将复合任务分解为子任务，编排多 Agent 执行
输入: Router 判定为复合任务的请求 + 用户画像
输出: 执行计划 (任务列表 + 依赖关系 + 执行策略)

任务分解规则:
  1. 识别请求中的多个子需求（如"复习+出题+写代码"）
  2. 每个子需求映射到对应 Agent
  3. 标注子任务间的依赖关系（如 Profile 必须先于其他 Agent）

执行策略:
  串行优先: ProfileAgent 必须先完成（其他 Agent 依赖画像数据）
  可并行组: DocAgent / QuizAgent / CodeAgent 无相互依赖，可并行执行
  按需触发: MediaAgent 仅在用户显式请求或画像认知风格为"视觉型"时触发
  超时控制: 单个 Agent 超时 30 秒，整体编排超时 120 秒

错误回退:
  - 某个 Agent 失败不阻塞其他 Agent 继续执行
  - 失败 Agent 的结果标记为"生成失败"，返回已成功的其他资源
  - 画像更新失败时保留旧画像，继续走通用参数生成
  - 所有 Agent 全部失败时返回友好中文错误提示

输出汇总:
  - 收集所有 Agent 的生成结果
  - 按类型排序：文档 → 题目 → 代码 → 多媒体
  - 组装为完整学习资源包，通过 SSE 分段推送
```

### 3.3 Agent 协同工作流 (LangGraph)

```
用户消息
    │
    ▼
┌─────────┐     意图识别
│ Router  │────────────────────────────────────┐
│ Agent   │                                    │
└────┬────┘                                    │
     │                                         │
     │  复合任务                    简单任务     │
     ▼                                         ▼
┌─────────┐                              直接路由到
│ Planner │                              单个 Agent
│ Agent   │
└────┬────┘
     │ 任务分解
     │
     ├──→ Task 1: ProfileAgent.update_profile()
     │         │
     │         ▼ (画像数据)
     │
     ├──→ Task 2: DocAgent.generate_notes()  ←── LLM Wiki 检索
     │         │
     │         ▼ (文档) ──→ 回写 LLM Wiki
     │
     ├──→ Task 3: QuizAgent.generate_quiz()  ←── LLM Wiki 检索
     │         │
     │         ▼ (题目)
     │
     ├──→ Task 4: CodeAgent.generate_code()
     │         │
     │         ▼ (代码)
     │
     └──→ Task 5: MediaAgent.generate_visual()
              │
              ▼ (多媒体)
              │
     ┌────────┘
     ▼
┌─────────┐
│ Planner │  汇总所有 Agent 输出
│ (汇总)  │  组装为完整学习资源包
└────┬────┘
     │
     ▼
  返回前端（流式输出各部分结果）
```

**并行与串行策略：**
- **并行**：DocAgent + QuizAgent + CodeAgent 可并行（独立任务）
- **串行**：ProfileAgent 先执行 → 其他 Agent 依赖画像数据
- **条件**：MediaAgent 可根据用户请求选择性执行

---

## 四、LLM Wiki 知识中枢设计

### 4.1 知识组织结构

```
LLM Wiki
├── 课程: 人工智能导论
│   ├── 第1章: 人工智能概述
│   │   ├── 1.1 AI 的定义与历史
│   │   │   ├── 概念: 图灵测试
│   │   │   ├── 概念: 达特茅斯会议
│   │   │   └── 概念: AI 三大学派
│   │   ├── 1.2 AI 的应用领域
│   │   └── 1.3 AI 的发展趋势
│   ├── 第2章: 知识表示与推理
│   │   ├── 2.1 命题逻辑
│   │   ├── 2.2 谓词逻辑
│   │   └── 2.3 知识图谱
│   ├── 第3章: 搜索策略
│   │   ├── 3.1 无信息搜索 (BFS/DFS)
│   │   ├── 3.2 启发式搜索 (A*)
│   │   └── 3.3 对抗搜索 (Minimax)
│   ├── 第4章: 机器学习基础
│   │   ├── 4.1 监督学习
│   │   ├── 4.2 无监督学习
│   │   └── 4.3 强化学习
│   ├── 第5章: 深度学习
│   │   ├── 5.1 神经网络基础
│   │   ├── 5.2 CNN
│   │   └── 5.3 RNN/Transformer
│   └── 第6章: 自然语言处理
│       ├── 6.1 文本表示
│       ├── 6.2 语言模型
│       └── 6.3 大语言模型
│
├── 知识依赖图 (DAG)
│   ├── "梯度下降" depends_on ["微积分", "线性代数"]
│   ├── "反向传播" depends_on ["梯度下降", "链式法则"]
│   ├── "CNN" depends_on ["神经网络基础", "卷积运算"]
│   └── ...
│
└── 生成内容库 (Agent 回写)
    ├── 学习笔记/
    ├── 练习题库/
    ├── 代码案例/
    └── FAQ 问答对/
```

### 4.2 技术实现

```
┌──────────────────────────────────────────────────┐
│                    LLM Wiki                       │
│                                                   │
│  ┌────────────────┐    ┌───────────────────────┐  │
│  │  文档存储层     │    │    向量索引层          │  │
│  │  (PostgreSQL)  │    │    (Milvus/Chroma)    │  │
│  │                │    │                       │  │
│  │  - 章节结构    │◄──►│  - 文档分块 Embedding │  │
│  │  - 知识点元数据│    │  - 语义相似度检索     │  │
│  │  - 版本历史    │    │  - Hybrid Search      │  │
│  │  - 依赖关系    │    │    (向量 + 关键词)    │  │
│  └────────────────┘    └───────────────────────┘  │
│                                                   │
│  ┌────────────────┐    ┌───────────────────────┐  │
│  │  知识图谱层     │    │    内容管理层          │  │
│  │ (JSON + JSONB) │    │                       │  │
│  │                │    │  - 初始知识导入        │  │
│  │  - 概念节点    │    │  - Agent 生成内容回写  │  │
│  │  - 依赖边      │    │  - 内容版本管理       │  │
│  │  - 先修关系    │    │  - 质量审核（LLM）    │  │
│  └────────────────┘    └───────────────────────┘  │
│                                                   │
│  注：知识图谱层 MVP 阶段使用 JSON 文件 +           │
│  PostgreSQL JSONB 字段存储 DAG 依赖关系，           │
│  满足课程级别的知识点规模（数百节点）。              │
│  如后续知识规模超过万级节点，可引入 Neo4j。          │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │                 API 接口                     │  │
│  │  search(query) → 语义检索相关知识片段        │  │
│  │  get_prerequisites(topic) → 前置知识列表     │  │
│  │  get_knowledge_tree(chapter) → 知识树结构    │  │
│  │  write_back(content, source_agent) → 回写    │  │
│  │  get_related(topic) → 关联知识推荐           │  │
│  └─────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### 4.3 RAG 检索流程

```
用户问题: "反向传播算法的数学原理是什么？"
    │
    ▼
┌──────────────────┐
│ 1. Query 改写    │  LLM 将口语化问题改写为检索 query
│    + 扩展       │  "反向传播 数学推导 链式法则 梯度计算"
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. Hybrid Search │  向量相似度 + BM25 关键词 混合检索
│    Top-K 召回    │  召回 8-10 个相关文档块
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 3. Rerank 重排   │  用 Cross-Encoder 对召回结果重排序
│                  │  筛选 Top-3 最相关
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. 注入 Context  │  将检索结果注入 Agent 的 System Prompt
│    + 生成响应    │  Agent 基于知识库内容 + 自身能力生成回答
└──────────────────┘
```

---

## 五、数据库设计

### 5.1 核心表结构

```sql
-- 1. 用户表
CREATE TABLE users (
    id          BIGSERIAL PRIMARY KEY,
    username    VARCHAR(50) UNIQUE NOT NULL,
    email       VARCHAR(100),
    password    VARCHAR(255) NOT NULL,
    avatar_url  VARCHAR(500),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 学生画像表
CREATE TABLE student_profiles (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id),
    
    -- 6+ 维度画像数据 (JSONB 灵活存储)
    knowledge_base  JSONB DEFAULT '{}',  -- 知识基础: {"搜索算法": 75, "机器学习": 40, ...}
    cognitive_style VARCHAR(20),          -- 认知风格: visual/auditory/reading/kinesthetic
    learning_goal   VARCHAR(20),          -- 学习目标: exam/research/competition/career
    weak_points     JSONB DEFAULT '[]',  -- 易错点: ["梯度消失", "过拟合判断", ...]
    learning_pace   VARCHAR(20),          -- 学习节奏: fast/moderate/deep
    interest_areas  JSONB DEFAULT '[]',  -- 兴趣方向: ["NLP", "CV", ...]
    coding_level    VARCHAR(20),          -- 编程能力: beginner/intermediate/advanced
    weekly_hours    INT,                  -- 每周学习时间
    
    -- 元数据
    profile_version INT DEFAULT 1,        -- 画像版本号（每次更新+1）
    last_updated    TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 对话会话表
CREATE TABLE chat_sessions (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users(id),
    title       VARCHAR(200),
    context     JSONB DEFAULT '{}',       -- 会话上下文
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 4. 对话消息表
CREATE TABLE chat_messages (
    id          BIGSERIAL PRIMARY KEY,
    session_id  BIGINT REFERENCES chat_sessions(id),
    role        VARCHAR(20) NOT NULL,     -- user/assistant/system
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',       -- Agent 名称、工具调用等
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 5. 生成资源表
CREATE TABLE generated_resources (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id),
    session_id      BIGINT REFERENCES chat_sessions(id),
    
    resource_type   VARCHAR(50) NOT NULL,  -- document/quiz/code/ppt/video/mindmap
    title           VARCHAR(200) NOT NULL,
    content         TEXT,                   -- 文本内容(Markdown)
    file_url        VARCHAR(500),           -- 文件存储 URL (PPT/视频)
    knowledge_point VARCHAR(200),           -- 关联知识点
    
    agent_name      VARCHAR(50),            -- 生成此资源的 Agent
    metadata        JSONB DEFAULT '{}',     -- 额外元数据
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 6. 学习路径表
CREATE TABLE learning_paths (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users(id),
    title       VARCHAR(200),
    description TEXT,
    status      VARCHAR(20) DEFAULT 'active',  -- active/completed/paused
    path_data   JSONB NOT NULL,                 -- 路径节点结构
    progress    JSONB DEFAULT '{}',             -- 各节点完成状态
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 7. 学习行为记录表（学习效果评估用）
CREATE TABLE learning_activities (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id),
    activity_type   VARCHAR(50),       -- quiz_attempt/resource_view/code_run/chat
    knowledge_point VARCHAR(200),
    result          JSONB DEFAULT '{}', -- 答题正确率、用时等
    duration_sec    INT,                -- 学习时长(秒)
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Wiki 知识条目表
CREATE TABLE wiki_entries (
    id              BIGSERIAL PRIMARY KEY,
    chapter         VARCHAR(100),       -- 所属章节
    section         VARCHAR(100),       -- 所属小节
    title           VARCHAR(200) NOT NULL,
    content         TEXT NOT NULL,
    content_type    VARCHAR(50),        -- original/agent_generated/user_contributed
    source_agent    VARCHAR(50),        -- 生成来源 Agent
    prerequisites   JSONB DEFAULT '[]', -- 前置知识ID列表
    tags            JSONB DEFAULT '[]',
    version         INT DEFAULT 1,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.2 关键索引

```sql
-- 高频查询索引
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX idx_student_profiles_user_id ON student_profiles(user_id);
CREATE INDEX idx_generated_resources_user_id ON generated_resources(user_id);
CREATE INDEX idx_generated_resources_session_id ON generated_resources(session_id);
CREATE INDEX idx_generated_resources_type ON generated_resources(resource_type);
CREATE INDEX idx_learning_activities_user_id ON learning_activities(user_id);
CREATE INDEX idx_learning_activities_knowledge ON learning_activities(knowledge_point);
CREATE INDEX idx_learning_activities_created ON learning_activities(created_at);
CREATE INDEX idx_wiki_entries_chapter ON wiki_entries(chapter);
CREATE INDEX idx_learning_paths_user_id ON learning_paths(user_id);
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
```

### 6.1 页面结构

遵循 DESIGN.md 中的 Claude 风格设计系统（暖色调、衬线标题、羊皮纸底色）。

```
Next.js App Router 页面结构:

app/
├── (auth)/
│   ├── login/page.tsx          # 登录
│   └── register/page.tsx       # 注册
│
├── (main)/
│   ├── layout.tsx              # 主布局（侧边栏 + 内容区）
│   │
│   ├── chat/
│   │   └── [sessionId]/
│   │       └── page.tsx        # 💬 AI 对话界面（核心）
│   │                           #    流式输出、多模态内容卡片
│   │
│   ├── profile/
│   │   └── page.tsx            # 👤 学习画像仪表盘
│   │                           #    雷达图、维度详情、更新历史
│   │
│   ├── resources/
│   │   ├── page.tsx            # 📚 资源中心（所有生成的资源）
│   │   └── [resourceId]/
│   │       └── page.tsx        # 📄 资源详情（文档/题目/代码）
│   │
│   ├── path/
│   │   └── page.tsx            # 🗺️ 学习路径（可视化节点图）
│   │
│   └── wiki/
│       ├── page.tsx            # 📖 知识 Wiki 浏览
│       └── [entryId]/
│           └── page.tsx        # 📝 Wiki 条目详情
│
└── api/                        # Next.js API Routes (BFF 代理)
```

### 6.2 核心交互设计

**对话界面（核心页面）：**

```
┌─────────────────────────────────────────────────────────┐
│  ☰  EduAgent                              👤 用户名     │  ← 导航栏
├────────────┬────────────────────────────────────────────┤
│            │                                            │
│  会话列表   │     AI 学习助手                             │
│            │                                            │
│  ● 新对话   │  ┌──────────────────────────────────────┐  │
│            │  │ 🤖 你好！我是你的 AI 学习助手。       │  │
│  昨天       │  │   请告诉我你的学习需求...            │  │
│  ├ 机器学习 │  └──────────────────────────────────────┘  │
│  └ A*算法   │                                            │
│            │  ┌──────────────────────────────────────┐  │
│  上周       │  │ 👤 帮我复习反向传播算法              │  │
│  ├ 深度学习 │  └──────────────────────────────────────┘  │
│  └ ...     │                                            │
│            │  ┌──────────────────────────────────────┐  │
│            │  │ 🤖 好的，正在为你生成学习资源...      │  │
│            │  │                                      │  │
│            │  │ ┌──── 📄 学习笔记 ──────────────┐    │  │
│            │  │ │ # 反向传播算法                 │    │  │
│            │  │ │ ## 1. 核心思想               │    │  │
│            │  │ │ 反向传播是...                 │    │  │
│            │  │ └───────────────────────────────┘    │  │
│            │  │                                      │  │
│            │  │ ┌──── 🧩 练习题 ──────────────┐     │  │
│            │  │ │ Q1: 反向传播中链式法则的     │     │  │
│            │  │ │     作用是？                  │     │  │
│            │  │ │ A. ...  B. ...  C. ...       │     │  │
│            │  │ └──────────────────────────────┘     │  │
│            │  │                                      │  │
│            │  │ ┌──── 💻 代码示例 ──────────────┐    │  │
│            │  │ │ import numpy as np            │    │  │
│            │  │ │ def backprop(x, y, w):        │    │  │
│            │  │ │     ...                       │    │  │
│            │  │ └───────────────────────────────┘    │  │
│            │  └──────────────────────────────────────┘  │
│            │                                            │
│            │  ┌────────────────────────────────────┐    │
│            │  │ 💬 输入你的学习需求...        [发送] │    │
│            │  └────────────────────────────────────┘    │
├────────────┴────────────────────────────────────────────┤
```

**关键交互特性：**
- **流式输出**：Agent 响应实时流式呈现，不白屏等待
- **多模态卡片**：不同类型资源（文档/题目/代码/图表）用不同卡片样式展示
- **资源可折叠**：长内容可折叠/展开，不占满屏幕
- **一键保存**：每个生成的资源可一键保存到资源中心
- **进度追踪**：多 Agent 并行工作时，显示各 Agent 执行状态

---

## 七、项目目录结构

```
EduAgent/
├── README.md                        # 项目说明
├── DESIGN.md                        # UI 设计规范（已有）
├── PLAN.md                          # 本架构设计文档
├── docker-compose.yml               # 一键启动所有服务
│
├── backend/                         # 🐍 Python 后端
│   ├── pyproject.toml               # 项目依赖 (uv/poetry)
│   ├── alembic/                     # 数据库迁移
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口
│   │   ├── config.py                # 配置管理
│   │   │
│   │   ├── api/                     # API 路由
│   │   │   ├── auth.py              # 认证接口
│   │   │   ├── chat.py              # 对话接口 (SSE 流式)
│   │   │   ├── resources.py         # 资源管理接口
│   │   │   ├── profile.py           # 画像接口
│   │   │   ├── path.py              # 学习路径接口
│   │   │   └── wiki.py              # Wiki 接口
│   │   │
│   │   ├── agents/                  # 🤖 多 Agent 系统
│   │   │   ├── orchestrator.py      # LangGraph 编排器
│   │   │   ├── router_agent.py      # 路由 Agent
│   │   │   ├── planner_agent.py     # 规划 Agent
│   │   │   ├── profile_agent.py     # 画像构建 Agent
│   │   │   ├── doc_agent.py         # 文档生成 Agent
│   │   │   ├── quiz_agent.py        # 题库生成 Agent
│   │   │   ├── code_agent.py        # 代码实操 Agent
│   │   │   ├── media_agent.py       # 多媒体生成 Agent
│   │   │   ├── tutor_agent.py       # 智能辅导 Agent
│   │   │   └── tools/               # Agent 工具集
│   │   │       ├── wiki_search.py   # Wiki 检索工具
│   │   │       ├── code_runner.py   # 代码沙箱执行
│   │   │       ├── ppt_generator.py # PPT 生成工具
│   │   │       └── chart_maker.py   # 图表生成工具
│   │   │
│   │   ├── wiki/                    # 📖 LLM Wiki 知识中枢
│   │   │   ├── knowledge_base.py    # 知识库管理
│   │   │   ├── rag_engine.py        # RAG 检索引擎
│   │   │   ├── embeddings.py        # 向量化服务
│   │   │   ├── graph.py             # 知识图谱
│   │   │   └── ingestion.py         # 知识导入管道
│   │   │
│   │   ├── models/                  # 数据模型
│   │   │   ├── user.py
│   │   │   ├── profile.py
│   │   │   ├── chat.py
│   │   │   ├── resource.py
│   │   │   └── wiki.py
│   │   │
│   │   ├── services/                # 业务服务
│   │   │   ├── auth_service.py
│   │   │   ├── profile_service.py
│   │   │   ├── resource_service.py
│   │   │   └── path_service.py
│   │   │
│   │   └── core/                    # 基础设施
│   │       ├── database.py          # DB 连接
│   │       ├── redis.py             # Redis 客户端
│   │       ├── storage.py           # MinIO 文件存储
│   │       ├── llm.py               # LLM 客户端封装
│   │       └── security.py          # 安全/认证
│   │
│   ├── knowledge/                   # 📚 初始知识库数据
│   │   ├── ai_intro/                # 人工智能导论课程
│   │   │   ├── chapter1_overview.md
│   │   │   ├── chapter2_knowledge_representation.md
│   │   │   ├── chapter3_search.md
│   │   │   ├── chapter4_machine_learning.md
│   │   │   ├── chapter5_deep_learning.md
│   │   │   ├── chapter6_nlp.md
│   │   │   └── metadata.json        # 课程结构元数据
│   │   └── knowledge_graph.json     # 知识依赖图
│   │
│   └── tests/
│       ├── test_agents/
│       ├── test_wiki/
│       └── test_api/
│
├── frontend/                        # ⚛️ Next.js 前端
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts           # Claude 风格主题配置
│   │
│   ├── app/                         # App Router
│   │   ├── layout.tsx               # 全局布局
│   │   ├── (auth)/                  # 认证页面组
│   │   ├── (main)/                  # 主功能页面组
│   │   │   ├── chat/
│   │   │   ├── profile/
│   │   │   ├── resources/
│   │   │   ├── path/
│   │   │   └── wiki/
│   │   └── api/                     # BFF 代理
│   │
│   ├── components/                  # 组件库
│   │   ├── ui/                      # 基础 UI (shadcn)
│   │   ├── chat/                    # 对话组件
│   │   │   ├── ChatMessage.tsx      # 消息气泡
│   │   │   ├── StreamingText.tsx    # 流式文本
│   │   │   ├── ResourceCard.tsx     # 资源卡片
│   │   │   └── AgentStatus.tsx      # Agent 执行状态
│   │   ├── profile/                 # 画像组件
│   │   │   ├── RadarChart.tsx       # 雷达图
│   │   │   └── ProfileCard.tsx
│   │   ├── path/                    # 学习路径组件
│   │   │   └── PathGraph.tsx        # 路径可视化
│   │   └── wiki/                    # Wiki 组件
│   │
│   ├── lib/                         # 工具库
│   │   ├── api.ts                   # API 客户端
│   │   ├── sse.ts                   # SSE 流式处理
│   │   └── store.ts                 # 状态管理
│   │
│   └── styles/
│       └── globals.css              # Claude 设计系统样式
│
└── docs/                            # 📄 提交文档
    ├── 系统设计文档.md
    ├── 技术选型说明.md
    ├── 开源协议声明.md
    └── AI工具使用说明.md
```

---

## 八、核心功能与赛题需求对应

### 8.1 需求覆盖矩阵

| 赛题要求 | 系统模块 | Agent | 状态 |
|---------|---------|-------|------|
| **1. 对话式学习画像** (≥6维度) | ProfileAgent + 对话界面 | Profile Agent | 必做 |
| **2. 多智能体资源生成** (≥5种) | Agent 群协同 | Doc/Quiz/Code/Media/Tutor | 必做 |
| **3. 个性化学习路径** | PathPlanning + 路径可视化 | Planner Agent | 必做 |
| **4. 智能辅导** (加分) | TutorAgent + 多模态解答 | Tutor Agent | 做 |
| **5. 学习效果评估** (加分) | 行为追踪 + 画像更新 | Profile Agent | 做 |

### 8.2 资源类型覆盖 (≥5种)

| # | 资源类型 | 生成 Agent | 输出格式 |
|---|---------|-----------|---------|
| 1 | 课程讲解文档 | DocAgent | Markdown |
| 2 | 知识点思维导图 | DocAgent | Mermaid/Markmap |
| 3 | 练习题目 (选择/填空/编程) | QuizAgent | 结构化 JSON |
| 4 | 代码实操案例 | CodeAgent | Python 代码 |
| 5 | 教学 PPT | MediaAgent | PPTX 文件 |
| 6 | 拓展阅读材料 | DocAgent | Markdown | 必选 |
| 7 | 算法可视化图解 | MediaAgent | Mermaid 图/SVG | 锦上添花 |

> **注**：原设计中第 7 项为"算法可视化动画"（Manim 视频/GIF），但 Manim 需要 LaTeX + FFmpeg 环境且生成耗时长。
> MVP 阶段降级为 Mermaid 流程图 + SVG 静态图解，Phase 5 按时间余量决定是否升级为 Manim 动画。
> 资源类型 1-6 已满足赛题"≥5 种"刚性要求。

### 8.3 非功能性需求覆盖

| 要求 | 实现方案 |
|------|---------|
| **界面美观** | Claude 风格设计系统 (DESIGN.md)，暖色调 |
| **流式输出** | SSE 流式传输，前端逐字渲染 |
| **Markdown 渲染** | react-markdown + rehype 插件 |
| **多模态卡片展示** | 不同资源类型专属卡片组件 |
| **防幻觉** | RAG 知识检索 + 引用标注 + 内容校验 |
| **内容安全** | 输出过滤层 + 讯飞内容审核 |
| **响应速度** | Agent 并行执行 + 流式输出 + 进度追踪 |

---

## 九、开发阶段规划

### Phase 1: 基础骨架 (Week 1)

```
目标: 系统能跑通，可以对话
├── 后端
│   ├── FastAPI 项目初始化 + 数据库建表
│   ├── 用户认证 (JWT)
│   ├── LLM 客户端封装 (讯飞星火 API)
│   └── 基础对话 API (SSE 流式)
├── 前端
│   ├── Next.js 项目初始化 + Claude 主题
│   ├── 登录/注册页面
│   └── 基础对话界面 (流式渲染)
└── 基础设施
    ├── Docker Compose (PG + Redis + MinIO)
    └── 开发环境配置
```

### Phase 2: LLM Wiki + 画像 (Week 2)

```
目标: 知识中枢可用，画像系统工作
├── LLM Wiki
│   ├── 人工智能导论课程知识导入
│   ├── 向量化索引构建
│   ├── RAG 检索引擎
│   └── 知识图谱 (依赖关系)
├── Profile Agent
│   ├── 对话式画像构建
│   ├── 6+ 维度画像模型
│   └── 画像仪表盘 (雷达图)
└── Router Agent
    └── 意图识别与路由
```

### Phase 3: 资源生成 Agent 群 (Week 3)

```
目标: 5+ 种资源可生成
├── DocAgent: 文档 + 思维导图
├── QuizAgent: 多类型练习题
├── CodeAgent: 代码实操案例
├── MediaAgent: PPT + 可视化
├── Planner Agent: 多 Agent 编排
└── 前端: 多模态资源卡片组件
```

### Phase 4: 学习路径 + 智能辅导 (Week 4)

```
目标: 完整学习闭环
├── 学习路径规划与可视化
├── TutorAgent: 智能答疑
├── 学习效果评估
├── 画像动态更新
└── 全链路测试 + 优化
```

#### 学习路径规划算法设计

```
输入：学生画像 + 知识图谱 DAG + 学习目标
输出：有序的学习节点列表（带预估时间和优先级）

算法流程：
1. 目标解析
   └── 从用户请求中提取目标知识点集合 T = {t1, t2, ...}

2. 依赖展开
   └── 对每个 ti，沿 DAG 递归查找所有前置依赖
   └── 合并去重得到完整知识点集合 S = T ∪ prerequisites(T)

3. 画像过滤
   └── 从 S 中移除画像显示已掌握的知识点（knowledge_base[k] >= 80）
   └── 得到待学习集合 L

4. 拓扑排序
   └── 对 L 按 DAG 依赖关系做拓扑排序
   └── 同层节点按画像中的"易错点"优先级排列

5. 时间估算
   └── 根据画像 learning_pace 和 weekly_hours 估算每个节点学习时长
   └── fast: 基础时间 × 0.7, moderate: × 1.0, deep: × 1.5

6. 动态调整
   └── 每次学习活动后（答题/阅读/编码），更新画像中的知识掌握度
   └── 重新执行步骤 3-5，自适应调整剩余路径
```

### Phase 5: 打磨交付 (Week 5)

```
目标: 比赛级别质量
├── UI 精细打磨 (Claude 风格)
├── 防幻觉机制完善
├── 性能优化 (并行/缓存)
├── 文档撰写 (设计文档/技术说明)
└── Demo 视频录制
```

---

## 十、关键技术方案

### 10.1 流式输出方案

```
前端 (Next.js)                    后端 (FastAPI)                   Agent (LangGraph)
    │                                  │                                │
    │  GET /api/chat/stream            │                                │
    │  Accept: text/event-stream       │                                │
    │ ─────────────────────────────────>│                                │
    │                                  │  调用 Agent 编排器              │
    │                                  │ ──────────────────────────────→ │
    │                                  │                                │
    │                                  │  event: agent_status           │
    │  data: {"agent":"DocAgent",      │ <──── "DocAgent 开始工作"       │
    │         "status":"working"}      │                                │
    │ <─────────────────────────────── │                                │
    │                                  │  event: token                  │
    │  data: {"content":"反向传播"}     │ <──── 流式 token               │
    │ <─────────────────────────────── │                                │
    │                                  │  ...更多 token...              │
    │  data: {"content":"算法是..."}    │ <──── 流式 token               │
    │ <─────────────────────────────── │                                │
    │                                  │  event: resource_card          │
    │  data: {"type":"quiz",           │ <──── 资源卡片数据              │
    │         "data":{...}}            │                                │
    │ <─────────────────────────────── │                                │
    │                                  │  event: done                   │
    │ <─────────────────────────────── │                                │
```

### 10.2 防幻觉机制

```
三道防线：

1. 源头控制（RAG）
   └── Agent 必须基于 Wiki 知识库内容生成，不凭空创造
       System Prompt: "只基于以下检索到的知识回答，如不确定请标注"

2. 过程校验（Self-Check）
   └── Agent 生成后自检：
       - 事实性检查：关键公式/定义是否准确
       - 一致性检查：前后逻辑是否矛盾
       - 引用标注：标明知识来源章节

3. 输出过滤（Safety Filter）
   └── 敏感内容过滤 + 学术准确性审查
       - 讯飞内容安全审核 API
       - 自定义学术术语白名单
```

### 10.3 讯飞工具集成方案

赛题要求："开发过程中使用的其他AI辅助工具，需选用科大讯飞相关工具"

| 讯飞工具 | 用途 | 集成点 |
|---------|------|--------|
| **讯飞星火大模型** | Agent 的 LLM 推理引擎 | 所有 Agent 的核心 LLM |
| **讯飞 TTS** | 教学视频语音合成 | MediaAgent 生成教学音频 |
| **讯飞 OCR** | 学生上传资料识别（加分项） | 知识导入管道（Phase 5 按需接入） |
| **讯飞内容审核** | 生成内容安全过滤 | 输出过滤层 |

> **讯飞集成优先级**：星火 LLM（核心，Phase 1）→ 内容审核（Phase 3）→ TTS（Phase 5）→ OCR（Phase 5 可选）。
> 赛题要求"AI 辅助工具需选用科大讯飞"，星火 LLM + 内容审核已满足刚性要求，TTS/OCR 为加分项。

### 10.4 LLM 调用成本估算

| Agent | 平均输入 Token | 平均输出 Token | 调用频率 | 模型选择 |
|-------|--------------|--------------|---------|---------|
| RouterAgent | ~200 | ~50 | 每条消息 | 星火 Lite（低成本快速推理） |
| ProfileAgent | ~500 | ~200 | 含画像信息时 | 星火 Lite |
| DocAgent | ~800 | ~2000 | 按需 | 星火 Pro（需要高质量输出） |
| QuizAgent | ~600 | ~1500 | 按需 | 星火 Pro |
| CodeAgent | ~600 | ~1500 | 按需 | 星火 Pro |
| MediaAgent | ~400 | ~800 | 按需 | 星火 Lite |
| TutorAgent | ~800 | ~1000 | 每次答疑 | 星火 Pro |

**成本控制策略**：
- Router/Profile 使用星火 Lite 版本（成本约为 Pro 的 1/4）
- 生成类 Agent 使用星火 Pro，但加入结果缓存（相同知识点 + 相似画像 → 复用已生成资源）
- 单次复合请求最大 Agent 调用数限制为 5 次
- 设置每日 Token 用量上限告警

---

## 十一、差异化亮点

### 对比竞品的核心差异

| 维度 | 普通 AI 学习工具 | EduAgent |
|------|-----------------|----------|
| 知识管理 | 无结构化知识库 | **LLM Wiki 知识中枢**：结构化 + RAG + 可协作 |
| Agent 架构 | 单一 Agent 或简单串联 | **LangGraph 编排**：并行执行、条件分支、状态管理 |
| 个性化 | 简单偏好设置 | **8 维度动态画像**：对话式构建、随学随新 |
| 资源形式 | 纯文本问答 | **7 种多模态**：文档/思维导图/题目/代码/PPT/动画/视频 |
| 学习路径 | 无或静态 | **DAG 知识图谱驱动**：动态规划、自适应调整 |
| UI 设计 | 通用 AI 界面 | **Claude 风格**：暖色调文艺沙龙、独特辨识度 |

### 核心亮点总结

1. **LLM Wiki 知识中枢**：不只是 RAG，是一个活的、可生长的知识生态
2. **真正的多 Agent 协同**：LangGraph 编排，可观测、可追踪、可并行
3. **对话式画像 → 资源生成闭环**：聊着天就把个性化学习资源生成了
4. **Claude 风格 UI**：暖色调羊皮纸设计，在一堆冷色调 AI 产品中脱颖而出
5. **讯飞深度集成**：不是浅层调用，而是渗透到 LLM/TTS/OCR/安全审核全链路
