from __future__ import annotations

import asyncio

from app.agents.code_agent import CodeAgent
from app.agents.doc_agent import DocAgent
from app.agents.media_agent import MediaAgent
from app.agents.orchestrator import Orchestrator
from app.agents.planner_agent import PlannerAgent
from app.agents.profile_agent import ProfileAgent
from app.agents.quiz_agent import QuizAgent
from app.agents.reading_agent import ReadingAgent
from app.agents.resource_types import AgentResource
from app.agents.router_agent import RouteDecision, RouterAgent
from app.agents.tutor_agent import TutorAgent
from app.agents.video_agent import VideoAgent
from app.core.llm import BaseLLMClient
from app.core.video_search import VideoSearchResult
from app.schemas.chat import SSEEvent
from app.services.chat_service import ChatService
from app.services.profile_service import ProfileService


class StubLLMClient(BaseLLMClient):
    def __init__(self, response: str) -> None:
        self.response = response

    async def generate_text(self, prompt: str) -> str:
        return self.response


class ErrorLLMClient(BaseLLMClient):
    def __init__(self, message: str) -> None:
        self.message = message

    async def generate_text(self, prompt: str) -> str:
        raise RuntimeError(self.message)


class RecordingLearningService:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def record_agent_run_event(self, **kwargs):
        self.events.append(kwargs)
        return kwargs


class StubVideoSearchClient:
    async def search(self, query: str) -> list[VideoSearchResult]:
        return [
            VideoSearchResult(
                title="反向传播视频讲解",
                url="https://www.bilibili.com/video/BV123",
                snippet="链式法则和梯度计算。",
                score=0.9,
            )
        ]


def _build_orchestrator(
    *,
    doc_llm: BaseLLMClient | None = None,
    quiz_llm: BaseLLMClient | None = None,
    code_llm: BaseLLMClient | None = None,
    tutor_llm: BaseLLMClient | None = None,
    media_llm: BaseLLMClient | None = None,
    reading_llm: BaseLLMClient | None = None,
    learning_service=None,
) -> Orchestrator:
    return Orchestrator(
        router_agent=RouterAgent(),
        profile_agent=ProfileAgent(),
        planner_agent=PlannerAgent(),
        doc_agent=DocAgent(
            llm_client=doc_llm
            or StubLLMClient("这是面向图文结合复习需求的反向传播讲义正文。")
        ),
        quiz_agent=QuizAgent(
            llm_client=quiz_llm
            or StubLLMClient("1. 基础理解题\n答案：用于检验概念理解。")
        ),
        code_agent=CodeAgent(
            llm_client=code_llm
            or StubLLMClient("一、代码目标\n使用 Python 演示梯度计算。")
        ),
        media_agent=MediaAgent(llm_client=media_llm or StubLLMClient("思维导图内容")),
        reading_agent=ReadingAgent(
            llm_client=reading_llm or StubLLMClient("拓展阅读内容")
        ),
        video_agent=VideoAgent(search_client=StubVideoSearchClient()),
        tutor_agent=TutorAgent(
            llm_client=tutor_llm or StubLLMClient("这是 Tutor 回答")
        ),
        profile_service=ProfileService(session=None),
        chat_service=ChatService(session=None),
        learning_service=learning_service,
    )


async def _collect_events(
    orchestrator: Orchestrator, user_message: str
) -> list[SSEEvent]:
    return [
        event
        async for event in orchestrator.run(
            session_id=1,
            user_message=user_message,
        )
    ]


def _resource_types(events: list[SSEEvent]) -> list[str]:
    return [
        event.payload["resource_type"]
        for event in events
        if event.type == "resource_card"
    ]


def test_orchestrator_exposes_langgraph_workflow_nodes() -> None:
    orchestrator = _build_orchestrator()

    assert orchestrator.graph_node_names() == (
        "route",
        "profile",
        "dispatch",
        "tutor",
        "plan_resources",
        "document",
        "parallel_resources",
        "finalize",
    )


def test_orchestrator_yields_expected_event_sequence() -> None:
    orchestrator = _build_orchestrator()

    events = asyncio.run(
        _collect_events(
            orchestrator,
            "我是计算机专业大三学生，想复习反向传播，最好图文结合",
        )
    )

    event_types = [event.type for event in events]
    assert event_types[0:5] == [
        "agent_status",
        "agent_status",
        "profile_update_proposed",
        "agent_status",
        "progress",
    ]
    assert events[0].payload["agent"] == "RouterAgent"
    assert events[3].payload["agent"] == "PlannerAgent"
    assert "token" in event_types
    assert event_types[-1] == "done"
    assert set(_resource_types(events)) == {
        "document",
        "quiz",
        "code",
        "mindmap",
        "reading",
    }

    resource_card_indexes = [
        index for index, event in enumerate(events) if event.type == "resource_card"
    ]
    assert len(resource_card_indexes) == 5


def test_orchestrator_records_agent_observability_events() -> None:
    learning_service = RecordingLearningService()
    orchestrator = _build_orchestrator(learning_service=learning_service)

    asyncio.run(_collect_events(orchestrator, "帮我复习反向传播"))

    agent_names = {event["agent_name"] for event in learning_service.events}
    assert {
        "RouterAgent",
        "Orchestrator",
        "PlannerAgent",
        "DocAgent",
        "QuizAgent",
        "CodeAgent",
        "MediaAgent",
        "ReadingAgent",
    }.issubset(agent_names)
    assert all(event["run_id"] for event in learning_service.events)
    assert all(event["duration_ms"] >= 0 for event in learning_service.events)
    assert any(
        event["resource_type"] == "quiz" and event["status"] == "success"
        for event in learning_service.events
    )


