"""金漪湖 · 个性化学习智能体 —— MCP 服务器。

把 EduAgent 的 10 个协同 Agent 引擎，以 MCP（Model Context Protocol）的 16 个工具形式
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

# 10 个 Agent + Wiki 知识中枢 + 会话管理对应的 16 个 MCP 工具（JSON Schema 输入）。
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
        "name": "attach_material",
        "description": "上传/挂载学习材料到某会话（支持 md/txt 文本）。材料按会话隔离，"
        "课程知识库未命中时 Agent 会优先基于这些材料生成。省略 session_id 时自动挂载到默认会话。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "材料文本内容（markdown/纯文本）",
                },
                "session_id": {
                    "type": "integer",
                    "description": "目标聊天会话 ID；省略时使用默认会话",
                },
                "filename": {
                    "type": "string",
                    "description": "材料文件名，默认 notes.md",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "search_material",
        "description": "在指定会话的学习材料内做 RAG 检索，返回与查询相关的材料片段"
        "（知识库覆盖不足时使用）。省略 session_id 时检索默认会话。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "session_id": {
                    "type": "integer",
                    "description": "会话 ID；省略时使用默认会话",
                },
                "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "create_session",
        "description": "创建新的聊天会话，返回会话 ID 与标题；attach_material/search_material "
        "指定 session_id 前可先调用（也可直接省略 session_id 使用默认会话）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "会话标题，默认「新学习会话」",
                }
            },
        },
    },
    {
        "name": "list_sessions",
        "description": "列出最近的聊天会话（最多 20 条），返回会话 ID、标题与创建时间。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "extract_profile",
        "description": "画像 Agent：从学生描述中抽取多维度学习画像更新；persist=true 时把结果"
        "落库供后续调用复用（MCP 免登录形态按单学生 user_id=1 单行累积落库）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "persist": {
                    "type": "boolean",
                    "description": "是否落库（默认 false；true 时按单学生 user_id=1 累积落库）",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "generate_document",
        "description": "文档 Agent：基于 Wiki RAG 检索生成个性化中文学习讲义；传 session_id 时知识库未命中会基于该会话材料生成。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "profile": {"type": "object", "description": "学生画像，可缺省"},
                "course_id": {"type": "string"},
                "session_id": {
                    "type": "integer",
                    "description": "会话 ID，知识库不足时基于该会话材料生成",
                },
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
                "document_content": {
                    "type": "string",
                    "description": "可选，参考讲义文本",
                },
                "course_id": {"type": "string"},
                "session_id": {
                    "type": "integer",
                    "description": "传入后知识库未命中时改用该会话已挂载材料锚定",
                },
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
                "session_id": {
                    "type": "integer",
                    "description": "传入后知识库未命中时改用该会话已挂载材料锚定",
                },
            },
            "required": ["topic"],
        },
    },
    {
        "name": "generate_mindmap",
        "description": "媒体 Agent：生成知识点思维导图（图片 + Mermaid 文本）。",
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
                "session_id": {
                    "type": "integer",
                    "description": "传入后知识库未命中时改用该会话已挂载材料锚定",
                },
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
        "description": "答疑 Agent：基于知识库即时答疑，可选苏格拉底式引导；传 session_id 时知识库未命中会基于该会话材料回答并标注来源。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "profile": {"type": "object"},
                "history": {
                    "type": "string",
                    "description": "可选，多轮对话简要记录，每行一条，格式如「学生：…」「助手：…」",
                },
                "study_mode": {
                    "type": "boolean",
                    "description": "是否用苏格拉底式引导而非直接给答案",
                },
                "course_id": {"type": "string"},
                "session_id": {
                    "type": "integer",
                    "description": "会话 ID，知识库不足时基于该会话材料回答",
                },
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
            "attach_material": self.attach_material,
            "search_material": self.search_material,
            "create_session": self.create_session,
            "list_sessions": self.list_sessions,
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

    async def search_knowledge(
        self, query: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
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

    async def attach_material(
        self,
        content: str,
        session_id: int | None = None,
        filename: str = "notes.md",
    ) -> dict[str, Any]:
        """把一段文本材料挂载到会话（仅支持文本，供 MCP 宿主便捷使用）。"""
        if not content or not content.strip():
            raise ValueError(
                "材料内容不能为空。请粘贴材料文本内容（md/txt，或 pdf/pptx 提取后的文本）。"
            )
        content_bytes = content.encode("utf-8")
        if len(content_bytes) > 10 * 1024 * 1024:
            raise ValueError("材料内容超过 10MB 上限，请拆分为多份材料后分次上传")
        from sqlalchemy import select

        from app.core.database import AsyncSessionLocal
        from app.models.chat import ChatSession
        from app.services.chat_service import get_or_create_default_session
        from app.services.material_service import (
            SessionMaterialError,
            SessionMaterialService,
        )
        from app.wiki import get_wiki_service

        async with AsyncSessionLocal() as db:
            if session_id is None:
                # 免登录形态：省略 session_id 时自动落到默认会话，破除
                # 「必须先建会话才能挂材料」的工具链死锁。
                chat_session = await get_or_create_default_session(db)
                session_id = chat_session.id
            else:
                session_exists = await db.scalar(
                    select(ChatSession.id).where(ChatSession.id == session_id)
                )
                if session_exists is None:
                    raise ValueError(
                        f"会话 {session_id} 不存在；可省略 session_id 使用默认会话，"
                        "或先调用 create_session 创建"
                    )
            wiki = get_wiki_service(session=db)
            service = SessionMaterialService(session=db, wiki_service=wiki)
            try:
                material = await service.attach_material(
                    session_id=session_id,
                    user_id=None,
                    filename=filename or "notes.md",
                    content=content_bytes,
                    mime_type="text/markdown",
                )
            except SessionMaterialError as exc:
                raise ValueError(str(exc)) from exc
            return {
                "session_id": session_id,
                "id": material.id,
                "filename": material.filename,
                "chunk_count": material.chunk_count,
                "char_count": material.char_count,
            }

    async def search_material(
        self,
        query: str,
        session_id: int | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        from sqlalchemy import select

        from app.core.database import AsyncSessionLocal
        from app.models.chat import ChatSession
        from app.services.chat_service import get_or_create_default_session

        async with AsyncSessionLocal() as db:
            if session_id is None:
                chat_session = await get_or_create_default_session(db)
                session_id = chat_session.id
            else:
                session_exists = await db.scalar(
                    select(ChatSession.id).where(ChatSession.id == session_id)
                )
                if session_exists is None:
                    raise ValueError(
                        f"会话 {session_id} 不存在；可省略 session_id 使用默认会话，"
                        "或先调用 create_session 创建"
                    )
        results = await self.wiki.search(query, top_k=top_k, session_id=session_id)
        return [
            {
                "title": r.title,
                "content": r.content,
                "score": r.score,
                "course_id": r.course_id,
            }
            for r in results
        ]

    async def create_session(self, title: str = "新学习会话") -> dict[str, Any]:
        """创建新聊天会话，返回会话 ID 与标题。"""
        from app.core.database import AsyncSessionLocal
        from app.services.chat_service import ChatService

        async with AsyncSessionLocal() as db:
            session_id = await ChatService(session=db).create_session(title=title)
        return {"session_id": session_id, "title": title}

    async def list_sessions(self) -> list[dict[str, Any]]:
        """按创建时间倒序列出最近 20 个会话。"""
        from app.core.database import AsyncSessionLocal
        from app.services.chat_service import ChatService

        async with AsyncSessionLocal() as db:
            sessions = await ChatService(session=db).list_recent_sessions(limit=20)
        return [
            {
                "session_id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
            }
            for s in sessions
        ]

    async def extract_profile(self, text: str, persist: bool = False) -> dict[str, Any]:
        """抽取画像更新；persist=true 时按单学生（user_id=1）累积落库。"""
        update = await self.profile.extract_profile_update_async(text)
        if not persist:
            return update
        from app.core.database import AsyncSessionLocal
        from app.services.profile_service import ProfileService

        async with AsyncSessionLocal() as db:
            response = await ProfileService(session=db).save_profile_update(
                session_id=None, update=update, source="mcp"
            )
        return {"update": update, "persisted": True, "user_id": response.user_id}

    async def generate_document(
        self,
        topic: str,
        profile: dict[str, Any] | None = None,
        course_id: str | None = None,
        session_id: int | None = None,
    ) -> dict[str, Any]:
        resource = await self.doc.generate_document(
            topic, profile, course_id=course_id, session_id=session_id
        )
        return _resource_to_dict(resource)

    async def generate_quiz(
        self,
        topic: str,
        profile: dict[str, Any] | None = None,
        document_content: str | None = None,
        course_id: str | None = None,
        session_id: int | None = None,
    ) -> dict[str, Any]:
        resource = await self.quiz.generate_quiz(
            topic,
            profile,
            document_content=document_content,
            course_id=course_id,
            session_id=session_id,
        )
        return _resource_to_dict(resource)

    async def generate_code(
        self,
        topic: str,
        profile: dict[str, Any] | None = None,
        document_content: str | None = None,
        quiz_content: str | None = None,
        course_id: str | None = None,
        session_id: int | None = None,
    ) -> dict[str, Any]:
        resource = await self.code.generate_code(
            topic,
            profile,
            document_content=document_content,
            quiz_content=quiz_content,
            course_id=course_id,
            session_id=session_id,
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
        session_id: int | None = None,
    ) -> dict[str, Any]:
        resource = await self.reading.generate_reading(
            topic,
            profile,
            document_content=document_content,
            course_id=course_id,
            session_id=session_id,
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
        session_id: int | None = None,
        history: str | None = None,
    ) -> dict[str, Any]:
        answer = await self.tutor.answer(
            question,
            profile,
            history=_parse_history(history),
            study_mode=study_mode,
            course_id=course_id,
            session_id=session_id,
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
        "context_kind": resource.context_kind,
        "image_url": resource.image_url,
        "confidence": resource.confidence,
        "sources": resource.sources,
        "metadata": resource.metadata,
    }


_USER_ROLE_ALIASES = {"学生", "用户", "user"}
_ASSISTANT_ROLE_ALIASES = {"助手", "assistant", "ai"}


def _parse_history(history: str | None) -> list[dict[str, str]]:
    """把 MCP 宿主传入的多轮简要记录解析为 TutorAgent 需要的 role/content 列表。

    每行一条，支持「学生：xxx」「助手：xxx」（中英文冒号均可，说话人大小写不敏感）；
    无法识别说话人的行按学生发言处理。
    """
    if not history:
        return []
    messages: list[dict[str, str]] = []
    for raw_line in history.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        role, content = "user", line
        for sep in ("：", ":"):
            head, _, rest = line.partition(sep)
            speaker = head.strip().lower()
            if speaker in _USER_ROLE_ALIASES or speaker in _ASSISTANT_ROLE_ALIASES:
                role = "user" if speaker in _USER_ROLE_ALIASES else "assistant"
                content = rest.strip()
                break
        if content:
            messages.append({"role": role, "content": content})
    return messages


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
            "version": "2.0.0",
        },
        "instructions": "EduAgent 个性化多智能体学习引擎：支持意图路由、知识检索、画像抽取、"
        "文档/题目/代码/思维导图/PPT/拓展阅读/动画脚本生成与苏格拉底式答疑。"
        "使用编排：首次请先 create_session 建会话，或直接省略 session_id 自动使用默认会话；"
        "attach_material 挂载会话学习材料后，generate_document/generate_quiz/generate_code/"
        "generate_reading/tutor_answer 传 session_id 即可在知识库未命中时基于材料锚定；"
        "extract_profile 传 persist=true 可把画像按单学生（user_id=1）落库，供后续调用累积复用。",
    }


async def _dispatch(
    request: dict[str, Any], tools: EduAgentTools
) -> dict[str, Any] | None:
    method = request.get("method")
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": req_id,
            "result": _initialize_result(),
        }
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
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": req_id,
            "result": {"content": content},
        }

    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": req_id,
        "error": {"code": -32601, "message": f"未知方法：{method}"},
    }


def _parse_error_frame(exc: json.JSONDecodeError) -> dict[str, Any]:
    """畸形 JSON 行对应的标准 JSON-RPC 错误帧（-32700 Parse error）。"""
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": None,
        "error": {
            "code": -32700,
            "message": "Parse error",
            "data": f"畸形 JSON 行：{exc}",
        },
    }


def _invalid_request_frame(detail: str) -> dict[str, Any]:
    """合法 JSON 但不是 Request 对象（如数组/字符串行）的 -32600 错误帧。"""
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": None,
        "error": {"code": -32600, "message": "Invalid Request", "data": detail},
    }


def _write_frame(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


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
        except json.JSONDecodeError as exc:
            # 畸形行回标准 -32700 错误帧后继续读下一行：流式宿主偶发写坏一行时
            # 不能让整个 stdio 通道静默丢消息或挂死。
            _write_frame(_parse_error_frame(exc))
            continue
        if not isinstance(request, dict):
            # 合法 JSON 但不是 Request 对象（数组/字符串行）：_dispatch 只接受 dict，
            # 直接放行会在 request.get 处 AttributeError 打断整个服务循环。
            _write_frame(_invalid_request_frame(f"行不是 JSON-RPC 请求对象：{line[:200]}"))
            continue
        response = await _dispatch(request, tools)
        if response is not None:
            _write_frame(response)


def _self_test() -> None:
    """离线冒烟：不初始化模型/向量库，仅验证导入、工具清单、会话供给与正则路由。"""
    # 仅读配置、不加载模型：dev mode 开启时 Embedding 返回零向量、检索静默退化，
    # 首跑结果会是假的，必须在自检最前面用红色横幅提醒，避免误把假结果当真实效果。
    from app.core.config import get_settings

    if get_settings().wiki_embedding_dev_mode:
        sys.stderr.write(
            "\033[91m"
            "==============================================\n"
            "⚠️ 警告：Embedding 开发模式已开启（WIKI_EMBEDDING_DEV_MODE=true）！\n"
            "向量检索将使用零向量，检索结果是假的、静默退化。\n"
            "正式评测/演示前必须关闭（在 .env 中设为 false）！\n"
            "==============================================\n"
            "\033[0m"
        )
        sys.stderr.flush()

    names = [tool["name"] for tool in TOOLS]
    assert len(names) == 16, f"MCP 工具数应为 16，实际 {len(names)}：{names}"
    print(f"工具数：{len(names)}")
    print("工具清单：", ", ".join(names))

    # 默认会话供给：内存库验证 get_or_create 幂等（不触碰真实 eduagent.db）
    asyncio.run(_check_default_session_idempotent())
    print("默认会话 get_or_create 幂等：通过")

    # 畸形 JSON 行 → 标准 -32700 Parse error 帧（stdio 循环不中断）
    frame = _parse_error_frame(json.JSONDecodeError("Expecting value", "not-json", 0))
    assert frame["id"] is None and frame["error"]["code"] == -32700
    print("畸形行错误帧：", json.dumps(frame, ensure_ascii=False))

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


async def _check_default_session_idempotent() -> None:
    """在内存 SQLite 上验证默认会话 get_or_create 的幂等分支。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.database import Base
    from app.models.chat import ChatSession  # noqa: F401 — 注册模型到 Base 元数据
    from app.services.chat_service import (
        DEFAULT_SESSION_TITLE,
        get_or_create_default_session,
    )

    engine = create_async_engine("sqlite+aiosqlite://")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as db:
            first = await get_or_create_default_session(db)
            second = await get_or_create_default_session(db)
            assert first.id == second.id, "默认会话应幂等复用，不应重复创建"
            assert first.title == DEFAULT_SESSION_TITLE

            # 已有多个同标题会话时复用最新一条，不重复创建
            db.add(ChatSession(title=DEFAULT_SESSION_TITLE))
            await db.commit()
            newer = await get_or_create_default_session(db)
            assert newer.id > first.id
            again = await get_or_create_default_session(db)
            assert again.id == newer.id, "同标题多会话时应稳定复用最新一条"
    finally:
        await engine.dispose()


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
