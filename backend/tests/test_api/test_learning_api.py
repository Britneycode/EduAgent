from __future__ import annotations

import json

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.learning import (
    get_agent_observability,
    get_learning_dashboard,
    get_review_queue,
    record_activity,
    submit_quiz,
    update_review_item,
)
from app.models.chat import ChatSession
from app.models.learning import LearningActivity, LearningPath
from app.models.resource import GeneratedResource
from app.models.user import User
from app.schemas.learning import (
    QuizAnswer,
    QuizSubmitRequest,
    RecordActivityRequest,
    ReviewItemUpdateRequest,
)
from app.services.learning_path_service import LearningPathService


@pytest.mark.asyncio
async def test_submit_quiz_scores_only_objective_questions(
    async_session: AsyncSession,
) -> None:
    user = User(username="quiz_objective_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    chat_session = ChatSession(title="练习会话", user_id=user.id)
    async_session.add(chat_session)
    await async_session.commit()
    await async_session.refresh(chat_session)

    content = json.dumps(
        {
            "questions": [
                {
                    "id": 1,
                    "type": "choice",
                    "question": "哪一项正确？",
                    "options": ["A. 正确选项", "B. 干扰项"],
                    "answer": "A",
                    "explanation": "A 正确。",
                },
                {
                    "id": 2,
                    "type": "short_answer",
                    "question": "简述核心思想。",
                    "options": [],
                    "answer": "参考答案",
                    "explanation": "开放题只记录答案。",
                },
            ]
        },
        ensure_ascii=False,
    )
    resource = GeneratedResource(
        session_id=chat_session.id,
        resource_type="quiz",
        title="混合练习",
        content=content,
        knowledge_point="反向传播",
        agent_name="QuizAgent",
    )
    async_session.add(resource)
    await async_session.commit()
    await async_session.refresh(resource)

    response = await submit_quiz(
        QuizSubmitRequest(
            resource_id=resource.id,
            answers=[
                QuizAnswer(question_id=1, user_answer="A"),
                QuizAnswer(question_id=2, user_answer="我自己的表述"),
            ],
            duration_sec=30,
        ),
        db=async_session,
        user=user,
    )

    assert response.score == 100
    assert response.total == 1
    assert response.correct_count == 1
    assert response.duration_sec == 30
    assert response.accuracy_by_type == {"choice": 100.0}
    assert response.weak_points == []

    review_queue = await get_review_queue(db=async_session, user=user)
    assert review_queue == []


@pytest.mark.asyncio
async def test_wrong_objective_question_enters_review_queue_and_can_be_mastered(
    async_session: AsyncSession,
) -> None:
    user = User(username="quiz_review_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    chat_session = ChatSession(title="错题会话", user_id=user.id)
    async_session.add(chat_session)
    await async_session.commit()
    await async_session.refresh(chat_session)

    content = json.dumps(
        {
            "questions": [
                {
                    "id": 1,
                    "type": "choice",
                    "question": "A* 搜索的评价函数通常包含什么？",
                    "options": ["A. g(n)+h(n)", "B. 仅 h(n)"],
                    "answer": "A",
                    "explanation": "A* 同时考虑已走代价和启发式估计。",
                }
            ]
        },
        ensure_ascii=False,
    )
    resource = GeneratedResource(
        session_id=chat_session.id,
        resource_type="quiz",
        title="A* 练习",
        content=content,
        knowledge_point="A* 搜索",
        agent_name="QuizAgent",
    )
    async_session.add(resource)
    await async_session.commit()
    await async_session.refresh(resource)

    response = await submit_quiz(
        QuizSubmitRequest(
            resource_id=resource.id,
            answers=[QuizAnswer(question_id=1, user_answer="B")],
            duration_sec=20,
        ),
        db=async_session,
        user=user,
    )

    assert response.score == 0
    assert response.weak_points == ["A* 搜索"]
    assert response.accuracy_by_type == {"choice": 0.0}

    queue = await get_review_queue(db=async_session, user=user)
    assert len(queue) == 1
    assert queue[0].knowledge_point == "A* 搜索"
    assert queue[0].correct_answer == "A"

    dashboard = await get_learning_dashboard(db=async_session, user=user)
    assert dashboard.summary.pending_review_count == 1

    updated = await update_review_item(
        item_id=queue[0].id,
        request=ReviewItemUpdateRequest(mastered=True),
        db=async_session,
        user=user,
    )
    assert updated.status == "mastered"

    assert await get_review_queue(db=async_session, user=user) == []


@pytest.mark.asyncio
async def test_learning_dashboard_endpoint_returns_summary(
    async_session: AsyncSession,
) -> None:
    user = User(username="dashboard_api_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    response = await get_learning_dashboard(db=async_session, user=user)

    assert response.summary.total_activities == 0
    assert len(response.activity_trend) == 7
    assert response.recommendations


@pytest.mark.asyncio
async def test_agent_observability_endpoint_returns_recent_runs(
    async_session: AsyncSession,
) -> None:
    user = User(username="agent_observer_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    chat_session = ChatSession(title="观测会话", user_id=user.id)
    async_session.add(chat_session)
    await async_session.commit()
    await async_session.refresh(chat_session)

    service = LearningPathService(session=async_session)
    await service.record_agent_run_event(
        run_id="run-1",
        user_id=user.id,
        session_id=chat_session.id,
        agent_name="RouterAgent",
        node_name="route",
        status="success",
        duration_ms=12,
        input_chars=20,
        output_chars=8,
        token_estimate=7,
        llm_used=True,
        llm_provider="StubLLMClient",
    )
    await service.record_agent_run_event(
        run_id="run-1",
        user_id=user.id,
        session_id=chat_session.id,
        agent_name="QuizAgent",
        node_name="generate_resource",
        resource_type="quiz",
        status="error",
        duration_ms=45,
        input_chars=120,
        output_chars=0,
        token_estimate=30,
        error="练习题生成失败",
    )

    response = await get_agent_observability(
        limit=20,
        db=async_session,
        user=user,
    )

    assert response.summary.total_runs == 1
    assert response.summary.total_events == 2
    assert response.summary.error_events == 1
    assert response.recent_runs[0].status == "error"
    assert response.agent_stats[0].agent_name == "QuizAgent"
    assert response.recent_events[0].agent_name == "QuizAgent"


@pytest.mark.asyncio
async def test_record_activity_rejects_foreign_path_and_resource(
    async_session: AsyncSession,
) -> None:
    owner = User(username="activity_owner", hashed_password="hashed")
    other = User(username="activity_other", hashed_password="hashed")
    async_session.add_all([owner, other])
    await async_session.commit()
    await async_session.refresh(owner)
    await async_session.refresh(other)

    owner_path = LearningPath(
        user_id=owner.id,
        title="我的路径",
        goal_topic="反向传播",
        nodes=[{"concept": "反向传播", "status": "pending"}],
        status="active",
    )
    other_path = LearningPath(
        user_id=other.id,
        title="他人路径",
        goal_topic="A* 搜索",
        nodes=[{"concept": "A* 搜索", "status": "pending"}],
        status="active",
    )
    owner_session = ChatSession(title="我的会话", user_id=owner.id)
    other_session = ChatSession(title="他人会话", user_id=other.id)
    async_session.add_all([owner_path, other_path, owner_session, other_session])
    await async_session.commit()
    await async_session.refresh(owner_path)
    await async_session.refresh(other_path)
    await async_session.refresh(owner_session)
    await async_session.refresh(other_session)

    owner_resource = GeneratedResource(
        session_id=owner_session.id,
        resource_type="note",
        title="我的资源",
        content="content",
    )
    other_resource = GeneratedResource(
        session_id=other_session.id,
        resource_type="note",
        title="他人资源",
        content="content",
    )
    async_session.add_all([owner_resource, other_resource])
    await async_session.commit()
    await async_session.refresh(owner_resource)
    await async_session.refresh(other_resource)

    response = await record_activity(
        RecordActivityRequest(
            path_id=owner_path.id,
            resource_id=owner_resource.id,
            activity_type="resource_view",
            knowledge_point="反向传播",
        ),
        db=async_session,
        user=owner,
    )
    assert response.path_id == owner_path.id
    assert response.resource_id == owner_resource.id

    with pytest.raises(HTTPException) as path_error:
        await record_activity(
            RecordActivityRequest(
                path_id=other_path.id,
                activity_type="resource_view",
            ),
            db=async_session,
            user=owner,
        )
    assert path_error.value.status_code == 404

    with pytest.raises(HTTPException) as resource_error:
        await record_activity(
            RecordActivityRequest(
                resource_id=other_resource.id,
                activity_type="resource_view",
            ),
            db=async_session,
            user=owner,
        )
    assert resource_error.value.status_code == 404

    result = await async_session.execute(
        select(LearningActivity).where(LearningActivity.user_id == owner.id)
    )
    assert len(result.scalars().all()) == 1
