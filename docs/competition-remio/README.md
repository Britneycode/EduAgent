# docs/competition-remio — 说明

本目录是 **金漪湖 · 智能体融合创新赛道** 的工程文档附录，只有一份：

| 文档 | 内容 |
| --- | --- |
| 01_方案说明书.md | 需求分析 + 系统设计与实现 + 验收口径 + 创新点 |

- Markdown 可直接进 Git 做版本管理，需要 .docx 时 `pandoc 01_方案说明书.md -o 01_方案说明书.docx` 一条命令转换。
- `remio/docs/*.md` = **提交给平台的材料**（方案/演示/视频/路演/合规/自评）。
- 本目录 = **工程文档附录**（比方案文档更细的系统设计与验收口径），评审需要时随方案文档附上。

> 口径基线：10 个协同 Agent（LangGraph）· LLM Wiki 知识中枢（3 门课程知识库，
> 向量 + BM25 混合检索）· remio aApp 10 端点（E1–E10）· MCP 工具集（12 工具，
> stdio 零依赖）。与 `remio/aapp/eduagent-aapp-spec.md`、`remio/mcp/README.md`、
> `CLAUDE.md` 保持一致。
