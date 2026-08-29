"""金漪湖 · 个性化学习智能体 —— MCP 服务器。

把 EduAgent 的 10 个协同 Agent 引擎，以 MCP（Model Context Protocol）的 12 个工具形式
暴露给 remio 睿妙及其他支持 MCP 的智能体宿主，落地「如能在其他智能体产品中
正常运行更佳」这一加分项。

实现要点：
- 仅依赖标准库（asyncio / json / sys / dataclasses），零新增三方依赖。
- stdio 传输：每行一条 JSON-RPC 2.0 消息，覆盖 initialize / tools/list / tools/call。
- 启动时完整复用 EduAgent 现有生命周期：init_db() + init_wiki()，随后按
  build_orchestrator 同款装配逻辑实例化各 Agent。

运行方式（在 backend/ 目录，需已配置 LLM 凭证（DeepSeek 或 OpenAI 兼容接口））：

    uv run python -m app.mcp_server             # 以 MCP stdio 服务启动
    uv run python -m app.mcp_server --self-test # 离线自检：工具清单 + 正则路由冒烟
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"

# 10 个 Agent + Wiki 知识中枢对应的 12 个 MCP 工具（JSON Schema 输入）。
# profile 字段在各工具中均为可选对象，缺省按空画像处理。
TOOLS: list[dict[str, Any]] = [
    {
        "name": "route_intent",
        "description": "路由 Agent：识别学生学习意图，输出是否需要建档、是否答疑、主题与所需资源类型。",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "学生输入的原话"}},
            "required": ["text"],
        },
    },
    {
        "name": "search_knowledge",
        "description": "Wiki 知识中枢 RAG 检索：对知识库做向量 + BM25 混合检索，返回带来源的知识片段，防幻觉。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "extract_profile",
        "description": "画像 Agent：从学生描述中抽取多维度学习画像更新。",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "generate_document",
        "description": "文档 Agent：基于 Wiki RAG 检索生成个性化中文学习讲义。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "profile": {"type": "object", "description": "学生画像，可缺省"},
                "course_id": {"type": "string"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "generate_quiz",
        "description": "题目 Agent：生成选择/填空/简答/编程等多类型练习题。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "profile": {"type": "object"},
                "document_content": {"type": "string", "description": "可选，参考讲义文本"},
                "course_id": {"type": "string"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "generate_code",
        "description": "代码 Agent：生成可运行的 Python 实操案例。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "profile": {"type": "object"},
                "document_content": {"type": "string"},
                "quiz_content": {"type": "string"},
                "course_id": {"type": "string"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "generate_mindmap",
        "description": "媒体 Agent：生成知识点思维导图（Markdown 结构）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "profile": {"type": "object"},
                "document_content": {"type": "string"},
                "course_id": {"type": "string"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "generate_ppt",
        "description": "媒体 Agent：生成教学 PPT 大纲与分页内容。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "profile": {"type": "object"},
                "document_content": {"type": "string"},
                "course_id": {"type": "string"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "generate_reading",
        "description": "拓展阅读 Agent：生成主题相关拓展阅读材料。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "profile": {"type": "object"},
                "document_content": {"type": "string"},
                "course_id": {"type": "string"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "generate_animation",
        "description": "媒体 Agent：生成算法/原理动画分镜脚本。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "profile": {"type": "object"},
                "document_content": {"type": "string"},
                "course_id": {"type": "string"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "tutor_answer",
        "description": "答疑 Agent：基于知识库即时答疑，可选苏格拉底式引导。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "profile": {"type": "object"},
                "study_mode": {"type": "boolean", "description": "是否用苏格拉底式引导而非直接给答案"},
                "course_id": {"type": "string"},
            },
            "required": ["question"],
        },
    },
    {
        "name": "list_courses",
        "description": "列出知识库中的可用课程模板与章节数。",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


class EduAgentTools:
    """把 EduAgent 各 Agent 的可复用生成方法封装成 MCP 工具门面。"""

    def __init__(
        self,
        *,
        router: Any,
        profile: Any,
        doc: Any,
        quiz: Any,
        code: Any,
        media: Any,
        reading: Any,
        tutor: Any,
        wiki: Any,
    ) -> None:
        self.router = router
        self.profile = profile
        self.doc = doc
        self.quiz = quiz
        self.code = code
        self.media = media
        self.reading = reading
        self.tutor = tutor
        self.wiki = wiki
        self._handlers: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
            "route_intent": self.route_intent,
            "search_knowledge": self.search_knowledge,
            "extract_profile": self.extract_profile,
            "generate_document": self.generate_document,
            "generate_quiz": self.generate_quiz,
            "generate_code": self.generate_code,
            "generate_mindmap": self.generate_mindmap,
            "generate_ppt": self.generate_ppt,
            "generate_reading": self.generate_reading,
            "generate_animation": self.generate_animation,
            "tutor_answer": self.tutor_answer,
            "list_courses": self.list_courses,
        }

    async def call(self, name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        handler = self._handlers.get(name)
        if handler is None:
            raise ValueError(f"未知工具：{name}")
        payload = await handler(**arguments)
        return [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]

    async def route_intent(self, text: str) -> dict[str, Any]:
        decision = await self.router.route_async(text)
        return {
            "topic": decision.topic,
            "update_profile": decision.update_profile,
            "is_tutor_question": decision.is_tutor_question,
            "generate_document": decision.generate_document,
            "resource_types": decision.resource_types,
            "quiz_only": decision.quiz_only,
        }

    async def search_knowledge(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        results = await self.wiki.search(query, top_k=top_k)
        return [
            {
                "title": r.title,
                "chapter": r.chapter,
                "section": r.section,
                "content": r.content,
                "score": r.score,
                "course_id": r.course_id,
            }
            for r in results
        ]

    async def extract_profile(self, text: str) -> dict[str, Any]:
        return await self.profile.extract_profile_update_async(text)

    async def generate_document(
        self,
        topic: str,
        profile: dict[str, Any] | None = None,
        course_id: str | None = None,
    ) -> dict[str, Any]:
        resource = await self.doc.generate_document(topic, profile, course_id=course_id)
        return _resource_to_dict(resource)

    async def generate_quiz(
        self,
        topic: str,
        profile: dict[str, Any] | None = None,
        document_content: str | None = None,
        course_id: str | None = None,
    ) -> dict[str, Any]:
        resource = await self.quiz.generate_quiz(
            topic, profile, document_content=document_content, course_id=course_id
        )
        return _resource_to_dict(resource)

    async def generate_code(
        self,
        topic: str,
        profile: dict[str, Any] | None = None,
        document_content: str | None = None,
        quiz_content: str | None = None,
        course_id: str | None = None,
    ) -> dict[str, Any]:
        resource = await self.code.generate_code(
            topic,
            profile,
            document_content=document_content,
            quiz_content=quiz_content,
            course_id=course_id,
        )
        return _resource_to_dict(resource)

    async def generate_mindmap(
        self,
        topic: str,
        profile: dict[str, Any] | None = None,
        document_content: str | None = None,
        course_id: str | None = None,
    ) -> dict[str, Any]:
        resource = await self.media.generate_mindmap(
            topic, profile, document_content=document_content, course_id=course_id
        )
        return _resource_to_dict(resource)

    async def generate_ppt(
        self,
        topic: str,
        profile: dict[str, Any] | None = None,
        document_content: str | None = None,
        course_id: str | None = None,
    ) -> dict[str, Any]:
        resource = await self.media.generate_ppt_outline(
            topic, profile, document_content=document_content, course_id=course_id
        )
        return _resource_to_dict(resource)

    async def generate_reading(
        self,
        topic: str,
        profile: dict[str, Any] | None = None,
        document_content: str | None = None,
        course_id: str | None = None,
    ) -> dict[str, Any]:
        resource = await self.reading.generate_reading(
            topic, profile, document_content=document_content, course_id=course_id
        )
        return _resource_to_dict(resource)

    async def generate_animation(
        self,
        topic: str,
        profile: dict[str, Any] | None = None,
        document_content: str | None = None,
        course_id: str | None = None,
    ) -> dict[str, Any]:
        resource = await self.media.generate_animation_script(
            topic, profile, document_content=document_content, course_id=course_id
        )
        return _resource_to_dict(resource)

    async def tutor_answer(
        self,
        question: str,
        profile: dict[str, Any] | None = None,
        study_mode: bool = False,
        course_id: str | None = None,
    ) -> dict[str, Any]:
        answer = await self.tutor.answer(
            question,
            profile,
            study_mode=study_mode,
            course_id=course_id,
        )
        return {"answer": answer}

    async def list_courses(self) -> list[dict[str, Any]]:
        return self.wiki.list_courses()


def _resource_to_dict(resource: Any) -> dict[str, Any]:
    """把 AgentResource dataclass 转成稳定 JSON 结构。"""
    return {
        "title": resource.title,
        "resource_type": resource.resource_type,
        "content": resource.content,
        "knowledge_point": resource.knowledge_point,
        "agent_name": resource.agent_name,
        "wiki_fallback": resource.wiki_fallback,
        "confidence": resource.confidence,
        "sources": resource.sources,
        "metadata": resource.metadata,
    }


async def _build_tools() -> EduAgentTools:
    """复用 EduAgent 现有生命周期完成引擎装配。"""
    from app.agents.code_agent import CodeAgent
    from app.agents.doc_agent import DocAgent
    from app.agents.media_agent import MediaAgent
    from app.agents.profile_agent import ProfileAgent
    from app.agents.quiz_agent import QuizAgent
    from app.agents.reading_agent import ReadingAgent
    from app.agents.router_agent import RouterAgent
    from app.agents.tutor_agent import TutorAgent
    from app.core.database import AsyncSessionLocal, init_db
    from app.core.llm import get_llm_client
    from app.wiki import get_wiki_service, init_wiki

    await init_db()
    async with AsyncSessionLocal() as session:
        await init_wiki(session=session)
    # MCP 工具只走 search/list_courses（不读写 DB 会话），传 None 避免持有
    # 已关闭的 session；write_back/ingest 等需会话的路径不在此使用。
    wiki = get_wiki_service()

    llm = get_llm_client()
    return EduAgentTools(
        router=RouterAgent(llm_client=llm),
        profile=ProfileAgent(llm_client=llm),
        doc=DocAgent(wiki_service=wiki),
        quiz=QuizAgent(wiki_service=wiki),
        code=CodeAgent(wiki_service=wiki),
        media=MediaAgent(wiki_service=wiki),
        reading=ReadingAgent(wiki_service=wiki),
        tutor=TutorAgent(wiki_service=wiki),
        wiki=wiki,
    )


def _initialize_result() -> dict[str, Any]:
    return {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {
            "name": "eduagent-personalized-learning",
            "version": "0.1.0",
        },
        "instructions": "EduAgent 个性化多智能体学习引擎：支持意图路由、知识检索、画像抽取、"
        "文档/题目/代码/思维导图/PPT/拓展阅读/动画脚本生成与苏格拉底式答疑。",
    }


async def _dispatch(request: dict[str, Any], tools: EduAgentTools) -> dict[str, Any] | None:
    method = request.get("method")
    req_id = request.get("id")

    if method == "initialize":
        return {"jsonrpc": JSONRPC_VERSION, "id": req_id, "result": _initialize_result()}
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return {"jsonrpc": JSONRPC_VERSION, "id": req_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": JSONRPC_VERSION, "id": req_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = request.get("params") or {}
        name = str(params.get("name", ""))
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            arguments = {}
        try:
            content = await tools.call(name, arguments)
        except Exception as exc:  # noqa: BLE001 — 工具异常需回传给宿主侧
            logger.exception("MCP 工具调用失败: %s", name)
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"工具调用失败：{exc}"}],
                    "isError": True,
                },
            }
        return {"jsonrpc": JSONRPC_VERSION, "id": req_id, "result": {"content": content}}

    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": req_id,
        "error": {"code": -32601, "message": f"未知方法：{method}"},
    }


async def _serve_stdio(tools: EduAgentTools) -> None:
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = await _dispatch(request, tools)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def _self_test() -> None:
    """离线冒烟：不初始化模型/向量库，仅验证导入、工具清单与正则路由。"""
    names = [tool["name"] for tool in TOOLS]
    print(f"工具数：{len(names)}")
    print("工具清单：", ", ".join(names))

    # 正则路由（RouterAgent.route 不依赖 LLM），验证路由逻辑可运行
    from app.agents.router_agent import RouterAgent

    router = RouterAgent(llm_client=None)
    samples = (
        "什么是TCP三次握手",
        "帮我整理一下子网划分的笔记和思维导图",
        "给我出几道关于HTTP的练习题",
        "我是计算机专业大一学生，基础一般，想复习TCP",
    )
    for text in samples:
        decision = router.route(text)
        print(
            f"输入「{text}」=> 主题={decision.topic} "
            f"资源={decision.resource_types} "
            f"答疑={decision.is_tutor_question} 建档={decision.update_profile}"
        )
    print("自检通过（仅验证离线路径；完整引擎需配置 LLM 后以 MCP 模式启动）")


def main() -> None:
    # stdio 传输必须为 UTF-8：MCP 规范要求，且 Windows 宿主以管道启动时
    # 默认使用本地 ANSI 代码页（如 cp936），LLM 输出中的 emoji 会触发
    # UnicodeEncodeError 使服务崩溃。
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO)
    if "--self-test" in sys.argv:
        _self_test()
        return
    tools = asyncio.run(_build_tools())
    asyncio.run(_serve_stdio(tools))


if __name__ == "__main__":
    main()