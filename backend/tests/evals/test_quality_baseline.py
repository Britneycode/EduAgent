from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from app.agents.content_guard import guard_content
from app.agents.profile_agent import ProfileAgent
from app.agents.quiz_agent import QuizAgent
from app.agents.router_agent import RouterAgent
from app.core.llm import BaseLLMClient
from app.wiki.embeddings import BaseEmbedding
from app.wiki.rag_engine import RAGEngine
from app.wiki.vector_store import VectorStore

FIXTURE_DIR = Path(__file__).with_name("fixtures")
ALLOWED_QUESTION_TYPES = {"choice", "judge", "short_answer"}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}


class EvalEmbedding(BaseEmbedding):
    KEYWORDS = ["反向传播", "链式法则", "梯度", "解释器", "脚本", "搜索"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    @property
    def dimension(self) -> int:
        return len(self.KEYWORDS)

    def _embed(self, text: str) -> list[float]:
        return [float(text.count(keyword)) for keyword in self.KEYWORDS]


class FixtureQuizLLMClient(BaseLLMClient):
    async def generate_text(self, prompt: str) -> str:
        assert "反向传播" in prompt
        return "```json\n" + _load_text_fixture("quiz_payload.json") + "\n```"


def _load_json_fixture(name: str) -> Any:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _load_text_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _case_ids(cases: list[dict[str, Any]]) -> list[str]:
    return [str(case["id"]) for case in cases]


PROFILE_CASES = _load_json_fixture("profile_cases.json")
ROUTER_CASES = _load_json_fixture("router_cases.json")
RAG_CASES = _load_json_fixture("rag_cases.json")
SAFETY_CASES = _load_json_fixture("safety_cases.json")


@pytest.mark.parametrize("case", PROFILE_CASES, ids=_case_ids(PROFILE_CASES))
def test_eval_profile_extraction_baseline(case: dict[str, Any]) -> None:
    """画像抽取基线：固定自然语言画像样例必须抽出关键字段。"""
    actual = ProfileAgent().extract_profile_update(case["input"])

    for key, expected_value in case["expected"].items():
        assert actual.get(key) == expected_value, (
            f"{case['id']} expected {key}={expected_value!r}, "
            f"got {actual.get(key)!r}; full={actual!r}"
        )


@pytest.mark.parametrize("case", ROUTER_CASES, ids=_case_ids(ROUTER_CASES))
def test_eval_router_baseline(case: dict[str, Any]) -> None:
    """路由基线：固定学习意图样例必须稳定落到正确处理链路。"""
    decision = RouterAgent().route(case["input"])
    actual = {
        "update_profile": decision.update_profile,
        "generate_document": decision.generate_document,
        "is_tutor_question": decision.is_tutor_question,
        "topic": decision.topic,
        "resource_types": decision.resource_types,
    }

    for key, expected_value in case["expected"].items():
        assert actual.get(key) == expected_value, (
            f"{case['id']} expected {key}={expected_value!r}, "
            f"got {actual.get(key)!r}; full={actual!r}"
        )


@pytest.mark.parametrize("case", RAG_CASES, ids=_case_ids(RAG_CASES))
def test_eval_rag_hit_baseline(case: dict[str, Any]) -> None:
    """RAG 命中基线：混合检索必须命中预期课程与来源片段。"""
    asyncio.run(_assert_rag_case(case))


async def _assert_rag_case(case: dict[str, Any]) -> None:
    rag_engine = _build_eval_rag_engine()

    results = await rag_engine.search(
        case["query"],
        top_k=3,
        course_id=case["course_id"],
        min_score=float(case["min_score"]),
    )
    assert results, f"{case['id']} expected at least one hit"
    assert results[0].chunk_id == case["expected_top_chunk"], (
        f"{case['id']} expected top chunk {case['expected_top_chunk']!r}, "
        f"got {results[0].chunk_id!r}; hits={[r.chunk_id for r in results]!r}"
    )
    assert case["expected_phrase"] in results[0].content

    context = await rag_engine.build_context_with_sources(
        case["query"],
        top_k=1,
        course_id=case["course_id"],
    )
    assert context.sources[0].chunk_id == case["expected_top_chunk"]
    assert case["expected_phrase"] in context.sources[0].snippet
    assert context.confidence >= float(case["min_score"])


def _build_eval_rag_engine() -> RAGEngine:
    store = VectorStore(EvalEmbedding())
    store.add(
        chunk_ids=[
            "ai_intro:ch5_backprop",
            "ai_intro:ch1_search",
            "python_basics:py1_runtime",
        ],
        documents=[
            "反向传播通过链式法则高效计算梯度，是训练神经网络的核心算法。",
            "搜索算法用于状态空间探索，包括宽度优先搜索和启发式搜索。",
            "Python 解释器负责运行脚本，适合初学者理解程序执行流程。",
        ],
        metadatas=[
            {
                "course_id": "ai_intro",
                "chapter": "ch5",
                "section": "ch5_s1",
                "title": "反向传播",
            },
            {
                "course_id": "ai_intro",
                "chapter": "ch1",
                "section": "ch1_s2",
                "title": "搜索算法",
            },
            {
                "course_id": "python_basics",
                "chapter": "py1",
                "section": "py1_s1",
                "title": "Python 解释器",
            },
        ],
    )
    return RAGEngine(store)


def test_eval_quiz_structure_baseline() -> None:
    """题目结构基线：结构化题目必须满足训练模式前端可消费的数据契约。"""
    resource = asyncio.run(
        QuizAgent(llm_client=FixtureQuizLLMClient()).generate_quiz(
            "反向传播",
            {"learning_goal": "复习", "cognitive_style": "图文结合"},
            document_content="反向传播通过链式法则计算梯度。",
        )
    )
    payload = json.loads(resource.content)

    settings = payload["settings"]
    assert settings["mode"] == "training"
    assert settings["question_count"] == 3
    assert settings["time_limit_sec"] == 480

    questions = payload["questions"]
    assert len(questions) == 3
    assert {question["type"] for question in questions} == ALLOWED_QUESTION_TYPES
    for question in questions:
        _assert_quiz_question_shape(question)


def _assert_quiz_question_shape(question: dict[str, Any]) -> None:
    assert isinstance(question["id"], int)
    assert question["type"] in ALLOWED_QUESTION_TYPES
    assert question["difficulty"] in ALLOWED_DIFFICULTIES
    assert str(question["knowledge_point"]).strip()
    assert str(question["question"]).strip()
    assert str(question["answer"]).strip()
    assert str(question["explanation"]).strip()
    assert isinstance(question["options"], list)
    if question["type"] in {"choice", "judge"}:
        assert len(question["options"]) >= 2


@pytest.mark.parametrize("case", SAFETY_CASES, ids=_case_ids(SAFETY_CASES))
def test_eval_content_safety_baseline(case: dict[str, Any]) -> None:
    """内容安全基线：高风险片段要过滤，低置信和虚构引用要暴露警告。"""
    filtered, warnings = guard_content(
        case["input"],
        wiki_context=case.get("wiki_context"),
        topic=case.get("topic"),
        confidence=case.get("confidence"),
    )

    for unsafe_fragment in case.get("expect_removed", []):
        assert unsafe_fragment not in filtered, (
            f"{case['id']} expected {unsafe_fragment!r} to be removed, "
            f"got {filtered!r}"
        )
    for expected_text in case.get("expect_present", []):
        assert expected_text in filtered, (
            f"{case['id']} expected filtered content to include {expected_text!r}, "
            f"got {filtered!r}"
        )
    for expected_warning in case.get("expect_warning_contains", []):
        assert any(expected_warning in warning for warning in warnings), (
            f"{case['id']} expected warning containing {expected_warning!r}, "
            f"got {warnings!r}"
        )
