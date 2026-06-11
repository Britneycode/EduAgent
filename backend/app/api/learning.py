from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.llm import get_llm_client, get_llm_configuration_warning
from app.models.user import User
from app.schemas.learning import (
    AgentObservabilityResponse,
    CreatePathRequest,
    LearningDashboardResponse,
    LearningActivityResponse,
    LearningPathListResponse,
    LearningPathResponse,
    PathRecommendation,
    QuizQuestionResult,
    QuizSubmitRequest,
    QuizSubmitResponse,
    RecordActivityRequest,
    ReviewItemResponse,
    ReviewItemUpdateRequest,
    TeacherDashboardResponse,
    UpdateNodeStatusRequest,
)
from app.services.chat_service import ChatService
from app.services.learning_path_service import (
    LearningActivityOwnershipError,
    LearningPathService,
)
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/api/learning", tags=["learning"])


def _is_auto_scored_question(question: dict) -> bool:
    question_type = str(question.get("type") or "").strip()
    options = question.get("options")
    return (
        question_type != "short_answer"
        and isinstance(options, list)
        and bool(options)
    )


def _get_knowledge_graph() -> object | None:
    """尝试获取知识图谱实例，未初始化时返回 None。"""
    try:
        from app.wiki import _knowledge_graph

        return _knowledge_graph
    except Exception:
        return None


def _get_default_course_id() -> str | None:
    try:
        from app.wiki import get_default_course_id

        return get_default_course_id()
    except Exception:
        return None


def _path_course_id(path) -> str | None:
    nodes = path.nodes or []
    for node in nodes:
        course_id = node.get("course_id")
        if isinstance(course_id, str) and course_id:
            return course_id
    return None


