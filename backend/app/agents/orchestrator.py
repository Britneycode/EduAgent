from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.code_agent import CodeAgent
from app.agents.content_guard import (
    audit_model_output,
    filter_unsafe_fragments,
    format_source_citations,
    guard_content,
)
from app.agents.doc_agent import DocAgent
from app.agents.media_agent import MediaAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.profile_agent import ProfileAgent
from app.agents.quiz_agent import QuizAgent
from app.agents.reading_agent import ReadingAgent
from app.agents.resource_types import AgentResource
from app.agents.router_agent import RouteDecision, RouterAgent
from app.agents.tutor_agent import TutorAgent
from app.agents.video_agent import VideoAgent
from app.core.config import get_settings
from app.schemas.chat import (
    ResourceCardPayload,
    SSEEvent,
    agent_status_event,
    done_event,
    error_event,
    progress_event,
    profile_update_proposed_event,
    resource_card_event,
    token_event,
    wiki_fallback_event,
)
from app.services.chat_service import ChatService
from app.services.learning_path_service import LearningPathService
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

GRAPH_NODE_NAMES = (
    "route",
    "profile",
    "dispatch",
    "tutor",
    "plan_resources",
    "document",
    "parallel_resources",
    "finalize",
)
_TUTOR_STREAM_FLUSH_CHARS = 220
_TUTOR_SENTENCE_ENDINGS = ("。", "！", "？", ".", "!", "?", "\n")


class OrchestratorState(TypedDict, total=False):
    session_id: int
    user_id: int
    user_message: str
    history: list[dict[str, str]]
    decision: RouteDecision
    profile: dict[str, Any]
    resource_types: list[str]
    generated_resources: dict[str, AgentResource]
    assistant_content: str
    study_mode: bool
    run_id: str
    course_id: str | None
    events: list[SSEEvent]
    stop: bool


def _should_flush_tutor_buffer(buffer: str) -> bool:
    if len(buffer) >= _TUTOR_STREAM_FLUSH_CHARS:
        return True
    return buffer.rstrip().endswith(_TUTOR_SENTENCE_ENDINGS)


def _build_resource_intro(topic: str, resource_types: list[str], single_resource: bool) -> str:
    if not single_resource:
        return f"好的，我来为你生成关于「{topic}」的学习资源。"

    primary_type = resource_types[0] if resource_types else "quiz"
    intro_by_type = {
        "quiz": f"好的，我来为你生成「{topic}」的练习题，请开始作答吧！",
        "ppt": f"好的，我来为你生成「{topic}」的 PPT 演示图片，请稍候...",
        "mindmap": f"好的，我来为你生成「{topic}」的思维导图，请稍候...",
        "animation": f"好的，我来为你生成「{topic}」的动画分镜脚本，请稍候...",
        "code": f"好的，我来为你生成「{topic}」的代码实践资源，请稍候...",
        "reading": f"好的，我来为你生成「{topic}」的拓展阅读资源，请稍候...",
        "video": f"好的，我来为你查找「{topic}」相关视频，请稍候...",
    }
    return intro_by_type.get(
        primary_type,
        f"好的，我来为你生成「{topic}」的学习资源，请稍候...",
    )


def _build_resource_status_message(
    resource_types: list[str],
    single_resource: bool,
) -> str:
    if not single_resource:
        return "正在逐项生成学习资源..."

    primary_type = resource_types[0] if resource_types else "quiz"
    status_by_type = {
        "quiz": "正在生成练习题...",
        "ppt": "正在生成 PPT 演示图片...",
        "mindmap": "正在生成思维导图...",
        "animation": "正在生成动画分镜脚本...",
        "code": "正在生成代码实践资源...",
        "reading": "正在生成拓展阅读资源...",
        "video": "正在搜索相关视频...",
    }
    return status_by_type.get(primary_type, "正在生成学习资源...")


