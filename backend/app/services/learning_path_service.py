from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from datetime import timezone, datetime, timedelta
from typing import Any

from app.core.llm import BaseLLMClient
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.chat import ChatSession
from app.models.learning import (
    AgentRunEvent,
    LearningActivity,
    LearningPath,
    ReviewItem,
)
from app.models.profile import StudentProfile
from app.models.resource import GeneratedResource
from app.models.user import User

logger = logging.getLogger(__name__)


class LearningActivityOwnershipError(ValueError):
    """Raised when an activity references data outside the current user."""


class LearningPathService:
    """学习路径与学习活动服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate_path(
        self,
        user_id: int,
        goal_topic: str,
        title: str | None = None,
        profile: dict[str, Any] | None = None,
        knowledge_graph: Any | None = None,
        llm_client: BaseLLMClient | None = None,
        course_id: str | None = None,
    ) -> LearningPath:
        """根据目标知识点和学生画像生成个性化学习路径。"""
        rule_nodes = self._build_nodes(
            goal_topic,
            profile,
            knowledge_graph,
            course_id=course_id,
        )
        llm_plan = await self._build_llm_path(
            goal_topic=goal_topic,
            profile=profile,
            rule_nodes=rule_nodes,
            llm_client=llm_client,
            course_id=course_id,
        )
        nodes = llm_plan["nodes"] if llm_plan is not None else rule_nodes
        path_title = title or f"{goal_topic} 学习路径"
        if title is None and llm_plan is not None and llm_plan.get("title"):
            path_title = str(llm_plan["title"])[:255]

        path = LearningPath(
            user_id=user_id,
            title=path_title,
            goal_topic=goal_topic,
            nodes=nodes,
            status="active",
        )
        self.session.add(path)
        await self.session.commit()
        await self.session.refresh(path)
        return path

    async def _build_llm_path(
        self,
        *,
        goal_topic: str,
        profile: dict[str, Any] | None,
        rule_nodes: list[dict[str, Any]],
        llm_client: BaseLLMClient | None,
        course_id: str | None = None,
    ) -> dict[str, Any] | None:
        if llm_client is None or not rule_nodes:
            return None

        prompt = self._build_llm_path_prompt(
            goal_topic=goal_topic,
            profile=profile or {},
            candidates=rule_nodes,
            course_id=course_id,
        )
        try:
            raw = await llm_client.generate_text(prompt)
            payload = self._extract_json_object(raw)
            nodes = self._validate_llm_nodes(payload.get("nodes"), rule_nodes)
        except Exception:
            logger.warning("LLM 学习路径规划失败，回退规则路径", exc_info=True)
            return None

        if not nodes:
            return None
        return {
            "title": payload.get("title") if isinstance(payload.get("title"), str) else None,
            "nodes": nodes,
        }

    def _build_llm_path_prompt(
        self,
        *,
        goal_topic: str,
        profile: dict[str, Any],
        candidates: list[dict[str, Any]],
        course_id: str | None = None,
    ) -> str:
        candidate_payload = [
            {
                "concept": node.get("concept", ""),
                "chapter": node.get("chapter", ""),
                "section": node.get("section", ""),
                "description": node.get("description", ""),
                "prerequisites": node.get("prerequisites", []),
                "status": node.get("status", "pending"),
                "course_id": node.get("course_id", ""),
            }
            for node in candidates
        ]
        profile_payload = {
            "knowledge_base": profile.get("knowledge_base", {}),
            "weak_points": profile.get("weak_points", []),
            "interest_areas": profile.get("interest_areas", []),
            "learning_goal": profile.get("learning_goal"),
            "learning_pace": profile.get("learning_pace"),
            "weekly_hours": profile.get("weekly_hours"),
        }
        return "\n".join(
            [
                "你是 EduAgent 的学习路径规划 Agent。",
                "请只从给定候选知识点中选择并排序，不要编造新的知识点。",
                "要结合学生画像：已掌握的知识可标为 completed，薄弱点应提前复习。",
                "输出必须是 JSON 对象，不要添加 Markdown 代码块。",
                '格式：{"title":"...","nodes":[{"concept":"...","chapter":"...","section":"...","description":"...","prerequisites":["..."],"status":"pending|in_progress|completed|skipped"}]}',
                f"目标知识点：{goal_topic}",
                f"课程 ID：{course_id or '未限定'}",
                "学生画像：",
                json.dumps(profile_payload, ensure_ascii=False),
                "候选知识点：",
                json.dumps(candidate_payload, ensure_ascii=False),
            ]
        )

    def _extract_json_object(self, raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                raise
            data = json.loads(match.group(0))
        if not isinstance(data, dict):
            raise ValueError("LLM path payload must be an object")
        return data

    def _validate_llm_nodes(
        self,
        raw_nodes: Any,
        rule_nodes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not isinstance(raw_nodes, list):
            return []

        candidates = {
            str(node.get("concept")): node
            for node in rule_nodes
            if str(node.get("concept", "")).strip()
        }
        valid_statuses = {"pending", "in_progress", "completed", "skipped"}
        nodes: list[dict[str, Any]] = []
        seen: set[str] = set()

        for raw_node in raw_nodes:
            if not isinstance(raw_node, dict):
                continue
            concept = str(raw_node.get("concept") or "").strip()
            if not concept or concept in seen or concept not in candidates:
                continue

            base = candidates[concept]
            status = str(raw_node.get("status") or base.get("status") or "pending")
            if status not in valid_statuses:
                status = str(base.get("status") or "pending")
            description = raw_node.get("description")
            prerequisites = raw_node.get("prerequisites")
            candidate_prerequisites = set(base.get("prerequisites") or [])
            normalized_prerequisites = [
                str(item)
                for item in prerequisites
                if isinstance(item, str) and item in candidate_prerequisites
            ] if isinstance(prerequisites, list) else list(base.get("prerequisites") or [])

            nodes.append(
                {
                    "concept": concept,
                    "course_id": str(base.get("course_id") or ""),
                    "chapter": str(raw_node.get("chapter") or base.get("chapter") or ""),
                    "section": str(raw_node.get("section") or base.get("section") or ""),
                    "description": (
                        str(description).strip()
                        if isinstance(description, str) and description.strip()
                        else str(base.get("description") or "")
                    ),
                    "prerequisites": normalized_prerequisites,
                    "status": status,
                }
            )
            seen.add(concept)

        if not nodes:
            return []

        goal = str(rule_nodes[-1].get("concept", ""))
        if goal and goal not in seen:
            nodes.append(rule_nodes[-1])
        return nodes

    def _build_nodes(
        self,
        goal_topic: str,
        profile: dict[str, Any] | None,
        knowledge_graph: Any | None,
        course_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """构建学习节点序列：拓扑排序 + 画像过滤。"""
        if knowledge_graph is None:
            return [
                {
                    "concept": goal_topic,
                    "course_id": course_id or "",
                    "chapter": "",
                    "section": "",
                    "description": "",
                    "status": "pending",
                }
            ]

        prerequisites = knowledge_graph.get_all_prerequisites(
            goal_topic,
            course_id=course_id,
        )
        concept_names = [*prerequisites, goal_topic]

        known_concepts: set[str] = set()
        if profile:
            kb = profile.get("knowledge_base", {})
            if isinstance(kb, dict):
                for concept, level in kb.items():
                    if isinstance(level, str) and level in ("熟练", "掌握"):
                        known_concepts.add(concept)
                    elif isinstance(level, (int, float)) and level >= 0.8:
                        known_concepts.add(concept)

        nodes: list[dict[str, Any]] = []
        concept_set = set(concept_names)
        for concept in concept_names:
            concept_node = knowledge_graph.get_concept(
                concept,
                course_id=course_id,
            )
            status = "completed" if concept in known_concepts else "pending"
            prerequisites = (
                [
                    prereq
                    for prereq in concept_node.prerequisites
                    if prereq in concept_set
                ]
                if concept_node
                else []
            )
            nodes.append(
                {
                    "concept": concept,
                    "course_id": concept_node.course_id if concept_node else course_id or "",
                    "chapter": concept_node.chapter if concept_node else "",
                    "section": concept_node.section if concept_node else "",
                    "description": concept_node.description if concept_node else "",
                    "prerequisites": prerequisites,
                    "status": status,
                }
            )

        return nodes

    async def list_paths(self, user_id: int) -> list[LearningPath]:
        result = await self.session.execute(
            select(LearningPath)
            .where(LearningPath.user_id == user_id)
            .order_by(LearningPath.updated_at.desc())
            .execution_options(populate_existing=True)
        )
        return list(result.scalars().all())

    async def get_path(self, path_id: int, user_id: int) -> LearningPath | None:
        result = await self.session.execute(
            select(LearningPath).where(
                LearningPath.id == path_id,
                LearningPath.user_id == user_id,
            )
        )
        return result.scalars().first()

    async def update_node_status(
        self, path_id: int, user_id: int, concept: str, status: str
    ) -> LearningPath | None:
        """更新路径中某个知识点的学习状态。"""
        path = await self.get_path(path_id, user_id)
        if path is None:
            return None

        nodes = list(path.nodes)
        updated = False
        for node in nodes:
            if node.get("concept") == concept:
                node["status"] = status
                updated = True
                break

        if not updated:
            return None

        path.nodes = nodes
        flag_modified(path, "nodes")
        path.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(path)
        return path

    async def get_recommendations(
        self, path_id: int, user_id: int
    ) -> dict[str, Any]:
        """获取学习路径的推荐：下一步要学的知识点。"""
        path = await self.get_path(path_id, user_id)
        if path is None:
            return {"next_concepts": [], "completed_count": 0, "total_count": 0, "message": "路径不存在"}

        nodes = path.nodes or []
        completed = [n for n in nodes if n.get("status") == "completed"]
        pending = [n for n in nodes if n.get("status") == "pending"]

        next_concepts = [n["concept"] for n in pending[:3]]
        total = len(nodes)
        done = len(completed)

        if not pending:
            message = "恭喜！你已完成该学习路径的所有知识点。"
        elif done == 0:
            message = f"开始学习吧！推荐从 {next_concepts[0]} 开始。"
        else:
            message = f"已完成 {done}/{total}，继续加油！"

        return {
            "next_concepts": next_concepts,
            "completed_count": done,
            "total_count": total,
            "message": message,
        }

    async def record_activity(
        self,
        user_id: int,
        activity_type: str,
        path_id: int | None = None,
        knowledge_point: str | None = None,
        resource_id: int | None = None,
        result: dict[str, Any] | None = None,
        score: float | None = None,
        duration_sec: int | None = None,
        detail: str | None = None,
    ) -> LearningActivity:
        """记录一次学习活动。"""
        await self._ensure_activity_associations_owned(
            user_id=user_id,
            path_id=path_id,
            resource_id=resource_id,
        )
        activity = LearningActivity(
            user_id=user_id,
            path_id=path_id,
            activity_type=activity_type,
            knowledge_point=knowledge_point,
            resource_id=resource_id,
            result=result,
            score=score,
            duration_sec=duration_sec,
            detail=detail,
        )
        self.session.add(activity)
        await self.session.commit()
        await self.session.refresh(activity)
        return activity

    async def _ensure_activity_associations_owned(
        self,
        *,
        user_id: int,
        path_id: int | None,
        resource_id: int | None,
    ) -> None:
        if path_id is not None:
            owned_path_id = await self.session.scalar(
                select(LearningPath.id).where(
                    LearningPath.id == path_id,
                    LearningPath.user_id == user_id,
                )
            )
            if owned_path_id is None:
                raise LearningActivityOwnershipError("学习活动关联对象不存在")

        if resource_id is not None:
            owned_resource_id = await self.session.scalar(
                select(GeneratedResource.id)
                .join(ChatSession, GeneratedResource.session_id == ChatSession.id)
                .where(
                    GeneratedResource.id == resource_id,
                    ChatSession.user_id == user_id,
                )
            )
            if owned_resource_id is None:
                raise LearningActivityOwnershipError("学习活动关联对象不存在")

    async def record_agent_run_event(
        self,
        *,
        run_id: str,
        user_id: int,
        session_id: int,
        agent_name: str,
        node_name: str,
        status: str,
        duration_ms: int,
        resource_type: str | None = None,
        llm_provider: str | None = None,
        llm_used: bool = False,
        input_chars: int = 0,
        output_chars: int = 0,
        token_estimate: int = 0,
        error: str | None = None,
        event_metadata: dict[str, Any] | None = None,
    ) -> AgentRunEvent:
        """记录一次 Agent 节点或资源生成事件。"""
        event = AgentRunEvent(
            run_id=run_id,
            user_id=user_id,
            session_id=session_id,
            agent_name=agent_name,
            node_name=node_name,
            resource_type=resource_type,
            status=status,
            duration_ms=max(0, int(duration_ms)),
            llm_provider=llm_provider,
            llm_used=llm_used,
            input_chars=max(0, int(input_chars)),
            output_chars=max(0, int(output_chars)),
            token_estimate=max(0, int(token_estimate)),
            error=error,
            event_metadata=event_metadata or {},
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def apply_quiz_result_to_paths(
        self,
        user_id: int,
        knowledge_point: str,
        score: float,
    ) -> int:
        """根据练习结果更新包含该知识点的学习路径节点状态。"""
        if not knowledge_point:
            return 0

        result = await self.session.execute(
            select(LearningPath).where(
                LearningPath.user_id == user_id,
                LearningPath.status == "active",
            )
        )
        paths = list(result.scalars().all())
        if score >= 80:
            next_status = "completed"
        elif score >= 50:
            next_status = "in_progress"
        else:
            next_status = "pending"

        updated_count = 0
        for path in paths:
            nodes = list(path.nodes or [])
            changed = False
            for node in nodes:
                if node.get("concept") != knowledge_point:
                    continue
                if node.get("status") != next_status:
                    node["status"] = next_status
                    flag_modified(path, "nodes")
                    changed = True
                break
            if score >= 80:
                changed = self._mark_next_available_node_in_progress(nodes) or changed
            if changed:
                path.nodes = nodes
                path.updated_at = datetime.now(timezone.utc)
                self.session.add(path)
                updated_count += 1

        if updated_count:
            await self.session.commit()

        return updated_count

    async def record_quiz_mistakes(
        self,
        *,
        user_id: int,
        resource_id: int,
        activity_id: int,
        knowledge_point: str | None,
        questions: list[dict[str, Any]],
        results: list[Any],
    ) -> int:
        """把答错题写入错题本，已存在的错题会重新排入复习队列。"""
        question_map = {
            int(question.get("id")): question
            for question in questions
            if isinstance(question.get("id"), int)
        }
        now = datetime.now(timezone.utc)
        changed_count = 0

        for result in results:
            if bool(getattr(result, "correct", False)):
                continue
            question_id = int(getattr(result, "question_id"))
            question = question_map.get(question_id, {})
            if not _is_reviewable_question(question):
                continue
            existing = await self.session.scalar(
                select(ReviewItem).where(
                    ReviewItem.user_id == user_id,
                    ReviewItem.resource_id == resource_id,
                    ReviewItem.question_id == question_id,
                )
            )
            if existing is None:
                self.session.add(
                    ReviewItem(
                        user_id=user_id,
                        resource_id=resource_id,
                        activity_id=activity_id,
                        knowledge_point=knowledge_point,
                        question_id=question_id,
                        question_type=str(question.get("type") or "unknown"),
                        question_text=str(question.get("question") or ""),
                        user_answer=str(getattr(result, "user_answer", "")),
                        correct_answer=str(getattr(result, "correct_answer", "")),
                        explanation=_optional_text(question.get("explanation")),
                        status="pending",
                        next_review_at=now,
                    )
                )
            else:
                existing.activity_id = activity_id
                existing.knowledge_point = knowledge_point
                existing.question_type = str(question.get("type") or existing.question_type)
                existing.question_text = str(question.get("question") or existing.question_text)
                existing.user_answer = str(getattr(result, "user_answer", ""))
                existing.correct_answer = str(getattr(result, "correct_answer", ""))
                existing.explanation = _optional_text(question.get("explanation"))
                existing.status = "pending"
                existing.next_review_at = now
                existing.updated_at = now
            changed_count += 1

        if changed_count:
            await self.session.commit()
        return changed_count

    async def get_review_queue(
        self,
        *,
        user_id: int,
        limit: int = 20,
    ) -> list[ReviewItem]:
        """获取当前到期的错题复习队列。"""
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(ReviewItem)
            .where(
                ReviewItem.user_id == user_id,
                ReviewItem.status.in_(("pending", "reviewing")),
                or_(ReviewItem.next_review_at.is_(None), ReviewItem.next_review_at <= now),
            )
            .order_by(ReviewItem.next_review_at.asc(), ReviewItem.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_review_item(
        self,
        *,
        user_id: int,
        item_id: int,
        mastered: bool,
    ) -> ReviewItem | None:
        """标记错题复习结果。"""
        item = await self.session.scalar(
            select(ReviewItem).where(
                ReviewItem.id == item_id,
                ReviewItem.user_id == user_id,
            )
        )
        if item is None:
            return None

        now = datetime.now(timezone.utc)
        item.review_count += 1
        item.last_reviewed_at = now
        item.updated_at = now
        if mastered:
            item.status = "mastered"
            item.next_review_at = None
        else:
            item.status = "reviewing"
            item.next_review_at = now + timedelta(days=_next_review_interval_days(item.review_count))
        await self.session.commit()
        await self.session.refresh(item)
        return item

    def _mark_next_available_node_in_progress(self, nodes: list[dict[str, Any]]) -> bool:
        completed = {
            str(node.get("concept"))
            for node in nodes
            if node.get("status") == "completed"
        }
        for node in nodes:
            if node.get("status") != "pending":
                continue
            prerequisites = [
                str(item)
                for item in node.get("prerequisites", [])
                if isinstance(item, str)
            ]
            if all(prereq in completed for prereq in prerequisites):
                node["status"] = "in_progress"
                return True
        return False

    async def list_activities(
        self,
        user_id: int,
        path_id: int | None = None,
        limit: int = 50,
    ) -> list[LearningActivity]:
        stmt = (
            select(LearningActivity)
            .where(LearningActivity.user_id == user_id)
            .order_by(LearningActivity.created_at.desc())
            .limit(limit)
        )
        if path_id is not None:
            stmt = stmt.where(LearningActivity.path_id == path_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_dashboard(self, user_id: int) -> dict[str, Any]:
        """聚合学习效果评估数据。"""
        paths = await self.list_paths(user_id=user_id)
        activities = await self._list_all_activities(user_id=user_id)

        scored_quizzes = [
            activity
            for activity in activities
            if activity.activity_type == "quiz" and activity.score is not None
        ]
        total_duration = sum(
            activity.duration_sec or 0 for activity in activities
        )
        completed_nodes = 0
        total_nodes = 0
        for path in paths:
            nodes = path.nodes or []
            total_nodes += len(nodes)
            completed_nodes += sum(
                1 for node in nodes if node.get("status") == "completed"
            )

        summary = {
            "total_activities": len(activities),
            "total_duration_sec": total_duration,
            "quiz_count": len([a for a in activities if a.activity_type == "quiz"]),
            "average_quiz_score": _round_average(
                [float(a.score) for a in scored_quizzes]
            ),
            "completed_nodes": completed_nodes,
            "total_nodes": total_nodes,
            "active_paths": len([p for p in paths if p.status == "active"]),
            "pending_review_count": await self.count_due_review_items(user_id=user_id),
        }

        dashboard = {
            "summary": summary,
            "activity_trend": self._build_activity_trend(activities),
            "knowledge_mastery": self._build_knowledge_mastery(scored_quizzes),
            "path_progress": self._build_path_progress(paths),
            "activity_types": self._build_activity_types(activities),
            "recent_activities": [
                {
                    "id": activity.id,
                    "user_id": activity.user_id,
                    "path_id": activity.path_id,
                    "activity_type": activity.activity_type,
                    "knowledge_point": activity.knowledge_point,
                    "resource_id": activity.resource_id,
                    "result": activity.result,
                    "score": activity.score,
                    "duration_sec": activity.duration_sec,
                    "detail": activity.detail,
                    "created_at": activity.created_at.isoformat(),
                }
                for activity in activities[:8]
            ],
            "recommendations": self._build_dashboard_recommendations(
                paths=paths,
                scored_quizzes=scored_quizzes,
                summary=summary,
            ),
        }
        return dashboard

    async def get_agent_observability(
        self,
        *,
        user_id: int,
        limit: int = 30,
    ) -> dict[str, Any]:
        """聚合当前用户的 Agent 运行观测数据。"""
        events = await self.list_agent_run_events(user_id=user_id, limit=limit)
        total_runs = len({event.run_id for event in events})
        total_events = len(events)
        success_events = len([event for event in events if event.status == "success"])
        error_events = len([event for event in events if event.status == "error"])
        total_duration_ms = sum(event.duration_ms for event in events)
        average_duration_ms = (
            round(total_duration_ms / total_events) if total_events else 0
        )

        agent_buckets: dict[str, dict[str, Any]] = {}
        for event in events:
            bucket = agent_buckets.setdefault(
                event.agent_name,
                {
                    "agent_name": event.agent_name,
                    "call_count": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "total_duration_ms": 0,
                    "average_duration_ms": 0,
                    "latest_status": event.status,
                    "resource_types": set(),
                },
            )
            is_first_for_agent = bucket["call_count"] == 0
            bucket["call_count"] += 1
            bucket["success_count"] += 1 if event.status == "success" else 0
            bucket["error_count"] += 1 if event.status == "error" else 0
            bucket["total_duration_ms"] += event.duration_ms
            if is_first_for_agent:
                bucket["latest_status"] = event.status
            if event.resource_type:
                bucket["resource_types"].add(event.resource_type)

        agent_stats = []
        for bucket in agent_buckets.values():
            bucket["average_duration_ms"] = round(
                bucket["total_duration_ms"] / max(bucket["call_count"], 1)
            )
            bucket["resource_types"] = sorted(bucket["resource_types"])
            agent_stats.append(bucket)
        agent_stats.sort(key=lambda item: item["total_duration_ms"], reverse=True)

        recent_runs = self._build_recent_agent_runs(events)

        return {
            "summary": {
                "total_runs": total_runs,
                "total_events": total_events,
                "success_events": success_events,
                "error_events": error_events,
                "average_duration_ms": average_duration_ms,
            },
            "agent_stats": agent_stats,
            "recent_runs": recent_runs,
            "recent_events": [
                self._agent_event_payload(event) for event in events[:limit]
            ],
        }

    async def list_agent_run_events(
        self,
        *,
        user_id: int,
        limit: int = 30,
    ) -> list[AgentRunEvent]:
        result = await self.session.execute(
            select(AgentRunEvent)
            .where(AgentRunEvent.user_id == user_id)
            .order_by(AgentRunEvent.created_at.desc(), AgentRunEvent.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_teacher_dashboard(self) -> dict[str, Any]:
        """聚合教师/助教视角的多用户学习概况。

        当前版本不引入角色权限模型，先提供教学观察所需的数据结构；
        后续可在 API 层接入教师角色校验。
        """
        users = await self._list_all_users()
        profiles = await self._list_all_profiles()
        paths = await self._list_all_paths()
        activities = await self._list_all_activities_for_teacher()
        review_items = await self._list_all_review_items()

        profile_by_user = {profile.user_id: profile for profile in profiles}
        paths_by_user: dict[int, list[LearningPath]] = defaultdict(list)
        activities_by_user: dict[int, list[LearningActivity]] = defaultdict(list)
        pending_reviews_by_user: Counter[int] = Counter()
        review_points_by_user: dict[int, set[str]] = defaultdict(set)
        review_counts_by_point: Counter[str] = Counter()

        for path in paths:
            paths_by_user[path.user_id].append(path)
        for activity in activities:
            activities_by_user[activity.user_id].append(activity)
        for item in review_items:
            if item.status in {"pending", "reviewing"}:
                pending_reviews_by_user[item.user_id] += 1
            if item.knowledge_point:
                review_points_by_user[item.user_id].add(item.knowledge_point)
                review_counts_by_point[item.knowledge_point] += 1

        scored_quizzes = [
            activity
            for activity in activities
            if activity.activity_type == "quiz" and activity.score is not None
        ]
        score_by_point: dict[str, list[float]] = defaultdict(list)
        students_by_point: dict[str, set[int]] = defaultdict(set)
        for activity in scored_quizzes:
            if not activity.knowledge_point:
                continue
            score_by_point[activity.knowledge_point].append(float(activity.score or 0))
            if activity.score is not None and activity.score < 80:
                students_by_point[activity.knowledge_point].add(activity.user_id)

        for profile in profiles:
            for weak_point in profile.weak_points or []:
                students_by_point[str(weak_point)].add(profile.user_id)

        students = [
            self._build_teacher_student_item(
                user=user,
                profile=profile_by_user.get(user.id),
                paths=paths_by_user.get(user.id, []),
                activities=activities_by_user.get(user.id, []),
                pending_reviews=pending_reviews_by_user[user.id],
                review_weak_points=review_points_by_user.get(user.id, set()),
            )
            for user in users
        ]

        weak_points = [
            {
                "knowledge_point": point,
                "affected_students": len(user_ids),
                "review_count": review_counts_by_point[point],
                "average_score": _round_average(score_by_point.get(point, [])),
            }
            for point, user_ids in students_by_point.items()
        ]
        weak_points.sort(
            key=lambda item: (
                -item["affected_students"],
                item["average_score"] if item["average_score"] else 101,
                item["knowledge_point"],
            )
        )

        quiz_performance = [
            {
                "knowledge_point": point,
                "attempts": len(scores),
                "average_score": _round_average(scores),
            }
            for point, scores in score_by_point.items()
        ]
        quiz_performance.sort(key=lambda item: (item["average_score"], -item["attempts"]))

        summary = {
            "student_count": len(users),
            "active_path_count": len([path for path in paths if path.status == "active"]),
            "quiz_count": len(scored_quizzes),
            "average_quiz_score": _round_average(
                [float(activity.score or 0) for activity in scored_quizzes]
            ),
            "pending_review_count": sum(pending_reviews_by_user.values()),
        }
        return {
            "summary": summary,
            "weak_points": weak_points[:8],
            "quiz_performance": quiz_performance[:8],
            "students": students,
            "recommendations": self._build_teacher_recommendations(
                summary=summary,
                weak_points=weak_points,
                quiz_performance=quiz_performance,
            ),
        }

    async def count_due_review_items(self, *, user_id: int) -> int:
        """统计当前待复习错题数量。"""
        return len(await self.get_review_queue(user_id=user_id, limit=1000))

    def compute_progress(self, path: LearningPath) -> float:
        """计算路径完成进度 (0.0 ~ 1.0)。"""
        nodes = path.nodes or []
        if not nodes:
            return 0.0
        completed = sum(1 for n in nodes if n.get("status") == "completed")
        return round(completed / len(nodes), 4)

    async def _list_all_activities(self, user_id: int) -> list[LearningActivity]:
        result = await self.session.execute(
            select(LearningActivity)
            .where(LearningActivity.user_id == user_id)
            .order_by(LearningActivity.created_at.desc())
        )
        return list(result.scalars().all())

    async def _list_all_users(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.id.asc()))
        return list(result.scalars().all())

    async def _list_all_profiles(self) -> list[StudentProfile]:
        result = await self.session.execute(select(StudentProfile))
        return list(result.scalars().all())

    async def _list_all_paths(self) -> list[LearningPath]:
        result = await self.session.execute(select(LearningPath))
        return list(result.scalars().all())

    async def _list_all_activities_for_teacher(self) -> list[LearningActivity]:
        result = await self.session.execute(
            select(LearningActivity).order_by(LearningActivity.created_at.desc())
        )
        return list(result.scalars().all())

    async def _list_all_review_items(self) -> list[ReviewItem]:
        result = await self.session.execute(select(ReviewItem))
        return list(result.scalars().all())

    def _build_recent_agent_runs(
        self,
        events: list[AgentRunEvent],
    ) -> list[dict[str, Any]]:
        buckets: dict[str, list[AgentRunEvent]] = defaultdict(list)
        for event in events:
            buckets[event.run_id].append(event)

        runs: list[dict[str, Any]] = []
        for run_id, run_events in buckets.items():
            sorted_events = sorted(run_events, key=lambda event: event.created_at)
            started_at = sorted_events[0].created_at
            ended_at = sorted_events[-1].created_at
            runs.append(
                {
                    "run_id": run_id,
                    "session_id": sorted_events[-1].session_id,
                    "started_at": started_at.isoformat(),
                    "ended_at": ended_at.isoformat(),
                    "event_count": len(sorted_events),
                    "duration_ms": sum(event.duration_ms for event in sorted_events),
                    "status": (
                        "error"
                        if any(event.status == "error" for event in sorted_events)
                        else "success"
                    ),
                    "agents": [event.agent_name for event in sorted_events],
                }
            )
        runs.sort(key=lambda item: item["ended_at"], reverse=True)
        return runs[:8]

    def _agent_event_payload(self, event: AgentRunEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "run_id": event.run_id,
            "session_id": event.session_id,
            "agent_name": event.agent_name,
            "node_name": event.node_name,
            "resource_type": event.resource_type,
            "status": event.status,
            "duration_ms": event.duration_ms,
            "llm_provider": event.llm_provider,
            "llm_used": event.llm_used,
            "input_chars": event.input_chars,
            "output_chars": event.output_chars,
            "token_estimate": event.token_estimate,
            "error": event.error,
            "event_metadata": event.event_metadata,
            "created_at": event.created_at.isoformat(),
        }

    def _build_teacher_student_item(
        self,
        *,
        user: User,
        profile: StudentProfile | None,
        paths: list[LearningPath],
        activities: list[LearningActivity],
        pending_reviews: int,
        review_weak_points: set[str],
    ) -> dict[str, Any]:
        active_paths = [path for path in paths if path.status == "active"]
        completed_nodes = 0
        total_nodes = 0
        for path in paths:
            nodes = path.nodes or []
            completed_nodes += sum(
                1 for node in nodes if node.get("status") == "completed"
            )
            total_nodes += len(nodes)

        quiz_scores = [
            float(activity.score or 0)
            for activity in activities
            if activity.activity_type == "quiz" and activity.score is not None
        ]
        profile_weak_points = [
            str(item) for item in (profile.weak_points if profile else []) or []
        ]
        weak_points = sorted(set(profile_weak_points) | review_weak_points)

        return {
            "user_id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "major": profile.major if profile else None,
            "grade": profile.grade if profile else None,
            "active_paths": len(active_paths),
            "completed_nodes": completed_nodes,
            "total_nodes": total_nodes,
            "average_quiz_score": _round_average(quiz_scores),
            "pending_reviews": pending_reviews,
            "weak_points": weak_points[:6],
        }

    def _build_activity_trend(
        self, activities: list[LearningActivity]
    ) -> list[dict[str, Any]]:
        today = datetime.now(timezone.utc).date()
        dates = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        buckets: dict[str, dict[str, Any]] = {
            date.isoformat(): {
                "date": date.isoformat(),
                "activity_count": 0,
                "duration_sec": 0,
                "quiz_count": 0,
                "_scores": [],
            }
            for date in dates
        }
        for activity in activities:
            key = _as_utc(activity.created_at).date().isoformat()
            if key not in buckets:
                continue
            bucket = buckets[key]
            bucket["activity_count"] += 1
            bucket["duration_sec"] += activity.duration_sec or 0
            if activity.activity_type == "quiz":
                bucket["quiz_count"] += 1
            if activity.score is not None:
                bucket["_scores"].append(float(activity.score))

        trend: list[dict[str, Any]] = []
        for bucket in buckets.values():
            scores = bucket.pop("_scores")
            bucket["average_score"] = _round_average(scores)
            trend.append(bucket)
        return trend

    def _build_knowledge_mastery(
        self, scored_quizzes: list[LearningActivity]
    ) -> list[dict[str, Any]]:
        score_map: dict[str, list[float]] = defaultdict(list)
        for activity in scored_quizzes:
            if not activity.knowledge_point:
                continue
            score_map[activity.knowledge_point].append(float(activity.score or 0))

        items: list[dict[str, Any]] = []
        for knowledge_point, scores in score_map.items():
            average_score = _round_average(scores)
            items.append(
                {
                    "knowledge_point": knowledge_point,
                    "attempts": len(scores),
                    "average_score": average_score,
                    "level": _mastery_level(average_score),
                }
            )
        return sorted(
            items,
            key=lambda item: (item["average_score"], -item["attempts"]),
        )[:8]

    def _build_path_progress(
        self, paths: list[LearningPath]
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in paths[:6]:
            nodes = path.nodes or []
            completed = sum(
                1 for node in nodes if node.get("status") == "completed"
            )
            items.append(
                {
                    "path_id": path.id,
                    "title": path.title,
                    "goal_topic": path.goal_topic,
                    "progress": self.compute_progress(path),
                    "completed_count": completed,
                    "total_count": len(nodes),
                    "status": path.status,
                }
            )
        return items

    def _build_activity_types(
        self, activities: list[LearningActivity]
    ) -> list[dict[str, Any]]:
        counter = Counter(activity.activity_type for activity in activities)
        return [
            {"activity_type": activity_type, "count": count}
            for activity_type, count in counter.most_common()
        ]

    def _build_dashboard_recommendations(
        self,
        *,
        paths: list[LearningPath],
        scored_quizzes: list[LearningActivity],
        summary: dict[str, Any],
    ) -> list[str]:
        recommendations: list[str] = []
        weak_quizzes = [
            activity
            for activity in scored_quizzes
            if activity.score is not None and activity.score < 80
        ]
        if weak_quizzes:
            weakest = min(weak_quizzes, key=lambda activity: activity.score or 0)
            if weakest.knowledge_point:
                recommendations.append(
                    f"优先复习「{weakest.knowledge_point}」，最近测验得分为 {weakest.score:.0f} 分。"
                )

        if summary.get("pending_review_count", 0) > 0:
            recommendations.append(
                f"今日有 {summary['pending_review_count']} 道错题待复习，建议先完成复盘再学习新内容。"
            )

        for path in paths:
            pending = [
                node.get("concept")
                for node in (path.nodes or [])
                if node.get("status") == "pending"
            ]
            if pending:
                recommendations.append(
                    f"继续推进「{path.title}」，下一步建议学习「{pending[0]}」。"
                )
                break

        if summary["total_duration_sec"] == 0:
            recommendations.append("开始记录学习时长，仪表盘会逐步形成趋势分析。")
        elif summary["average_quiz_score"] >= 85:
            recommendations.append("测验均分较高，可以增加代码实践或拓展阅读来巩固迁移能力。")

        return recommendations[:3]

    def _build_teacher_recommendations(
        self,
        *,
        summary: dict[str, Any],
        weak_points: list[dict[str, Any]],
        quiz_performance: list[dict[str, Any]],
    ) -> list[str]:
        recommendations: list[str] = []
        if weak_points:
            top = weak_points[0]
            recommendations.append(
                f"优先安排「{top['knowledge_point']}」讲解或答疑，"
                f"当前影响 {top['affected_students']} 名学生。"
            )
        low_quizzes = [
            item
            for item in quiz_performance
            if item["attempts"] >= 1 and item["average_score"] < 70
        ]
        if low_quizzes:
            item = low_quizzes[0]
            recommendations.append(
                f"「{item['knowledge_point']}」测验均分 {item['average_score']:.0f}，"
                "建议补充例题和课后训练。"
            )
        if summary.get("pending_review_count", 0) > 0:
            recommendations.append(
                f"共有 {summary['pending_review_count']} 道错题待复习，"
                "可提醒学生先完成错题复盘。"
            )
        if not recommendations:
            recommendations.append("暂无明显薄弱点，建议继续观察后续测验和学习路径进度。")
        return recommendations[:3]


def _round_average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _mastery_level(score: float) -> str:
    if score >= 85:
        return "mastered"
    if score >= 60:
        return "in_progress"
    return "weak"


def _optional_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _is_reviewable_question(question: dict[str, Any]) -> bool:
    question_type = str(question.get("type") or "").strip()
    options = question.get("options")
    return question_type != "short_answer" and isinstance(options, list) and bool(options)


def _next_review_interval_days(review_count: int) -> int:
    intervals = [1, 2, 4, 7, 14, 30]
    return intervals[min(max(review_count - 1, 0), len(intervals) - 1)]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
