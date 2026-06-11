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
from app.agents.router_agent import RouterAgent
from app.agents.tutor_agent import TutorAgent
from app.core.llm import BaseLLMClient
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
        "profile_updated",
        "agent_status",
        "token",
    ]
    assert events[0].payload["agent"] == "RouterAgent"
    assert events[3].payload["agent"] == "PlannerAgent"
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
        doc_llm=ErrorLLMClient("星火调用失败"),
    )

    events = asyncio.run(_collect_events(orchestrator, "帮我复习反向传播"))

    event_types = [event.type for event in events]
    assert event_types[-1] == "error"
    assert _resource_types(events) == []
    assert "done" not in event_types


def test_orchestrator_stops_when_quiz_generation_fails() -> None:
    orchestrator = _build_orchestrator(
        quiz_llm=ErrorLLMClient("练习题生成失败"),
    )

    events = asyncio.run(_collect_events(orchestrator, "帮我复习反向传播"))

    event_types = [event.type for event in events]
    assert event_types[-1] == "error"
    # quiz 和 code 并行，quiz 失败会导致整个并行批次失败，只保留 document
    assert _resource_types(events) == ["document"]
    assert "done" not in event_types


def test_orchestrator_stops_when_code_generation_fails() -> None:
    orchestrator = _build_orchestrator(
        code_llm=ErrorLLMClient("代码实践生成失败"),
    )

    events = asyncio.run(_collect_events(orchestrator, "帮我复习反向传播"))

    event_types = [event.type for event in events]
    assert event_types[-1] == "error"
    # code 和 quiz 并行，code 失败会导致整个并行批次失败
    assert _resource_types(events) == ["document"]
    assert "done" not in event_types


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