def _csv_values(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _csv_int_values(value: str) -> set[int]:
    values: set[int] = set()
    for item in _csv_values(value):
        try:
            values.add(int(item))
        except ValueError:
            continue
    return values


def _has_teacher_dashboard_access(user: User) -> bool:
    settings = get_settings()
    allowed_usernames = _csv_values(settings.teacher_dashboard_allowed_usernames)
    allowed_user_ids = _csv_int_values(settings.teacher_dashboard_allowed_user_ids)
    return user.username in allowed_usernames or user.id in allowed_user_ids


def _require_teacher_dashboard_access(user: User) -> None:
    if not _has_teacher_dashboard_access(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要教师或管理员权限",
        )


@router.get("/dashboard", response_model=LearningDashboardResponse)
async def get_learning_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LearningDashboardResponse:
    """获取学习效果评估仪表盘数据。"""
    svc = LearningPathService(session=db)
    return LearningDashboardResponse(**await svc.get_dashboard(user_id=user.id))


@router.get("/teacher-dashboard", response_model=TeacherDashboardResponse)
async def get_teacher_dashboard(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> TeacherDashboardResponse:
    """获取教师/助教视角的多用户学习概况。"""
    _require_teacher_dashboard_access(_user)
    svc = LearningPathService(session=db)
    return TeacherDashboardResponse(**await svc.get_teacher_dashboard())


@router.get("/agent-observability", response_model=AgentObservabilityResponse)
async def get_agent_observability(
    limit: Annotated[int, Query(ge=1, le=200)] = 60,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentObservabilityResponse:
    """获取当前用户的 Agent 编排运行观测数据。"""
    svc = LearningPathService(session=db)
    return AgentObservabilityResponse(
        **await svc.get_agent_observability(user_id=user.id, limit=limit)
    )


@router.post("/paths", response_model=LearningPathResponse)
async def create_learning_path(
    request: CreatePathRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LearningPathResponse:
    """根据目标知识点生成个性化学习路径。"""
    svc = LearningPathService(session=db)
    profile_svc = ProfileService(session=db)

    profile_resp = await profile_svc.get_or_create_profile(user_id=user.id)
    profile_dict = profile_resp.model_dump()

    kg = _get_knowledge_graph()
    llm_client = None if get_llm_configuration_warning() else get_llm_client()
    course_id = request.course_id or _get_default_course_id()

    path = await svc.generate_path(
        user_id=user.id,
        goal_topic=request.goal_topic,
        title=request.title,
        profile=profile_dict,
        knowledge_graph=kg,
        llm_client=llm_client,
        course_id=course_id,
    )

    return LearningPathResponse(
        id=path.id,
        user_id=path.user_id,
        title=path.title,
        goal_topic=path.goal_topic,
        course_id=_path_course_id(path),
        nodes=path.nodes,
        status=path.status,
        created_at=path.created_at.isoformat(),
        updated_at=path.updated_at.isoformat(),
        progress=svc.compute_progress(path),
    )


@router.get("/paths", response_model=list[LearningPathListResponse])
async def list_learning_paths(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[LearningPathListResponse]:
    """获取当前用户的所有学习路径。"""
    svc = LearningPathService(session=db)
    paths = await svc.list_paths(user_id=user.id)
    return [
        LearningPathListResponse(
            id=p.id,
            title=p.title,
            goal_topic=p.goal_topic,
            course_id=_path_course_id(p),
            status=p.status,
            node_count=len(p.nodes) if p.nodes else 0,
            progress=svc.compute_progress(p),
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in paths
    ]


@router.get("/paths/{path_id}", response_model=LearningPathResponse)
async def get_learning_path(
    path_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LearningPathResponse:
    """获取学习路径详情。"""
    svc = LearningPathService(session=db)
    path = await svc.get_path(path_id, user_id=user.id)
    if path is None:
        raise HTTPException(status_code=404, detail="学习路径不存在")

    return LearningPathResponse(
        id=path.id,
        user_id=path.user_id,
        title=path.title,
        goal_topic=path.goal_topic,
        course_id=_path_course_id(path),
        nodes=path.nodes,
        status=path.status,
        created_at=path.created_at.isoformat(),
        updated_at=path.updated_at.isoformat(),
        progress=svc.compute_progress(path),
    )


@router.patch("/paths/{path_id}/nodes", response_model=LearningPathResponse)
async def update_node_status(
    path_id: int,
    request: UpdateNodeStatusRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LearningPathResponse:
    """更新路径中某个知识点的学习状态。"""
    valid_statuses = {"pending", "in_progress", "completed", "skipped"}
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"无效状态，可选值：{', '.join(sorted(valid_statuses))}",
        )

    svc = LearningPathService(session=db)
    path = await svc.update_node_status(
        path_id=path_id,
        user_id=user.id,
        concept=request.concept,
        status=request.status,
    )
    if path is None:
        raise HTTPException(status_code=404, detail="学习路径或知识点不存在")

    return LearningPathResponse(
        id=path.id,
        user_id=path.user_id,
        title=path.title,
        goal_topic=path.goal_topic,
        course_id=_path_course_id(path),
        nodes=path.nodes,
        status=path.status,
        created_at=path.created_at.isoformat(),
        updated_at=path.updated_at.isoformat(),
        progress=svc.compute_progress(path),
    )


@router.get("/paths/{path_id}/recommendations", response_model=PathRecommendation)
async def get_path_recommendations(
    path_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PathRecommendation:
    """获取学习路径的推荐：下一步要学习的知识点。"""
    svc = LearningPathService(session=db)
    result = await svc.get_recommendations(path_id, user_id=user.id)
    return PathRecommendation(**result)


@router.post("/activities", response_model=LearningActivityResponse)
async def record_activity(
    request: RecordActivityRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LearningActivityResponse:
    """记录一次学习活动。"""
    svc = LearningPathService(session=db)
    try:
        activity = await svc.record_activity(
            user_id=user.id,
            activity_type=request.activity_type,
            path_id=request.path_id,
            knowledge_point=request.knowledge_point,
            resource_id=request.resource_id,
            result=request.result,
            score=request.score,
            duration_sec=request.duration_sec,
            detail=request.detail,
        )
    except LearningActivityOwnershipError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return LearningActivityResponse(
        id=activity.id,
        user_id=activity.user_id,
        path_id=activity.path_id,
        activity_type=activity.activity_type,
        knowledge_point=activity.knowledge_point,
        resource_id=activity.resource_id,
        result=activity.result,
        score=activity.score,
        duration_sec=activity.duration_sec,
        detail=activity.detail,
        created_at=activity.created_at.isoformat(),
    )


@router.get("/activities", response_model=list[LearningActivityResponse])
async def list_activities(
    path_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[LearningActivityResponse]:
    """获取学习活动列表。"""
    svc = LearningPathService(session=db)
    activities = await svc.list_activities(
        user_id=user.id, path_id=path_id
    )
    return [
        LearningActivityResponse(
            id=a.id,
            user_id=a.user_id,
            path_id=a.path_id,
            activity_type=a.activity_type,
            knowledge_point=a.knowledge_point,
            resource_id=a.resource_id,
            result=a.result,
            score=a.score,
            duration_sec=a.duration_sec,
            detail=a.detail,
            created_at=a.created_at.isoformat(),
        )
        for a in activities
    ]


@router.get("/review-queue", response_model=list[ReviewItemResponse])
async def get_review_queue(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ReviewItemResponse]:
    """获取当前到期的错题复习队列。"""
    svc = LearningPathService(session=db)
    items = await svc.get_review_queue(user_id=user.id, limit=limit)
    return [_review_item_response(item) for item in items]


@router.patch("/review-items/{item_id}", response_model=ReviewItemResponse)
async def update_review_item(
    item_id: int,
    request: ReviewItemUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReviewItemResponse:
    """标记错题是否已掌握。"""
    svc = LearningPathService(session=db)
    item = await svc.update_review_item(
        user_id=user.id,
        item_id=item_id,
        mastered=request.mastered,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="错题记录不存在")
    return _review_item_response(item)


@router.post("/quiz-submit", response_model=QuizSubmitResponse)
async def submit_quiz(
    request: QuizSubmitRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QuizSubmitResponse:
    """提交练习答案，自动评分并记录学习活动。"""
    chat_svc = ChatService(session=db)
    resource = await chat_svc.get_resource(request.resource_id, user_id=user.id)
    if resource is None:
        raise HTTPException(status_code=404, detail="练习资源不存在")

    try:
        quiz_data = json.loads(resource.content)
        questions = quiz_data.get("questions", [])
    except (json.JSONDecodeError, AttributeError):
        raise HTTPException(status_code=400, detail="该资源不是可评分的练习题")

    if not questions:
        raise HTTPException(status_code=400, detail="该资源没有可评分的题目")

    answer_map = {a.question_id: a.user_answer for a in request.answers}

    results: list[QuizQuestionResult] = []
    correct_count = 0
    auto_scored_total = 0
    type_stats: dict[str, dict[str, int]] = {}
    weak_points: list[str] = []
    for q in questions:
        qid = q.get("id")
        question_type = str(q.get("type") or "")
        question_knowledge_point = _optional_non_empty_text(
            q.get("knowledge_point")
        ) or resource.knowledge_point
        difficulty = _optional_non_empty_text(q.get("difficulty"))
        correct_answer = q.get("answer", "")
        user_answer = answer_map.get(qid, "")
        is_correct = user_answer == correct_answer
        is_auto_scored = _is_auto_scored_question(q)
        if is_auto_scored:
            auto_scored_total += 1
            stats = type_stats.setdefault(question_type, {"correct": 0, "total": 0})
            stats["total"] += 1
        if is_auto_scored and is_correct:
            correct_count += 1
            type_stats[question_type]["correct"] += 1
        if is_auto_scored and not is_correct and question_knowledge_point:
            weak_points.append(question_knowledge_point)
        results.append(
            QuizQuestionResult(
                question_id=qid,
                correct=is_correct,
                user_answer=user_answer,
                correct_answer=correct_answer,
                question_type=question_type,
                knowledge_point=question_knowledge_point,
                difficulty=difficulty,
            )
        )

    total = auto_scored_total
    score = round((correct_count / total) * 100, 1) if total > 0 else 0
    accuracy_by_type = {
        question_type: round((stats["correct"] / stats["total"]) * 100, 1)
        for question_type, stats in type_stats.items()
        if stats["total"] > 0
    }
    weak_points = _unique_values(weak_points)

    svc = LearningPathService(session=db)
    activity = await svc.record_activity(
        user_id=user.id,
        activity_type="quiz",
        knowledge_point=resource.knowledge_point,
        resource_id=resource.id,
        result={
            "correct_count": correct_count,
            "total": total,
            "question_count": len(questions),
            "details": [r.model_dump() for r in results],
            "weak_points": weak_points,
            "accuracy_by_type": accuracy_by_type,
        },
        score=score,
        duration_sec=request.duration_sec,
    )
    await svc.record_quiz_mistakes(
        user_id=user.id,
        resource_id=resource.id,
        activity_id=activity.id,
        knowledge_point=resource.knowledge_point,
        questions=questions,
        results=results,
    )

    if resource.knowledge_point and total > 0:
        profile_svc = ProfileService(session=db)
        level = "掌握" if score >= 80 else "了解" if score >= 50 else "薄弱"
        profile_update: dict[str, object] = {
            "knowledge_base": {resource.knowledge_point: level}
        }
        if score < 80:
            profile_update["weak_points"] = [resource.knowledge_point]
        await profile_svc.save_profile_update(
            session_id=0,
            update=profile_update,
            user_id=user.id,
        )

        await svc.apply_quiz_result_to_paths(
            user_id=user.id,
            knowledge_point=resource.knowledge_point,
            score=score,
        )

    return QuizSubmitResponse(
        score=score,
        total=total,
        correct_count=correct_count,
        results=results,
        knowledge_point=resource.knowledge_point,
        activity_id=activity.id,
        duration_sec=request.duration_sec,
        weak_points=weak_points,
        accuracy_by_type=accuracy_by_type,
    )


def _review_item_response(item) -> ReviewItemResponse:
    return ReviewItemResponse(
        id=item.id,
        user_id=item.user_id,
        resource_id=item.resource_id,
        activity_id=item.activity_id,
        knowledge_point=item.knowledge_point,
        question_id=item.question_id,
        question_type=item.question_type,
        question_text=item.question_text,
        user_answer=item.user_answer,
        correct_answer=item.correct_answer,
        explanation=item.explanation,
        status=item.status,
        review_count=item.review_count,
        next_review_at=item.next_review_at.isoformat() if item.next_review_at else None,
        last_reviewed_at=item.last_reviewed_at.isoformat()
        if item.last_reviewed_at
        else None,
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat(),
    )


def _optional_non_empty_text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _unique_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique
