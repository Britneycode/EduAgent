# 开源协议声明

本项目（EduAgent）在开发过程中使用了以下开源项目和工具，特此声明并致谢。

---

## 后端依赖

| 项目 | 许可协议 | 用途 |
|------|---------|------|
| [FastAPI](https://github.com/tiangolo/fastapi) | MIT | Web 框架，提供 API 服务 |
| [Uvicorn](https://github.com/encode/uvicorn) | BSD-3-Clause | ASGI 服务器 |
| [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy) | MIT | ORM 框架，数据库访问层 |
| [Alembic](https://github.com/sqlalchemy/alembic) | MIT | 数据库迁移工具 |
| [Pydantic](https://github.com/pydantic/pydantic) | MIT | 数据验证与序列化 |
| [pydantic-settings](https://github.com/pydantic/pydantic-settings) | MIT | 配置管理 |
| [HTTPX](https://github.com/encode/httpx) | BSD-3-Clause | 异步 HTTP 客户端 |
| [asyncpg](https://github.com/MagicStack/asyncpg) | Apache-2.0 | PostgreSQL 异步驱动 |
| [aiosqlite](https://github.com/omnilib/aiosqlite) | MIT | SQLite 异步驱动（开发环境） |
| [PyJWT](https://github.com/jpadilla/pyjwt) | MIT | JWT 认证 |
| [Passlib](https://github.com/ggorber/passlib) | BSD-3-Clause | 密码哈希 |
| [NumPy](https://github.com/numpy/numpy) | BSD-3-Clause | 数值计算 |
| [sentence-transformers](https://github.com/UKPLab/sentence-transformers) | Apache-2.0 | 文本向量化（Embedding） |
| [Tenacity](https://github.com/jd/tenacity) | Apache-2.0 | 重试机制 |
| [LangGraph](https://github.com/langchain-ai/langgraph) | MIT | 多 Agent 状态图编排 |
| [redis-py](https://github.com/redis/redis-py) | MIT | 可选 Redis 缓存客户端 |
| [websockets](https://github.com/python-websockets/websockets) | BSD-3-Clause | 讯飞 TTS WebSocket 调用与异步通信 |
| [chromadb-client](https://github.com/chroma-core/chroma) | Apache-2.0 | Chroma HTTP 向量库客户端 |
| [python-multipart](https://github.com/Kludex/python-multipart) | Apache-2.0 | FastAPI 文件上传表单解析 |
| [pypdf](https://github.com/py-pdf/pypdf) | BSD-3-Clause | PDF 课程资料文本抽取 |
| [python-pptx](https://github.com/scanny/python-pptx) | MIT | PPTX 课程资料文本抽取 |
| [Pytest](https://github.com/pytest-dev/pytest) | MIT | 测试框架 |
| [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) | Apache-2.0 | 异步测试支持 |

## 前端依赖

| 项目 | 许可协议 | 用途 |
|------|---------|------|
| [Next.js](https://github.com/vercel/next.js) | MIT | React 全栈框架 |
| [React](https://github.com/facebook/react) | MIT | UI 组件库 |
| [React DOM](https://github.com/facebook/react/tree/main/packages/react-dom) | MIT | 浏览器 DOM 渲染 |
| [TypeScript](https://github.com/microsoft/TypeScript) | Apache-2.0 | 类型安全的 JavaScript 超集 |
| [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss) | MIT | 工具类优先的 CSS 框架 |
| [@tailwindcss/postcss](https://github.com/tailwindlabs/tailwindcss/tree/main/packages/@tailwindcss-postcss) | MIT | Tailwind CSS PostCSS 插件 |
| [Zustand](https://github.com/pmndrs/zustand) | MIT | 轻量状态管理 |
| [Recharts](https://github.com/recharts/recharts) | MIT | React 图表库（雷达图等） |
| [Mermaid](https://github.com/mermaid-js/mermaid) | MIT | 思维导图和流程图渲染 |
| [react-markdown](https://github.com/remarkjs/react-markdown) | MIT | Markdown 渲染 |
| [remark-gfm](https://github.com/remarkjs/remark-gfm) | MIT | GitHub 风格 Markdown 扩展 |
| [rehype-highlight](https://github.com/rehypejs/rehype-highlight) | MIT | 代码高亮 |
| [highlight.js](https://github.com/highlightjs/highlight.js) | BSD-3-Clause | 语法高亮引擎 |
| [ESLint](https://github.com/eslint/eslint) | MIT | 代码静态分析 |
| [eslint-config-next](https://github.com/vercel/next.js/tree/canary/packages/eslint-config-next) | MIT | Next.js ESLint 规则配置 |
| [Vitest](https://github.com/vitest-dev/vitest) | MIT | 前端测试框架 |
| [@testing-library/react](https://github.com/testing-library/react-testing-library) | MIT | React 组件测试工具 |
| [@testing-library/jest-dom](https://github.com/testing-library/jest-dom) | MIT | DOM 断言扩展 |
| [jsdom](https://github.com/jsdom/jsdom) | MIT | 前端测试 DOM 环境 |
| [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react) | MIT | Vitest/Vite React 测试插件 |

## AI 服务

| 服务 | 提供方 | 用途 |
|------|-------|------|
| 讯飞星火大模型 | 科大讯飞 | 主力 LLM，对话、内容生成 |
| DeepSeek | 深度求索 | 辅助 LLM |

## 向量存储

| 项目 | 许可协议 | 用途 |
|------|---------|------|
| [ChromaDB](https://github.com/chroma-core/chroma) | Apache-2.0 | 可选向量数据库服务，RAG 检索 |

## 开发工具

| 工具 | 许可协议 | 用途 |
|------|---------|------|
| [Ruff](https://github.com/astral-sh/ruff) | MIT | Python 代码格式化与 Lint |
| [uv](https://github.com/astral-sh/uv) | MIT/Apache-2.0 | Python 包管理器 |
| [pnpm](https://github.com/pnpm/pnpm) | MIT | Node.js 包管理器 |

---

> 本项目遵循各依赖项目的开源协议要求。如有遗漏，欢迎指出。