class Orchestrator:
    """LangGraph 多智能体编排器：统一控制事件顺序和 Agent 状态流转。"""

    def __init__(
        self,
        *,
        router_agent: RouterAgent,
        profile_agent: ProfileAgent,
        planner_agent: PlannerAgent,
        doc_agent: DocAgent,
        quiz_agent: QuizAgent,
        code_agent: CodeAgent,
        media_agent: MediaAgent,
        reading_agent: ReadingAgent,
        video_agent: VideoAgent,
        tutor_agent: TutorAgent,
        profile_service: ProfileService,
        chat_service: ChatService,
        learning_service: LearningPathService | None = None,
    ) -> None:
        self.router_agent = router_agent
        self.profile_agent = profile_agent
        self.planner_agent = planner_agent
        self.doc_agent = doc_agent
        self.quiz_agent = quiz_agent
        self.code_agent = code_agent
        self.media_agent = media_agent
        self.reading_agent = reading_agent
        self.video_agent = video_agent
        self.tutor_agent = tutor_agent
        self.profile_service = profile_service
        self.chat_service = chat_service
        self.learning_service = learning_service
        self._record_lock = asyncio.Lock()
        self._resource_concurrency = max(1, get_settings().resource_concurrency)
        self._graph = self._build_graph()

    async def run(
        self,
        *,
        session_id: int,
        user_message: str,
        user_id: int = 1,
        history: list[dict[str, str]] | None = None,
        study_mode: bool = False,
        course_id: str | None = None,
    ) -> AsyncGenerator[SSEEvent, None]:
        initial_state: OrchestratorState = {
            "session_id": session_id,
            "user_id": user_id,
            "user_message": user_message,
            "history": history or [],
            "profile": {},
            "generated_resources": {},
            "study_mode": study_mode,
            "run_id": uuid.uuid4().hex[:16],
            "course_id": course_id,
            "events": [],
            "stop": False,
        }

        async for update in self._graph.astream(
            initial_state,
            stream_mode="updates",
        ):
            for node_update in update.values():
                if not isinstance(node_update, dict):
                    continue
                for event in node_update.get("events", []):
                    yield event

    def graph_node_names(self) -> tuple[str, ...]:
        """返回当前 LangGraph 编排节点，供健康检查和测试验证。"""
        return GRAPH_NODE_NAMES

    async def _record_agent_event(
        self,
        *,
        state: OrchestratorState,
        started_at: float,
        agent_name: str,
        node_name: str,
        status: str,
        resource_type: str | None = None,
        input_chars: int = 0,
        output_chars: int = 0,
        error: str | None = None,
        event_metadata: dict[str, Any] | None = None,
        llm_holder: object | None = None,
    ) -> None:
        """Persist a best-effort observability event without disrupting chat."""
        if self.learning_service is None:
            return

        duration_ms = round((time.perf_counter() - started_at) * 1000)
        llm_client = getattr(llm_holder, "llm_client", None)
        llm_provider = _llm_provider_name(llm_client)
        try:
            async with self._record_lock:
                await self.learning_service.record_agent_run_event(
                    run_id=state["run_id"],
                    user_id=state["user_id"],
                    session_id=state["session_id"],
                    agent_name=agent_name,
                    node_name=node_name,
                    resource_type=resource_type,
                    status=status,
                    duration_ms=duration_ms,
                    llm_provider=llm_provider,
                    llm_used=llm_client is not None,
                    input_chars=input_chars,
                    output_chars=output_chars,
                    token_estimate=_estimate_tokens(input_chars + output_chars),
                    error=error,
                    event_metadata=event_metadata or {},
                )
        except Exception:
            logger.warning("记录 Agent 运行事件失败", exc_info=True)

    def _build_graph(self):
        graph = StateGraph(OrchestratorState)
        graph.add_node("route", self._route_node)
        graph.add_node("profile", self._profile_node)
        graph.add_node("dispatch", self._dispatch_node)
        graph.add_node("tutor", self._tutor_node)
        graph.add_node("plan_resources", self._plan_resources_node)
        graph.add_node("document", self._document_node)
        graph.add_node("parallel_resources", self._parallel_resources_node)
        graph.add_node("finalize", self._finalize_node)

        graph.add_edge(START, "route")
        graph.add_conditional_edges(
            "route",
            self._after_route,
            {"profile": "profile", "dispatch": "dispatch"},
        )
        graph.add_edge("profile", "dispatch")
        graph.add_conditional_edges(
            "dispatch",
            self._after_dispatch,
            {"tutor": "tutor", "plan_resources": "plan_resources"},
        )
        graph.add_edge("tutor", END)
        graph.add_conditional_edges(
            "plan_resources",
            self._after_plan_resources,
            {
                "document": "document",
                "parallel_resources": "parallel_resources",
                "end": END,
            },
        )
        graph.add_conditional_edges(
            "document",
            self._after_document,
            {
                "parallel_resources": "parallel_resources",
                "finalize": "finalize",
                "end": END,
            },
        )
        graph.add_conditional_edges(
            "parallel_resources",
            self._after_parallel_resources,
            {"finalize": "finalize", "end": END},
        )
        graph.add_edge("finalize", END)
        return graph.compile()

    async def _route_node(self, state: OrchestratorState) -> OrchestratorState:
        started_at = time.perf_counter()
        session_id = state["session_id"]
        try:
            decision = await self.router_agent.route_async(state["user_message"])
        except Exception as exc:
            await self._record_agent_event(
                state=state,
                started_at=started_at,
                agent_name="RouterAgent",
                node_name="route",
                status="error",
                input_chars=len(state["user_message"]),
                error=str(exc),
                llm_holder=self.router_agent,
            )
            raise
        await self._record_agent_event(
            state=state,
            started_at=started_at,
            agent_name="RouterAgent",
            node_name="route",
            status="success",
            input_chars=len(state["user_message"]),
            output_chars=len(decision.topic),
            event_metadata={
                "topic": decision.topic,
                "update_profile": decision.update_profile,
                "generate_document": decision.generate_document,
                "is_tutor_question": decision.is_tutor_question,
                "resource_types": decision.resource_types,
            },
            llm_holder=self.router_agent,
        )
        return {
            "decision": decision,
            "events": [
                agent_status_event(
                    agent="RouterAgent",
                    status="working",
                    message="正在识别学习意图与任务类型",
                    session_id=session_id,
                )
            ],
        }

    async def _profile_node(self, state: OrchestratorState) -> OrchestratorState:
        started_at = time.perf_counter()
        session_id = state["session_id"]
        user_id = state["user_id"]
        events = [
            agent_status_event(
                agent="ProfileAgent",
                status="working",
                message="正在更新学习画像",
                session_id=session_id,
            )
        ]

        profile: dict[str, Any] = {}
        try:
            update = await self.profile_agent.extract_profile_update_async(
                state["user_message"],
            )
        except Exception:
            logger.warning("学习画像抽取失败，跳过本轮画像更新", exc_info=True)
            update = {}

        if update:
            try:
                profile_resp, proposed_update, changed_fields = (
                    await self.profile_service.preview_profile_update(
                        session_id=session_id,
                        update=update,
                        user_id=user_id,
                    )
                )
                profile = profile_resp.model_dump(exclude_none=True)
                if proposed_update:
                    events.append(
                        profile_update_proposed_event(
                            update=proposed_update,
                            changed_fields=changed_fields,
                            session_id=session_id,
                        )
                    )
            except Exception:
                logger.warning("预览学习画像更新失败", exc_info=True)
                profile = {}
        else:
            try:
                profile_resp = await self.profile_service.get_or_create_profile(
                    session_id=session_id,
                    user_id=user_id,
                )
                profile = profile_resp.model_dump(exclude_none=True)
            except Exception:
                logger.warning("读取学习画像失败", exc_info=True)
                profile = {}

        await self._record_agent_event(
            state=state,
            started_at=started_at,
            agent_name="ProfileAgent",
            node_name="profile",
            status="success",
            input_chars=len(state["user_message"]),
            output_chars=len(str(profile)),
            event_metadata={
                "updated": bool(update),
                "proposed": bool(update),
                "profile_fields": sorted(profile.keys()),
            },
            llm_holder=self.profile_agent,
        )
        return {"profile": profile, "events": events}

    async def _dispatch_node(self, state: OrchestratorState) -> OrchestratorState:
        started_at = time.perf_counter()
        await self._record_agent_event(
            state=state,
            started_at=started_at,
            agent_name="Orchestrator",
            node_name="dispatch",
            status="success",
            input_chars=len(state["user_message"]),
            event_metadata={
                "topic": state["decision"].topic,
                "update_profile": state["decision"].update_profile,
                "generate_document": state["decision"].generate_document,
                "is_tutor_question": state["decision"].is_tutor_question,
            },
        )
        return {"events": []}

    async def _tutor_node(self, state: OrchestratorState) -> OrchestratorState:
        started_at = time.perf_counter()
        session_id = state["session_id"]
        user_message = state["user_message"]
        decision = state["decision"]
        profile = state.get("profile", {})
        chat_history = state.get("history", [])
        events = [
            agent_status_event(
                agent="TutorAgent",
                status="working",
                message=(
                    "正在按 Study Mode 诊断问题并设计分步提示"
                    if state.get("study_mode")
                    else "正在分析问题并准备解答"
                ),
                session_id=session_id,
            )
        ]

        streamed_parts: list[str] = []
        buffer_parts: list[str] = []
        audit_warnings: list[str] = []
        tutor_warnings: list[str] = []
        audit_allowed = True

        async def flush_tutor_buffer() -> bool:
            nonlocal audit_allowed
            segment = "".join(buffer_parts)
            buffer_parts.clear()
            if not segment:
                return True

            audited_segment, segment_warnings, segment_allowed = (
                await audit_model_output(
                    segment,
                    chat_sid=(
                        f"session-{session_id}:tutor:"
                        f"{len(streamed_parts) + 1}"
                    ),
                )
            )
            audit_warnings.extend(segment_warnings)
            if not segment_allowed:
                audit_allowed = False
                events.append(token_event(token=audited_segment, session_id=session_id))
                return False

            audited_segment = filter_unsafe_fragments(audited_segment)
            streamed_parts.append(audited_segment)
            events.append(token_event(token=audited_segment, session_id=session_id))
            return True

        try:
            async for token in self.tutor_agent.answer_stream(
                user_message,
                profile,
                history=chat_history,
                study_mode=bool(state.get("study_mode")),
                course_id=state.get("course_id"),
            ):
                buffer_parts.append(token)
                current_buffer = "".join(buffer_parts)
                if _should_flush_tutor_buffer(current_buffer):
                    if not await flush_tutor_buffer():
                        break
            if audit_allowed:
                await flush_tutor_buffer()
            answer = "".join(streamed_parts)
        except Exception as exc:
            await self._record_agent_event(
                state=state,
                started_at=started_at,
                agent_name="TutorAgent",
                node_name="tutor",
                status="error",
                input_chars=len(user_message),
                error=str(exc),
                event_metadata={"study_mode": bool(state.get("study_mode"))},
                llm_holder=self.tutor_agent,
            )
            events.append(
                error_event(
                    message=str(exc).strip() or "答疑失败，请稍后重试",
                    session_id=session_id,
                )
            )
            return {"events": events, "stop": True}

        for warning in audit_warnings:
            logger.info("Tutor 内容安全审核警告: %s", warning)

        if audit_allowed:
            guarded_answer, tutor_warnings = guard_content(answer, topic=decision.topic)
        else:
            guarded_answer = answer
        for warning in tutor_warnings:
            logger.info("Tutor 内容防护警告: %s", warning)

        if audit_allowed and guarded_answer.startswith(answer):
            suffix = guarded_answer[len(answer) :]
            if suffix:
                events.append(token_event(token=suffix, session_id=session_id))

        try:
            await self.chat_service.save_message(
                session_id=session_id,
                role="assistant",
                content=guarded_answer,
                turn_id=state["run_id"],
            )
        except Exception:
            logger.warning("保存 assistant 消息失败", exc_info=True)

        await self._update_session_title_if_needed(
            session_id=session_id,
            title=decision.topic[:30] if decision.topic else user_message[:30],
        )

        await self._record_agent_event(
            state=state,
            started_at=started_at,
            agent_name="TutorAgent",
            node_name="tutor",
            status="success",
            input_chars=len(user_message),
            output_chars=len(guarded_answer),
            event_metadata={
                "study_mode": bool(state.get("study_mode")),
                "audit_allowed": audit_allowed,
                "warning_count": len(audit_warnings) + len(tutor_warnings),
            },
            llm_holder=self.tutor_agent,
        )
        events.append(done_event(session_id=session_id))
        return {"events": events, "stop": True}

    async def _plan_resources_node(
        self, state: OrchestratorState
    ) -> OrchestratorState:
        started_at = time.perf_counter()
        session_id = state["session_id"]
        decision = state["decision"]
        try:
            resource_types = await self.planner_agent.plan_resources_async(
                decision.topic,
                state.get("profile", {}),
                decision,
            )
        except Exception as exc:
            await self._record_agent_event(
                state=state,
                started_at=started_at,
                agent_name="PlannerAgent",
                node_name="plan_resources",
                status="error",
                input_chars=len(decision.topic) + len(str(state.get("profile", {}))),
                error=str(exc),
                llm_holder=self.planner_agent,
            )
            raise
        events = [
            agent_status_event(
                agent="PlannerAgent",
                status="working",
                message="正在拆解资源生成任务",
                session_id=session_id,
            ),
            progress_event(
                stage="planning",
                completed=0,
                total=1,
                message="正在规划本轮学习资源",
                session_id=session_id,
            ),
        ]
        if not resource_types:
            await self._record_agent_event(
                state=state,
                started_at=started_at,
                agent_name="PlannerAgent",
                node_name="plan_resources",
                status="success",
                input_chars=len(decision.topic) + len(str(state.get("profile", {}))),
                output_chars=0,
                event_metadata={"resource_types": []},
                llm_holder=self.planner_agent,
            )
            return {
                "resource_types": [],
                "events": [*events, done_event(session_id=session_id)],
                "stop": True,
            }

        intro = _build_resource_intro(
            decision.topic,
            resource_types,
            single_resource=decision.quiz_only,
        )
        await self._record_agent_event(
            state=state,
            started_at=started_at,
            agent_name="PlannerAgent",
            node_name="plan_resources",
            status="success",
            input_chars=len(decision.topic) + len(str(state.get("profile", {}))),
            output_chars=len(",".join(resource_types)),
            event_metadata={"resource_types": resource_types, "quiz_only": decision.quiz_only},
            llm_holder=self.planner_agent,
        )
        return {
            "resource_types": resource_types,
            "assistant_content": intro,
            "generated_resources": {},
            "events": [
                *events,
                progress_event(
                    stage="planning",
                    completed=1,
                    total=1,
                    message="学习资源规划完成",
                    session_id=session_id,
                ),
                token_event(token=intro, session_id=session_id),
            ],
        }

    async def _document_node(self, state: OrchestratorState) -> OrchestratorState:
        started_at = time.perf_counter()
        session_id = state["session_id"]
        decision = state["decision"]
        events = [
            agent_status_event(
                agent="DocAgent",
                status="working",
                message="正在生成学习文档",
                session_id=session_id,
            ),
            progress_event(
                stage="resources",
                completed=0,
                total=max(len(state.get("resource_types", [])), 1),
                message="正在生成学习文档",
                session_id=session_id,
            ),
        ]

        try:
            doc_resource = await self.doc_agent.generate_document(
                decision.topic,
                state.get("profile", {}),
                course_id=state.get("course_id"),
            )
        except Exception as exc:
            await self._record_agent_event(
                state=state,
                started_at=started_at,
                agent_name="DocAgent",
                node_name="document",
                status="error",
                resource_type="document",
                input_chars=len(decision.topic) + len(str(state.get("profile", {}))),
                error=str(exc),
                llm_holder=self.doc_agent,
            )
            events.append(
                error_event(
                    message=str(exc).strip() or "生成学习文档失败，请稍后重试",
                    session_id=session_id,
                )
            )
            return {"events": events, "stop": True}

        generated_resources = dict(state.get("generated_resources", {}))
        generated_resources["document"] = doc_resource
        if doc_resource.wiki_fallback:
            events.append(wiki_fallback_event(session_id=session_id))
        events.append(
            await self._save_and_emit_resource(
                session_id,
                doc_resource,
                turn_id=state["run_id"],
            )
        )
        events.append(
            progress_event(
                stage="resources",
                completed=1,
                total=max(len(state.get("resource_types", [])), 1),
                message="学习文档已生成",
                session_id=session_id,
            )
        )
        await self._record_agent_event(
            state=state,
            started_at=started_at,
            agent_name="DocAgent",
            node_name="document",
            status="success",
            resource_type="document",
            input_chars=len(decision.topic) + len(str(state.get("profile", {}))),
            output_chars=len(doc_resource.content),
            event_metadata={
                "title": doc_resource.title,
                "wiki_fallback": doc_resource.wiki_fallback,
                "source_count": len(doc_resource.sources),
            },
            llm_holder=self.doc_agent,
        )
        return {"generated_resources": generated_resources, "events": events}

    async def _parallel_resources_node(
        self, state: OrchestratorState
    ) -> OrchestratorState:
        started_at = time.perf_counter()
        session_id = state["session_id"]
        decision = state["decision"]
        generated_resources = dict(state.get("generated_resources", {}))
        parallel_types = [
            resource_type
            for resource_type in state.get("resource_types", [])
            if resource_type != "document"
        ]
        if not parallel_types:
            await self._record_agent_event(
                state=state,
                started_at=started_at,
                agent_name="Orchestrator",
                node_name="parallel_resources",
                status="success",
                event_metadata={"resource_types": []},
            )
            return {"events": []}

        decision = state["decision"]
        parallel_msg = _build_resource_status_message(
            parallel_types,
            single_resource=decision.quiz_only,
        )
        events = [
            agent_status_event(
                agent="PlannerAgent",
                status="working",
                message=parallel_msg,
                session_id=session_id,
            )
        ]

        semaphore = asyncio.Semaphore(self._resource_concurrency)

        async def _run_one(resource_type: str) -> tuple[str, AgentResource | None]:
            async with semaphore:
                try:
                    resource = await self._generate_resource(
                        resource_type=resource_type,
                        topic=decision.topic,
                        profile=state.get("profile", {}),
                        generated_resources=generated_resources,
                        state=state,
                    )
                    return resource_type, resource
                except Exception as exc:
                    logger.warning("资源 %s 生成失败，跳过: %s", resource_type, exc)
                    return resource_type, None

        first_layer = [
            resource_type
            for resource_type in parallel_types
            if resource_type != "code"
        ]
        second_layer = [
            resource_type
            for resource_type in parallel_types
            if resource_type == "code"
        ]

        all_failed = True
        total_resources = max(len(state.get("resource_types", [])), 1)
        completed_resources = 1 if "document" in generated_resources else 0
        for layer in (first_layer, second_layer):
            if not layer:
                continue
            results = await asyncio.gather(*[_run_one(t) for t in layer])
            for resource_type, resource in results:
                if resource is None:
                    continue
                all_failed = False
                generated_resources[resource_type] = resource
                events.append(
                    await self._save_and_emit_resource(
                        session_id,
                        resource,
                        turn_id=state["run_id"],
                    )
                )
                completed_resources += 1
                events.append(
                    progress_event(
                        stage="resources",
                        completed=completed_resources,
                        total=total_resources,
                        message=f"{resource.title} 已生成",
                        session_id=session_id,
                    )
                )

        if all_failed:
            events.append(
                error_event(
                    message="所有学习资源生成失败，请稍后重试",
                    session_id=session_id,
                )
            )
            return {"events": events, "stop": True}

        await self._record_agent_event(
            state=state,
            started_at=started_at,
            agent_name="Orchestrator",
            node_name="parallel_resources",
            status="success",
            input_chars=len(decision.topic),
            output_chars=sum(
                len(r.content) for r in generated_resources.values()
            ),
            event_metadata={"resource_types": parallel_types},
        )
        return {"generated_resources": generated_resources, "events": events}

    async def _finalize_node(self, state: OrchestratorState) -> OrchestratorState:
        started_at = time.perf_counter()
        session_id = state["session_id"]
        decision = state["decision"]
        user_message = state["user_message"]
        assistant_content = state.get("assistant_content", "")

        if assistant_content:
            try:
                await self.chat_service.save_message(
                    session_id=session_id,
                    role="assistant",
                    content=assistant_content,
                    turn_id=state["run_id"],
                )
            except Exception:
                logger.warning("保存 assistant 消息失败", exc_info=True)

        await self._update_session_title_if_needed(
            session_id=session_id,
            title=decision.topic[:30] if decision.topic else user_message[:30],
        )
        await self._record_agent_event(
            state=state,
            started_at=started_at,
            agent_name="Orchestrator",
            node_name="finalize",
            status="success",
            input_chars=len(assistant_content),
            event_metadata={
                "resource_count": len(state.get("generated_resources", {})),
            },
        )
        return {"events": [done_event(session_id=session_id)], "stop": True}

    def _after_route(
        self, state: OrchestratorState
    ) -> Literal["profile", "dispatch"]:
        decision = state["decision"]
        return "profile" if decision.update_profile else "dispatch"

    def _after_dispatch(
        self, state: OrchestratorState
    ) -> Literal["tutor", "plan_resources"]:
        decision = state["decision"]
        if decision.is_tutor_question and not decision.generate_document:
            return "tutor"
        return "plan_resources"

    def _after_plan_resources(
        self, state: OrchestratorState
    ) -> Literal["document", "parallel_resources", "end"]:
        if state.get("stop"):
            return "end"
        resource_types = state.get("resource_types", [])
        if "document" in resource_types:
            return "document"
        if resource_types:
            return "parallel_resources"
        return "end"

    def _after_document(
        self, state: OrchestratorState
    ) -> Literal["parallel_resources", "finalize", "end"]:
        if state.get("stop"):
            return "end"
        parallel_types = [
            resource_type
            for resource_type in state.get("resource_types", [])
            if resource_type != "document"
        ]
        return "parallel_resources" if parallel_types else "finalize"

    def _after_parallel_resources(
        self, state: OrchestratorState
    ) -> Literal["finalize", "end"]:
        return "end" if state.get("stop") else "finalize"

    async def _save_and_emit_resource(
        self,
        session_id: int,
        resource: AgentResource,
        *,
        turn_id: str | None = None,
    ) -> SSEEvent:
        content = resource.content
        audited, audit_warnings, audit_allowed = await audit_model_output(
            content,
            chat_sid=f"session-{session_id}:{resource.resource_type}",
        )
        content = audited
        for warning in audit_warnings:
            logger.info("内容安全审核警告 [%s]: %s", resource.title, warning)

        if audit_allowed and resource.resource_type not in ("quiz", "ppt", "video"):
            guarded, warnings = guard_content(
                content,
                wiki_context=resource.wiki_context,
                topic=resource.knowledge_point,
                confidence=resource.confidence or None,
            )
            content = guarded
            for warning in warnings:
                logger.info("内容防护警告 [%s]: %s", resource.title, warning)

            if resource.sources:
                content += format_source_citations(
                    resource.sources, confidence=resource.confidence
                )

        try:
            resource_model = await self.chat_service.save_resource(
                session_id=session_id,
                resource_type=resource.resource_type,
                title=resource.title,
                content=content,
                knowledge_point=resource.knowledge_point,
                agent_name=resource.agent_name,
                turn_id=turn_id,
            )
            resource_id = resource_model.id
        except Exception:
            resource_id = None
            logger.warning("保存资源到数据库失败", exc_info=True)

        return resource_card_event(
            resource=ResourceCardPayload(
                id=resource_id,
                resource_type=resource.resource_type,
                title=resource.title,
                content=content,
                knowledge_point=resource.knowledge_point,
                agent_name=resource.agent_name,
                turn_id=turn_id,
                confidence=resource.confidence,
                sources=resource.sources,
            ),
            session_id=session_id,
        )

    async def _generate_resource(
        self,
        *,
        resource_type: str,
        topic: str,
        profile: dict[str, Any],
        generated_resources: dict[str, AgentResource],
        state: OrchestratorState,
    ) -> AgentResource:
        started_at = time.perf_counter()
        agent_name, agent = self._resource_agent(resource_type)
        document = generated_resources.get("document")
        quiz = generated_resources.get("quiz")
        input_chars = (
            len(topic)
            + len(str(profile))
            + (len(document.content) if document else 0)
            + (len(quiz.content) if quiz else 0)
        )

        try:
            if resource_type == "document":
                resource = await self.doc_agent.generate_document(
                    topic,
                    profile,
                    course_id=state.get("course_id"),
                )
            elif resource_type == "quiz":
                resource = await self.quiz_agent.generate_quiz(
                    topic,
                    profile,
                    document_content=document.content if document else None,
                    course_id=state.get("course_id"),
                )
            elif resource_type == "code":
                resource = await self.code_agent.generate_code(
                    topic,
                    profile,
                    document_content=document.content if document else None,
                    quiz_content=quiz.content if quiz else None,
                    course_id=state.get("course_id"),
                )
            elif resource_type == "mindmap":
                resource = await self.media_agent.generate_mindmap(
                    topic,
                    profile,
                    document_content=document.content if document else None,
                    course_id=state.get("course_id"),
                )
            elif resource_type == "ppt":
                resource = await self.media_agent.generate_ppt_images(
                    topic,
                    profile,
                    document_content=document.content if document else None,
                    course_id=state.get("course_id"),
                )
            elif resource_type == "reading":
                resource = await self.reading_agent.generate_reading(
                    topic,
                    profile,
                    document_content=document.content if document else None,
                    course_id=state.get("course_id"),
                )
            elif resource_type == "animation":
                resource = await self.media_agent.generate_animation_script(
                    topic,
                    profile,
                    document_content=document.content if document else None,
                    course_id=state.get("course_id"),
                )
            elif resource_type == "video":
                resource = await self.video_agent.generate_videos(
                    topic,
                    profile,
                    document_content=document.content if document else None,
                    course_id=state.get("course_id"),
                )
            else:
                raise ValueError(f"不支持的资源类型：{resource_type}")
        except Exception as exc:
            await self._record_agent_event(
                state=state,
                started_at=started_at,
                agent_name=agent_name,
                node_name="generate_resource",
                status="error",
                resource_type=resource_type,
                input_chars=input_chars,
                error=str(exc),
                llm_holder=agent,
            )
            raise

        await self._record_agent_event(
            state=state,
            started_at=started_at,
            agent_name=agent_name,
            node_name="generate_resource",
            status="success",
            resource_type=resource_type,
            input_chars=input_chars,
            output_chars=len(resource.content),
            event_metadata={
                "title": resource.title,
                "source_count": len(resource.sources),
                **resource.metadata,
            },
            llm_holder=agent,
        )
        return resource

    def _resource_agent(self, resource_type: str) -> tuple[str, object]:
        if resource_type == "document":
            return "DocAgent", self.doc_agent
        if resource_type == "quiz":
            return "QuizAgent", self.quiz_agent
        if resource_type == "code":
            return "CodeAgent", self.code_agent
        if resource_type in {"mindmap", "ppt", "animation"}:
            return "MediaAgent", self.media_agent
        if resource_type == "reading":
            return "ReadingAgent", self.reading_agent
        if resource_type == "video":
            return "VideoAgent", self.video_agent
        return "UnknownAgent", self

    async def _update_session_title_if_needed(
        self,
        *,
        session_id: int,
        title: str,
    ) -> None:
        try:
            session_obj = await self.chat_service.get_session(session_id)
            if session_obj is not None and session_obj.title == "新学习会话":
                await self.chat_service.update_session_title(session_id, title)
        except Exception:
            logger.warning("更新会话标题失败", exc_info=True)


def _estimate_tokens(char_count: int) -> int:
    if char_count <= 0:
        return 0
    return max(1, round(char_count / 4))


def _llm_provider_name(llm_client: object | None) -> str | None:
    if llm_client is None:
        return None
    name = llm_client.__class__.__name__
    if name == "FallbackLLMClient":
        primary = getattr(llm_client, "primary", None)
        fallback = getattr(llm_client, "fallback", None)
        primary_name = primary.__class__.__name__ if primary is not None else "unknown"
        fallback_name = fallback.__class__.__name__ if fallback is not None else "unknown"
        return f"{primary_name}+{fallback_name}"
    return name
