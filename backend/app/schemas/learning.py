from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreatePathRequest(BaseModel):
    goal_topic: str = Field(..., min_length=1, max_length=255, description="目标知识点")
    title: str | None = Field(default=None, max_length=255, description="路径标题，为空则自动生成")
    course_id: str | None = Field(default=None, max_length=100, description="课程 ID")


class PathNodeResponse(BaseModel):
    concept: str
    course_id: str = ""
    chapter: str = ""
    section: str = ""
    description: str = ""
    prerequisites: list[str] = Field(default_factory=list)
    status: str = "pending"


class LearningPathResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    goal_topic: str
    course_id: str | None = None
    nodes: list[dict[str, Any]]
    status: str
    created_at: str
    updated_at: str
    progress: float = 0.0


class LearningPathListResponse(BaseModel):
    id: int
    title: str
    goal_topic: str
    course_id: str | None = None
    status: str
    node_count: int = 0
    progress: float = 0.0
    created_at: str
    updated_at: str


class RecordActivityRequest(BaseModel):
    path_id: int | None = Field(default=None, description="关联的学习路径 ID")
    activity_type: str = Field(..., description="活动类型：quiz / resource_view / code_practice / note")
    knowledge_point: str | None = Field(default=None, description="关联知识点")
    resource_id: int | None = Field(default=None, description="关联资源 ID")
    result: dict[str, Any] | None = Field(default=None, description="活动结果")
    score: float | None = Field(default=None, ge=0, le=100, description="得分 (0-100)")
    duration_sec: int | None = Field(default=None, ge=0, description="耗时（秒）")
    detail: str | None = Field(default=None, description="补充说明")


class LearningActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    path_id: int | None
    activity_type: str
    knowledge_point: str | None
    resource_id: int | None
    result: dict[str, Any] | None
    score: float | None
    duration_sec: int | None
    detail: str | None
    created_at: str


class UpdateNodeStatusRequest(BaseModel):
    concept: str = Field(..., description="知识点名称")
    status: str = Field(..., description="状态：pending / in_progress / completed / skipped")


class PathRecommendation(BaseModel):
    next_concepts: list[str] = Field(default_factory=list, description="推荐学习的下一批知识点")
    completed_count: int = 0
    total_count: int = 0
    message: str = ""


class QuizAnswer(BaseModel):
    question_id: int = Field(..., description="题目 ID")
    user_answer: str = Field(..., description="用户选择的答案")


class QuizSubmitRequest(BaseModel):
    resource_id: int = Field(..., description="练习资源 ID")
    answers: list[QuizAnswer] = Field(..., min_length=1, description="答题列表")
    duration_sec: int | None = Field(default=None, ge=0, description="答题耗时（秒）")


class QuizQuestionResult(BaseModel):
    question_id: int
    correct: bool
    user_answer: str
    correct_answer: str
    question_type: str = ""
    knowledge_point: str | None = None
    difficulty: str | None = None


class QuizSubmitResponse(BaseModel):
    score: float
    total: int
    correct_count: int
    results: list[QuizQuestionResult]
    knowledge_point: str | None = None
    activity_id: int
    duration_sec: int | None = None
    weak_points: list[str] = Field(default_factory=list)
    accuracy_by_type: dict[str, float] = Field(default_factory=dict)


class DashboardSummary(BaseModel):
    total_activities: int = 0
    total_duration_sec: int = 0
    quiz_count: int = 0
    average_quiz_score: float = 0.0
    completed_nodes: int = 0
    total_nodes: int = 0
    active_paths: int = 0
    pending_review_count: int = 0


class ActivityTrendPoint(BaseModel):
    date: str
    activity_count: int = 0
    duration_sec: int = 0
    quiz_count: int = 0
    average_score: float = 0.0


class KnowledgeMasteryItem(BaseModel):
    knowledge_point: str
    attempts: int = 0
    average_score: float = 0.0
    level: str = "unknown"


class PathProgressItem(BaseModel):
    path_id: int
    title: str
    goal_topic: str
    progress: float = 0.0
    completed_count: int = 0
    total_count: int = 0
    status: str


class ActivityTypeCount(BaseModel):
    activity_type: str
    count: int = 0


class LearningDashboardResponse(BaseModel):
    summary: DashboardSummary
    activity_trend: list[ActivityTrendPoint] = Field(default_factory=list)
    knowledge_mastery: list[KnowledgeMasteryItem] = Field(default_factory=list)
    path_progress: list[PathProgressItem] = Field(default_factory=list)
    activity_types: list[ActivityTypeCount] = Field(default_factory=list)
    recent_activities: list[LearningActivityResponse] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class AgentRunSummary(BaseModel):
    total_runs: int = 0
    total_events: int = 0
    success_events: int = 0
    error_events: int = 0
    average_duration_ms: int = 0


class AgentRunStatItem(BaseModel):
    agent_name: str
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_duration_ms: int = 0
    average_duration_ms: int = 0
    latest_status: str = ""
    resource_types: list[str] = Field(default_factory=list)


class AgentRecentRunItem(BaseModel):
    run_id: str
    session_id: int
    started_at: str
    ended_at: str
    event_count: int = 0
    duration_ms: int = 0
    status: str = ""
    agents: list[str] = Field(default_factory=list)


class AgentRunEventItem(BaseModel):
    id: int
    run_id: str
    session_id: int
    agent_name: str
    node_name: str
    resource_type: str | None = None
    status: str
    duration_ms: int = 0
    llm_provider: str | None = None
    llm_used: bool = False
    input_chars: int = 0
    output_chars: int = 0
    token_estimate: int = 0
    error: str | None = None
    event_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class AgentObservabilityResponse(BaseModel):
    summary: AgentRunSummary
    agent_stats: list[AgentRunStatItem] = Field(default_factory=list)
    recent_runs: list[AgentRecentRunItem] = Field(default_factory=list)
    recent_events: list[AgentRunEventItem] = Field(default_factory=list)


class ReviewItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    resource_id: int | None
    activity_id: int | None
    knowledge_point: str | None
    question_id: int
    question_type: str
    question_text: str
    user_answer: str
    correct_answer: str
    explanation: str | None
    status: str
    review_count: int
    next_review_at: str | None
    last_reviewed_at: str | None
    created_at: str
    updated_at: str


class ReviewItemUpdateRequest(BaseModel):
    mastered: bool = Field(..., description="是否已掌握该错题")
