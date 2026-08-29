# EduAgent MCP 工具集 — 跨智能体产品运行

把 EduAgent 的 10 个协同 Agent 引擎，封装为符合 **MCP（Model Context Protocol）** 的
工具集，可在 **remio 睿妙**（赛事"系统调用覆盖 MCP 外部工具"）以及任何支持 MCP 的
智能体宿主（Claude Desktop、各类 Agent 客户端等）中注册调用。

这是赛事评分中"**技术实现难度**（工具调用深度、系统架构）"与"**如能在其他智能体
产品中正常运行更佳**"这一加分项的直接落地。

---

## 一、实现文件

- 服务文件：`backend/app/mcp_server.py`（实现见该文件内 `TOOLS` 与 `EduAgentTools`）
- 依赖：**零新增三方依赖**，仅用标准库实现 MCP stdio 传输（JSON-RPC 2.0）。

## 二、暴露的工具（12 个）

| 工具名 | 对应 Agent | 说明 |
| --- | --- | --- |
| `route_intent` | Router | 意图路由：主题/是否建档/是否答疑/资源类型 |
| `search_knowledge` | Wiki RAG | 向量 + BM25 混合检索，带来源，防幻觉 |
| `extract_profile` | Profile | 抽取 8 维度学习画像 |
| `generate_document` | Doc | 个性化中文学习讲义 |
| `generate_quiz` | Quiz | 多类型练习题 |
| `generate_code` | Code | 可运行 Python 实操案例 |
| `generate_mindmap` | Media | 思维导图（Markdown 结构） |
| `generate_ppt` | Media | 教学 PPT 大纲 |
| `generate_reading` | Reading | 拓展阅读材料 |
| `generate_animation` | Media | 动画分镜脚本 |
| `tutor_answer` | Tutor | 知识库锚定答疑 + 苏格拉底引导 |
| `list_courses` | Wiki | 列出知识库课程模板 |

## 三、运行

前置条件：与现有后端一致——已配置 LLM 凭证（DeepSeek，或
OpenAI 兼容 `/ DeepSeek`），并确保 `backend/.env` 的 `WIKI_KNOWLEDGE_DIR` 指向
`./knowledge/计算机网络知识库`。

```bash
cd backend

# 离线自检（不加载模型/向量库，只验证导入 + 工具清单 + 正则路由）
uv run python -m app.mcp_server --self-test

# 以 MCP stdio 服务启动（供 remio/Claude Desktop 等宿主调用）
uv run python -m app.mcp_server
```

## 四、在 remio 中注册（示意）

在 remio 的 MCP 外部工具配置里，新增一个 stdio 类型 MCP 服务器，指向：

- 命令：`uv`
- 参数：`run python -m app.mcp_server`
- 工作目录：`backend/`

> 具体注册入口以实际安装的 remio 客户端（aapp-studio）界面为准。若 remio 要求
> `mcp` 官方 SDK 的能力协商更完整，可把这层 stdio JSON-RPC 换成 FastMCP
> （`pip install mcp` 后约 10 行即可挂载同一批 `EduAgentTools` 方法），工具语义不变。

## 五、与 aApp 的关系

- **aApp / skill**：运行在 remio 内，是"原生作品"（见 `../aapp/eduagent-aapp-spec.md`）。
- **MCP 工具集**：同一引擎的"跨产品形态"，是加分项与双轨演示路径——评委在同一套
  多智能体引擎上，既能看 remio 原生 aApp，也能看它被其他智能体产品通过 MCP 调用。