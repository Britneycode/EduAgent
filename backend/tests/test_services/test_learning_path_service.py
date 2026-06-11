from __future__ import annotations

from datetime import timezone, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import BaseLLMClient
from app.models.chat import ChatSession
from app.models.learning import LearningPath
from app.models.resource import GeneratedResource
from app.models.user import User
from app.services.learning_path_service import (
    LearningActivityOwnershipError,
    LearningPathService,
)
from app.wiki.graph import KnowledgeGraph


class StubLLMClient(BaseLLMClient):
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    async def generate_text(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


class ErrorLLMClient(BaseLLMClient):
    async def generate_text(self, prompt: str) -> str:
        raise RuntimeError("llm failed")


@pytest.mark.asyncio
async def test_generate_path_persists_prerequisites_for_dag(
    async_session: AsyncSession,
) -> None:
    user = User(username="path_dag_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    graph = KnowledgeGraph()
    graph.load_from_dict(
        {
            "concepts": {
                "梯度下降": {
                    "chapter": "ch4",
                    "section": "ch4_s4",
                    "prerequisites": [],
                    "description": "参数优化方法",
                },
                "多层感知机": {
                    "chapter": "ch5",
                    "section": "ch5_s1",
                    "prerequisites": ["梯度下降"],
                    "description": "多层神经网络",
                },
                "反向传播": {
                    "chapter": "ch5",
                    "section": "ch5_s1",
                    "prerequisites": ["多层感知机", "梯度下降"],
                    "description": "梯度计算算法",
                },
            }
        }
    )
    service = LearningPathService(session=async_session)

    path = await service.generate_path(
        user_id=user.id,
        goal_topic="反向传播",
        knowledge_graph=graph,
    )

    assert [node["concept"] for node in path.nodes] == [
        "梯度下降",
        "多层感知机",
        "反向传播",
    ]
    assert path.nodes[0]["prerequisites"] == []
    assert path.nodes[1]["prerequisites"] == ["梯度下降"]
    assert path.nodes[2]["prerequisites"] == ["多层感知机", "梯度下降"]


@pytest.mark.asyncio
async def test_generate_path_uses_selected_course_graph(
    async_session: AsyncSession,
) -> None:
    user = User(username="path_course_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    graph = KnowledgeGraph()
    graph.load_from_dict(
        {
            "concepts": {
                "搜索": {
                    "chapter": "ch01",
                    "section": "",
                    "prerequisites": [],
                    "description": "AI 搜索",
                }
            }
        },
        course_id="ai_intro",
    )
    graph.load_from_dict(
        {
            "concepts": {
                "变量与基础数据类型": {
                    "chapter": "py01",
                    "section": "",
                    "prerequisites": [],
                    "description": "Python 类型",
                },
                "函数定义与参数": {
                    "chapter": "py02",
                    "section": "",
                    "prerequisites": ["变量与基础数据类型"],
                    "description": "函数封装",
                },
            }
        },
        course_id="python_basics",
        clear=False,
    )
    service = LearningPathService(session=async_session)

    path = await service.generate_path(
        user_id=user.id,
        goal_topic="函数定义与参数",
        knowledge_graph=graph,
        course_id="python_basics",
    )

    assert [node["concept"] for node in path.nodes] == [
        "变量与基础数据类型",
        "函数定义与参数",
    ]
    assert {node["course_id"] for node in path.nodes} == {"python_basics"}


@pytest.mark.asyncio
async def test_generate_path_uses_llm_plan_when_valid(
    async_session: AsyncSession,
) -> None:
    user = User(username="path_llm_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    graph = KnowledgeGraph()
    graph.load_from_dict(
        {
            "concepts": {
                "梯度下降": {
                    "chapter": "ch4",
                    "section": "ch4_s4",
                    "prerequisites": [],
                    "description": "参数优化方法",
                },
                "多层感知机": {
                    "chapter": "ch5",
                    "section": "ch5_s1",
                    "prerequisites": ["梯度下降"],
                    "description": "多层神经网络",
                },
                "反向传播": {
                    "chapter": "ch5",
                    "section": "ch5_s1",
                    "prerequisites": ["多层感知机", "梯度下降"],
                    "description": "梯度计算算法",
                },
            }
        }
    )
    llm = StubLLMClient(
        """
        {
          "title": "反向传播冲刺路径",
          "nodes": [
            {"concept": "梯度下降", "status": "completed", "description": "先确认优化基础"},
            {"concept": "反向传播", "status": "pending", "description": "重点突破链式法则"}
          ]
        }
        """
    )
    service = LearningPathService(session=async_session)

    path = await service.generate_path(
        user_id=user.id,
        goal_topic="反向传播",
        profile={"knowledge_base": {"梯度下降": "掌握"}, "weak_points": ["反向传播"]},
        knowledge_graph=graph,
        llm_client=llm,
    )

    assert path.title == "反向传播冲刺路径"
    assert [node["concept"] for node in path.nodes] == ["梯度下降", "反向传播"]
    assert path.nodes[0]["status"] == "completed"
    assert path.nodes[1]["description"] == "重点突破链式法则"
    assert "候选知识点" in llm.prompts[0]


@pytest.mark.asyncio
async def test_generate_path_falls_back_when_llm_fails(
    async_session: AsyncSession,
) -> None:
    user = User(username="path_llm_fallback_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    graph = KnowledgeGraph()
    graph.load_from_dict(
        {
            "concepts": {
                "梯度下降": {
                    "chapter": "ch4",
                    "section": "ch4_s4",
                    "prerequisites": [],
                    "description": "参数优化方法",
                },
                "反向传播": {
                    "chapter": "ch5",
                    "section": "ch5_s1",
                    "prerequisites": ["梯度下降"],
                    "description": "梯度计算算法",
                },
            }
        }
    )
    service = LearningPathService(session=async_session)

    path = await service.generate_path(
        user_id=user.id,
        goal_topic="反向传播",
        knowledge_graph=graph,
        llm_client=ErrorLLMClient(),
    )

    assert path.title == "反向传播 学习路径"
    assert [node["concept"] for node in path.nodes] == ["梯度下降", "反向传播"]


@pytest.mark.asyncio
async def test_apply_quiz_result_updates_matching_path_node(
    async_session: AsyncSession,
) -> None:
    user = User(username="path_quiz_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    service = LearningPathService(session=async_session)
    path = await service.generate_path(user_id=user.id, goal_topic="反向传播")

    updated_count = await service.apply_quiz_result_to_paths(
        user_id=user.id,
        knowledge_point="反向传播",
        score=86,
    )
    updated_path = await service.get_path(path.id, user_id=user.id)

    assert updated_count == 1
    assert updated_path is not None
    assert updated_path.nodes[0]["status"] == "completed"
    assert service.compute_progress(updated_path) == 1.0


@pytest.mark.asyncio
async def test_apply_quiz_result_marks_partial_score_in_progress(
    async_session: AsyncSession,
) -> None:
    user = User(username="path_partial_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    service = LearningPathService(session=async_session)
    path = await service.generate_path(user_id=user.id, goal_topic="梯度下降")

    updated_count = await service.apply_quiz_result_to_paths(
        user_id=user.id,
        knowledge_point="梯度下降",
        score=60,
    )
    updated_path = await service.get_path(path.id, user_id=user.id)

    assert updated_count == 1
    assert updated_path is not None
    assert updated_path.nodes[0]["status"] == "in_progress"


@pytest.mark.asyncio
async def test_apply_quiz_result_unlocks_next_available_node(
    async_session: AsyncSession,
) -> None:
    user = User(username="path_unlock_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    graph = KnowledgeGraph()
    graph.load_from_dict(
        {
            "concepts": {
                "梯度下降": {
                    "chapter": "ch4",
                    "section": "ch4_s4",
                    "prerequisites": [],
                    "description": "参数优化方法",
                },
                "多层感知机": {
                    "chapter": "ch5",
                    "section": "ch5_s1",
                    "prerequisites": ["梯度下降"],
                    "description": "多层神经网络",
                },
                "反向传播": {
                    "chapter": "ch5",
                    "section": "ch5_s1",
                    "prerequisites": ["多层感知机"],
                    "description": "梯度计算算法",
                },
            }
        }
    )
    service = LearningPathService(session=async_session)
    path = await service.generate_path(
        user_id=user.id,
        goal_topic="反向传播",
        knowledge_graph=graph,
    )

    updated_count = await service.apply_quiz_result_to_paths(
        user_id=user.id,
        knowledge_point="梯度下降",
        score=92,
    )
    updated_path = await service.get_path(path.id, user_id=user.id)

    assert updated_count == 1
    assert updated_path is not None
    assert [node["status"] for node in updated_path.nodes] == [
        "completed",
        "in_progress",
        "pending",
    ]


@pytest.mark.asyncio
async def test_record_activity_requires_owned_path_and_resource(
    async_session: AsyncSession,
) -> None:
    owner = User(username="service_activity_owner", hashed_password="hashed")
    other = User(username="service_activity_other", hashed_password="hashed")
    async_session.add_all([owner, other])
    await async_session.commit()
    await async_session.refresh(owner)
    await async_session.refresh(other)

    other_path = LearningPath(
        user_id=other.id,
        title="他人路径",
        goal_topic="A* 搜索",
        nodes=[{"concept": "A* 搜索", "status": "pending"}],
        status="active",
    )
    other_session = ChatSession(title="他人会话", user_id=other.id)
    async_session.add_all([other_path, other_session])
    await async_session.commit()
    await async_session.refresh(other_path)
    await async_session.refresh(other_session)

    other_resource = GeneratedResource(
        session_id=other_session.id,
        resource_type="note",
        title="他人资源",
        content="content",
    )
    async_session.add(other_resource)
    await async_session.commit()
    await async_session.refresh(other_resource)

    service = LearningPathService(session=async_session)
    with pytest.raises(LearningActivityOwnershipError):
        await service.record_activity(
            user_id=owner.id,
            activity_type="resource_view",
            path_id=other_path.id,
        )

    with pytest.raises(LearningActivityOwnershipError):
        await service.record_activity(
            user_id=owner.id,
            activity_type="resource_view",
            resource_id=other_resource.id,
        )


@pytest.mark.asyncio
async def test_dashboard_aggregates_learning_effect_metrics(
    async_session: AsyncSession,
) -> None:
    user = User(username="dashboard_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    service = LearningPathService(session=async_session)
    path = await service.generate_path(user_id=user.id, goal_topic="反向传播")
    await service.update_node_status(
        path_id=path.id,
        user_id=user.id,
        concept="反向传播",
        status="completed",
    )

    quiz = await service.record_activity(
        user_id=user.id,
        activity_type="quiz",
        knowledge_point="反向传播",
        score=72,
        duration_sec=120,
    )
    review = await service.record_activity(
        user_id=user.id,
        activity_type="resource_view",
        knowledge_point="梯度下降",
        duration_sec=60,
    )
    quiz.created_at = datetime.now(timezone.utc) - timedelta(days=1)
    review.created_at = datetime.now(timezone.utc)
    await async_session.commit()

    dashboard = await service.get_dashboard(user_id=user.id)

    assert dashboard["summary"]["total_activities"] == 2
    assert dashboard["summary"]["total_duration_sec"] == 180
    assert dashboard["summary"]["quiz_count"] == 1
    assert dashboard["summary"]["average_quiz_score"] == 72
    assert dashboard["summary"]["completed_nodes"] == 1
    assert dashboard["knowledge_mastery"][0]["knowledge_point"] == "反向传播"
    assert dashboard["knowledge_mastery"][0]["level"] == "in_progress"
    assert len(dashboard["activity_trend"]) == 7
    assert dashboard["path_progress"][0]["progress"] == 1.0
    assert dashboard["recent_activities"][0]["activity_type"] == "resource_view"