def test_orchestrator_stops_when_document_generation_fails() -> None:
    orchestrator = _build_orchestrator(
        doc_llm=ErrorLLMClient("LLM 调用失败"),
    )

    events = asyncio.run(_collect_events(orchestrator, "帮我复习反向传播"))

    event_types = [event.type for event in events]
    assert event_types[-1] == "error"
    assert _resource_types(events) == []
    assert "done" not in event_types


def test_orchestrator_skips_failed_quiz_and_finishes_other_resources() -> None:
    orchestrator = _build_orchestrator(
        quiz_llm=ErrorLLMClient("练习题生成失败"),
    )

    events = asyncio.run(_collect_events(orchestrator, "帮我复习反向传播"))

    event_types = [event.type for event in events]
    assert event_types[-1] == "done"
    assert set(_resource_types(events)) == {
        "document",
        "code",
        "mindmap",
        "reading",
    }
    assert "quiz" not in _resource_types(events)


def test_orchestrator_skips_failed_code_and_finishes_other_resources() -> None:
    orchestrator = _build_orchestrator(
        code_llm=ErrorLLMClient("代码实践生成失败"),
    )

    events = asyncio.run(_collect_events(orchestrator, "帮我复习反向传播"))

    event_types = [event.type for event in events]
    assert event_types[-1] == "done"
    assert set(_resource_types(events)) == {
        "document",
        "quiz",
        "mindmap",
        "reading",
    }
    assert "code" not in _resource_types(events)


def test_parallel_resources_preserve_quiz_before_code_dependency() -> None:
    orchestrator = _build_orchestrator()
    orchestrator._resource_concurrency = 2
    starts: list[str] = []
    active_first_layer: set[str] = set()
    peak_first_layer = 0

    async def fake_generate_resource(
        *,
        resource_type: str,
        topic: str,
        profile: dict,
        generated_resources: dict[str, AgentResource],
        state: dict,
    ) -> AgentResource:
        nonlocal peak_first_layer
        if resource_type == "code":
            assert "quiz" in generated_resources
        else:
            active_first_layer.add(resource_type)
            peak_first_layer = max(peak_first_layer, len(active_first_layer))

        starts.append(resource_type)
        await asyncio.sleep(0.01)
        active_first_layer.discard(resource_type)
        return AgentResource(
            title=f"{resource_type} title",
            resource_type=resource_type,
            content=f"{resource_type} content",
            knowledge_point=topic,
            agent_name="TestAgent",
        )

    async def fake_save_and_emit_resource(
        session_id: int,
        resource: AgentResource,
        *,
        turn_id: str | None = None,
    ) -> SSEEvent:
        return SSEEvent(
            type="resource_card",
            session_id=session_id,
            payload={"resource_type": resource.resource_type},
        )

    orchestrator._generate_resource = fake_generate_resource  # type: ignore[method-assign]
    orchestrator._save_and_emit_resource = fake_save_and_emit_resource  # type: ignore[method-assign]
    state = {
        "session_id": 1,
        "user_id": 1,
        "run_id": "test-run",
        "decision": RouteDecision(
            update_profile=False,
            generate_document=True,
            is_tutor_question=False,
            topic="反向传播",
            resource_types=["quiz", "mindmap", "code"],
        ),
        "resource_types": ["quiz", "mindmap", "code"],
        "profile": {},
        "generated_resources": {
            "document": AgentResource(
                title="document title",
                resource_type="document",
                content="document content",
                knowledge_point="反向传播",
                agent_name="DocAgent",
            )
        },
    }

    result = asyncio.run(orchestrator._parallel_resources_node(state))

    assert peak_first_layer == 2
    assert starts.index("code") > starts.index("quiz")
    assert set(result["generated_resources"]) == {
        "document",
        "quiz",
        "mindmap",
        "code",
    }


def test_orchestrator_generates_video_resource_for_video_request() -> None:
    orchestrator = _build_orchestrator()

    events = asyncio.run(_collect_events(orchestrator, "帮我找反向传播相关视频学习"))

    assert events[-1].type == "done"
    streamed_text = "".join(
        event.payload["token"] for event in events if event.type == "token"
    )
    status_messages = [
        event.payload["message"] for event in events if event.type == "agent_status"
    ]
    assert "相关视频" in streamed_text
    assert "练习题" not in streamed_text
    assert "正在搜索相关视频..." in status_messages
    assert _resource_types(events) == ["video"]
    video_card = next(event for event in events if event.type == "resource_card")
    assert "反向传播视频讲解" in video_card.payload["content"]
    assert video_card.payload["agent_name"] == "VideoAgent"


def test_tutor_answer_is_guarded_before_streaming_to_client() -> None:
    orchestrator = _build_orchestrator(
        tutor_llm=StubLLMClient("可以执行 rm -rf / 来清理目录。")
    )

    events = asyncio.run(_collect_events(orchestrator, "什么是反向传播？"))

    streamed_answer = "".join(
        event.payload["token"] for event in events if event.type == "token"
    )

    assert "rm -rf" not in streamed_answer
    assert "[已过滤]" in streamed_answer
    assert "注意：以上内容由 AI 基于知识库生成" in streamed_answer
    assert events[-1].type == "done"
