# remio — 金漪湖论剑 · 智能体融合创新赛道 参赛交付包

本目录是 EduAgent 项目针对 **https://51tokenlink.com/tracks/agent-innovation**
（2026 智能体 OPC 创新大会 · 金漪湖论剑 · 智能体融合创新赛道）的改造交付物。

> 原项目是"个性化多智能体学习系统"（FastAPI + Next.js + LangGraph 多 Agent + RAG +
> 结构化课程知识库）。本次**不推翻原应用**，而是把它的核心能力按赛事要求的
> "remio aApp / skill"形态重新表达，并补齐参赛材料。

---

## 目录结构

```
remio/
├── README.md                          ← 本文件：总览 + 改造说明 + 差距分析
├── aapp/
│   ├── eduagent-aapp-spec.md          ← remio aApp「个性化学习智能体」开发规格（核心交付物）
│   └── eduagent-aapp-manifest.json    ← 端点/能力/自动化的机器可读清单
├── mcp/
│   └── README.md                      ← MCP 工具集说明（跨智能体产品运行，加分项）
└── docs/
    ├── 01_方案文档.md                  ← 作品方案（对齐评分维度）
    ├── 02_Demo演示脚本.md             ← 演示动线逐屏脚本
    ├── 03_演示视频分镜脚本.md         ← 演示视频拍摄分镜
    ├── 04_路演PPT大纲.md             ← 决赛路演 PPT 结构
    ├── 05_AI工具与开源合规说明.md     ← AI 工具选型 + 开源协议声明
    └── 06_提交清单与验收自评.md       ← 提交材料清单 + 评分维度自评
```

## 实现文件（在原有代码基础上增量新增）

- `backend/app/mcp_server.py` — 把 10 Agent 多智能体引擎封装为 MCP 工具集（12 个工具，零新增依赖，已自检通过）。

## 改造思路（差距分析结果）

| 比赛要求 | 原项目现状 | 改造动作 |
| --- | --- | --- |
| 作品形式 = remio aApp/skill | 独立 Web 应用 | 新增《aApp 开发规格》+ manifest，把 10 个 Agent 重表达为语义端点 + remio 能力调用 |
| 可在 remio 正常运行 | 不依赖 remio | 规格完全按 remio「语义端点→对话为主→UI为辅→订阅自动化→发布」范式编写 |
| 如能在其他智能体产品正常运行更佳 | 全栈自闭环 | 新增 MCP 工具集（`backend/app/mcp_server.py`），跨产品可调 |
| 提交方案文档 / Demo / 演示视频 | 已有 7 份 .docx（旧口径） | 新增 `docs/01–06`，口径切换为金漪湖论剑赛道 |
| 完成度（35）/可用性（30）/契合度（25）/创新性（10） | — | `docs/01` 与 `docs/06` 逐条对齐并自评 |
| 场景理解 / 创新性 / 技术难度 / 完成度 / 展示效果（复赛决赛） | — | 技术难度走 MCP + 多 Agent；展示效果走 Demo/视频/路演脚本 |

## 三分钟看懂怎么用

1. **在 remio 内做 aApp**：打开 remio 客户端 → aapp-studio → 按
   `aapp/eduagent-aapp-spec.md` 第 2–7 节逐步搭端点/UI/订阅。
2. **跨产品调用**：按 `mcp/README.md` 用 `uv run python -m app.mcp_server` 起 MCP 服务。
3. **独立 Web 演示**（原应用，已部署 `https://xwz0219.top`）：作为 Demo 与
   "其他产品正常运行"的另一种呈现，评委可直接体验流式对话 + 多模态资源卡片。
4. **提交材料**：按 `docs/01–06` 整理方案文档、Demo、演示视频与路演 PPT。

## 外部依赖边界（重要，如实说明）

remio 的 aApp/skill 打包与上架格式内嵌在 remio 桌面客户端（aapp-studio）中，
官网未公开独立的 web SDK 文档。因此本交付包提供了**可逐步执行的开发规格**与
**自验证的 MCP 工具集**，但"导入 aapp-studio 生成、安装到正式环境、发布到应用市场"
这三步需要在已登录的 remio 客户端内由开发者完成，并需一个 remio 账号。