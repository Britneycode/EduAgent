from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
AI_INTRO_DIR = BACKEND_ROOT / "knowledge" / "ai_intro"


def test_ai_intro_demo_scenario_references_existing_course_assets() -> None:
    scenario = _read_json(AI_INTRO_DIR / "demo_scenario.json")
    metadata = _read_json(AI_INTRO_DIR / "metadata.json")
    graph = _read_json(AI_INTRO_DIR / "knowledge_graph.json")

    chapter_ids = {chapter["chapter_id"] for chapter in metadata["chapters"]}
    node_ids = {node["id"] for node in graph["nodes"]}

    assert scenario["scenario_id"] == "ai_intro_backprop_learning_loop"
    assert scenario["duration_minutes"] <= 10
    assert scenario["course_context"]["target_chapter_id"] in chapter_ids
    assert scenario["course_context"]["target_knowledge_point_id"] in node_ids

    referenced_nodes = [
        *scenario["course_context"]["prerequisite_knowledge_point_ids"],
        *scenario["course_context"]["follow_up_knowledge_point_ids"],
    ]
    missing_nodes = [node_id for node_id in referenced_nodes if node_id not in node_ids]
    assert missing_nodes == []


def test_ai_intro_demo_scenario_covers_full_learning_loop() -> None:
    scenario = _read_json(AI_INTRO_DIR / "demo_scenario.json")

    demo_inputs = scenario["demo_inputs"]
    assert "反向传播" in demo_inputs["resource_prompt"]
    assert "辅导模式" in demo_inputs["study_mode_prompt"]
    assert "链式法则" in demo_inputs["wiki_search_query"]

    pages = {item["path"] for item in scenario["expected_pages"]}
    assert {"/chat", "/profile", "/path", "/analytics", "/wiki", "/teacher"} <= pages

    expected_quiz = scenario["expected_quiz"]
    question_ids = {question["id"] for question in expected_quiz["questions"]}
    answer_ids = set(expected_quiz["demo_answers"])
    assert answer_ids == question_ids
    assert len(expected_quiz["questions"]) >= 3
    assert _has_intentional_wrong_answer(expected_quiz) is True
    assert expected_quiz["expected_review_item_count"] >= 1


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _has_intentional_wrong_answer(expected_quiz: dict[str, Any]) -> bool:
    answers = expected_quiz["demo_answers"]
    return any(
        answers.get(question["id"]) != question["answer"]
        for question in expected_quiz["questions"]
    )
