from __future__ import annotations

from pydantic import BaseModel, Field


class WikiSearchRequest(BaseModel):
    """Wiki 语义检索请求。"""

    query: str = Field(..., description="检索查询文本")
    top_k: int = Field(default=5, description="返回结果数量", ge=1, le=20)
    course_id: str | None = Field(default=None, description="限定课程 ID")
    chapter: str | None = Field(default=None, description="限定章节 ID（如 ch1）")


class WikiSearchResultItem(BaseModel):
    """单条检索结果。"""

    chunk_id: str
    title: str
    content: str
    course_id: str = ""
    chapter: str = ""
    section: str = ""
    score: float = 0.0


class WikiSearchResponse(BaseModel):
    """Wiki 检索响应。"""

    results: list[WikiSearchResultItem]
    total: int


class KnowledgeTreeNode(BaseModel):
    """知识树节点。"""

    name: str
    course_id: str = ""
    chapter: str
    section: str
    prerequisites: list[str] = Field(default_factory=list)
    description: str = ""


class KnowledgeTreeResponse(BaseModel):
    """知识树响应。"""

    course_id: str | None = None
    chapter_id: str
    concepts: list[KnowledgeTreeNode]


class PrerequisitesResponse(BaseModel):
    """前置知识响应。"""

    topic: str
    prerequisites: list[str]


class RelatedResponse(BaseModel):
    """关联知识响应。"""

    topic: str
    related: list[str]


class WriteBackRequest(BaseModel):
    """知识回写请求。"""

    title: str = Field(..., description="知识条目标题")
    content: str = Field(..., description="知识内容")
    source_agent: str = Field(..., description="生成来源 Agent")
    course_id: str | None = Field(default=None, description="所属课程")
    chapter: str | None = Field(default=None, description="所属章节")
    section: str | None = Field(default=None, description="所属小节")
    tags: list[str] = Field(default_factory=list, description="标签列表")


class WriteBackResponse(BaseModel):
    """知识回写响应。"""

    success: bool
    chunk_id: str | None = None


class WikiUploadResponse(BaseModel):
    """课程资料上传入库响应。"""

    success: bool
    filename: str
    title: str
    course_id: str
    content_type: str
    chunk_count: int
    chunk_ids: list[str]
    char_count: int
    chapter: str
    section: str


class CourseTemplateResponse(BaseModel):
    """课程模板响应。"""

    id: str
    title: str
    description: str = ""
    metadata_course_id: str = ""
    chapter_count: int = 0
    concept_count: int = 0
    estimated_hours: int = 0
    is_default: bool = False
