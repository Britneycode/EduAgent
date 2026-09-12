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

## 二、暴露的工具（16 个）

| 工具名 | 对应 Agent | 说明 |
| --- | --- | --- |
| `route_intent` | Router | 意图路由：主题/是否建档/是否答疑/资源类型 |
| `search_knowledge` | Wiki RAG | 向量 + BM25 混合检索，带来源，防幻觉 |
| `attach_material` | SessionMaterial | 挂载学习材料到会话（知识库未命中的兜底源）；省略 session_id 时自动挂到默认会话 |
| `search_material` | SessionMaterial | 在指定会话材料内 RAG 检索；省略 session_id 时检索默认会话 |
| `create_session` | ChatService | 创建聊天会话，返回会话 ID/标题 |
| `list_sessions` | ChatService | 列出最近 20 个会话（ID/标题/创建时间） |
| `extract_profile` | Profile | 抽取 8 维度学习画像；`persist=true` 时按单学生（user_id=1）累积落库供后续调用复用 |
| `generate_document` | Doc | 个性化中文学习讲义（可传 session_id 基于材料生成） |
| `generate_quiz` | Quiz | 多类型练习题；可选 session_id，知识库未命中时用该会话材料锚定 |
| `generate_code` | Code | 可运行 Python 实操案例；可选 session_id，同上 |
| `generate_mindmap` | Media | 思维导图（Mermaid 渲染图片 + 文本） |
| `generate_ppt` | Media | 教学 PPT 大纲 |
| `generate_reading` | Reading | 拓展阅读材料；可选 session_id，同上 |
| `generate_animation` | Media | 动画分镜脚本 |
| `tutor_answer` | Tutor | 知识库锚定答疑 + 苏格拉底引导（可选 session_id 材料兜底、history 多轮简要记录） |
| `list_courses` | Wiki | 列出知识库课程模板 |

## 三、会话使用流程

MCP 免登录形态没有用户体系，会话按 `session_id` 隔离：

1. **零门槛起步**：`attach_material` / `search_material` 直接省略 `session_id`，
   自动落到标题为「MCP 默认会话」的默认会话（首次自动创建，幂等复用）。
2. **多会话隔离**：先 `create_session(title)` 拿到 `session_id`，再把它传给
   `attach_material`；`list_sessions` 可查看最近 20 个会话。
3. **材料锚定生成**：材料挂好后，`generate_quiz` / `generate_code` /
   `generate_reading` / `generate_document` / `tutor_answer` 传入 `session_id`，
   课程知识库未命中时自动改用该会话已挂载材料锚定（返回的 `context_kind` 标注
   knowledge / material / none）。
4. **画像落库**：`extract_profile(text, persist=true)` 把抽取结果经 ProfileService
   按单学生（user_id=1）累积落库，供后续生成与答疑复用。

## 四、运行

前置条件：与现有后端一致——已配置 LLM 凭证（DeepSeek，或
OpenAI 兼容 `/ DeepSeek`），并确保 `backend/.env` 的 `WIKI_KNOWLEDGE_DIR` 指向
`../knowledge/计算机网络知识库`。

```bash
cd backend

# 离线自检（不加载模型/向量库，只验证导入 + 工具清单 + 会话供给 + 正则路由）
uv run python -m app.mcp_server --self-test

# 以 MCP stdio 服务启动（供 remio/Claude Desktop 等宿主调用）
uv run python -m app.mcp_server
```

## 五、在 Claude Desktop 中注册

编辑 `claude_desktop_config.json`（Windows：`%APPDATA%\Claude\claude_desktop_config.json`；
macOS：`~/Library/Application Support/Claude/claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "eduagent": {
      "command": "cmd",
      "args": [
        "/c", "cd", "/d", "D:\\a-program\\EduAgent\\backend",
        "&&", "uv", "run", "python", "-m", "app.mcp_server"
      ]
    }
  }
}
```

macOS / Linux 用 shell 包装（Claude Desktop 不支持 cwd 字段）：

```json
{
  "mcpServers": {
    "eduagent": {
      "command": "bash",
      "args": ["-c", "cd /path/to/EduAgent/backend && uv run python -m app.mcp_server"]
    }
  }
}
```

改完配置重启 Claude Desktop，工具前缀显示为 `eduagent` 即注册成功。

## 六、在 remio 中注册（示意）

在 remio 的 MCP 外部工具配置里，新增一个 stdio 类型 MCP 服务器，指向：

- 命令：`uv`
- 参数：`run python -m app.mcp_server`
- 工作目录：`backend/`

> 具体注册入口以实际安装的 remio 客户端（aapp-studio）界面为准。若 remio 要求
> `mcp` 官方 SDK 的能力协商更完整，可把这层 stdio JSON-RPC 换成 FastMCP
> （`pip install mcp` 后约 10 行即可挂载同一批 `EduAgentTools` 方法），工具语义不变。

## 七、注册排错

| 现象 | 原因与处理 |
| --- | --- |
| 宿主启动服务器即退出 / 找不到 `uv` | `uv` 不在宿主进程 PATH 里：用 `where uv`（Windows）/ `which uv` 确认绝对路径，把 command 换成绝对路径，或先 `uv sync` 安装依赖 |
| 工具调用报 401 / LLM 连接失败 | `backend/.env` 未配置 LLM 凭证：至少配 `DEEPSEEK_API_KEY` 或 `OPENAI_COMPATIBLE_*` 三件套；本地调试可临时 `LLM_DEV_MODE=true` 验证链路 |
| `search_knowledge` 恒为空 / 生成内容无知识锚定 | 向量库为空：确认 `WIKI_KNOWLEDGE_DIR` 指向 `../knowledge/计算机网络知识库`；服务启动时会自动 `init_wiki()` 重建/加载索引，首次启动请等待摄取完成 |
| Windows 下中文/emoji 输出报 UnicodeEncodeError | stdio 服务已在启动时强制 UTF-8 reconfigure；若经包装脚本/管道中转，请设置 `PYTHONIOENCODING=utf-8`，避免宿主用本地 ANSI 代码页（cp936）解码 |
| 工具调用返回「会话 xxx 不存在」 | 显式传了不存在的 `session_id`：可省略 `session_id` 使用默认会话，或先调用 `create_session` 创建 |

## 八、与 aApp 的关系

- **aApp / skill**：运行在 remio 内，是"原生作品"（见 `../aapp/eduagent-aapp-spec.md`）。
- **MCP 工具集**：同一引擎的"跨产品形态"，是加分项与双轨演示路径——评委在同一套
  多智能体引擎上，既能看 remio 原生 aApp，也能看它被其他智能体产品通过 MCP 调用。