import type {
  Profile,
  ProfileHistoryItem,
  ProfileUpdate,
  ChatSession,
  SessionDetail,
  ResourceResponse,
  ResourceType,
  ResourceAssetResponse,
  LearningPath,
  LearningPathSummary,
  PathRecommendation,
  LearningActivity,
  QuizSubmitResponse,
  LearningDashboard,
  AgentObservability,
  ReviewItem,
  CodeExecutionResponse,
  WikiCourse,
  WikiChapter,
  WikiConceptNode,
  WikiSearchResult,
  WikiUploadResponse,
} from "./types";
import { getToken, saveToken } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function formatErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail)) {
    const firstError = detail[0];
    if (
      firstError &&
      typeof firstError === "object" &&
      "msg" in firstError &&
      typeof firstError.msg === "string"
    ) {
      return firstError.msg;
    }
  }
  return fallback;
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

async function parseJSON<T>(response: Response): Promise<T> {
  try {
    return await response.json();
  } catch {
    throw new Error("服务器返回了无效的响应格式");
  }
}

export async function register(
  username: string,
  password: string,
  displayName?: string
): Promise<{ access_token: string; user_id: number }> {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, display_name: displayName }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "注册失败"));
  }
  const data = await parseJSON<{ access_token: string; user_id: number }>(response);
  saveToken(data.access_token, data.user_id);
  return data;
}

export async function login(
  username: string,
  password: string
): Promise<{ access_token: string; user_id: number }> {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "登录失败");
  }
  const data = await parseJSON<{ access_token: string; user_id: number }>(response);
  saveToken(data.access_token, data.user_id);
  return data;
}

export async function refreshToken(): Promise<{ access_token: string; user_id: number }> {
  const response = await fetch(`${API_BASE}/api/auth/refresh`, {
    method: "POST",
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "刷新登录状态失败"));
  }
  const data = await parseJSON<{ access_token: string; user_id: number }>(response);
  saveToken(data.access_token, data.user_id);
  return data;
}

export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<{ access_token: string; user_id: number }> {
  const response = await fetch(`${API_BASE}/api/auth/password`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "修改密码失败"));
  }
  const data = await parseJSON<{ access_token: string; user_id: number }>(response);
  saveToken(data.access_token, data.user_id);
  return data;
}

export async function createSession(): Promise<number> {
  const response = await fetch(`${API_BASE}/api/chat/session`, {
    method: "POST",
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, `创建会话失败（HTTP ${response.status})`));
  }
  const data = await parseJSON<{ session_id: number }>(response);
  return data.session_id;
}

export async function fetchSessions(): Promise<ChatSession[]> {
  const response = await fetch(`${API_BASE}/api/chat/sessions`, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    throw new Error("获取会话列表失败");
  }
  return parseJSON<ChatSession[]>(response);
}

export async function fetchSessionDetail(
  sessionId: number
): Promise<SessionDetail> {
  const response = await fetch(`${API_BASE}/api/chat/sessions/${sessionId}`, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    throw new Error("获取会话详情失败");
  }
  return parseJSON<SessionDetail>(response);
}

export async function deleteSession(sessionId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/api/chat/sessions/${sessionId}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, `删除会话失败（HTTP ${response.status})`));
  }
}

export async function fetchProfile(sessionId?: number): Promise<Profile> {
  const url = sessionId
    ? `${API_BASE}/api/profile?session_id=${sessionId}`
    : `${API_BASE}/api/profile`;
  const response = await fetch(url, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    throw new Error("获取画像失败");
  }
  return parseJSON<Profile>(response);
}

export async function fetchProfileHistory(
  limit: number = 20
): Promise<ProfileHistoryItem[]> {
  const response = await fetch(`${API_BASE}/api/profile/history?limit=${limit}`, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    throw new Error("获取画像历史失败");
  }
  return parseJSON<ProfileHistoryItem[]>(response);
}

export async function updateProfile(
  data: ProfileUpdate,
  sessionId?: number
): Promise<Profile> {
  const url = sessionId
    ? `${API_BASE}/api/profile?session_id=${sessionId}`
    : `${API_BASE}/api/profile`;
  const response = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(detail.detail, "保存画像失败"));
  }
  return parseJSON<Profile>(response);
}

export async function confirmAgentProfileUpdate(
  sessionId: number | null,
  update: ProfileUpdate
): Promise<Profile> {
  const response = await fetch(`${API_BASE}/api/profile/confirm-agent-update`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ session_id: sessionId, update }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(detail.detail, "确认画像更新失败"));
  }
  return parseJSON<Profile>(response);
}

export async function renameSession(sessionId: number, title: string): Promise<ChatSession> {
  const response = await fetch(`${API_BASE}/api/chat/sessions/${sessionId}/title`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, `重命名会话失败（HTTP ${response.status})`));
  }
  return parseJSON<ChatSession>(response);
}

export async function setSessionPinned(
  sessionId: number,
  isPinned: boolean
): Promise<ChatSession> {
  const response = await fetch(`${API_BASE}/api/chat/sessions/${sessionId}/pin`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ is_pinned: isPinned }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, `置顶会话失败（HTTP ${response.status})`));
  }
  return parseJSON<ChatSession>(response);
}

export async function fetchResources(
  resourceType?: ResourceType | null
): Promise<ResourceResponse[]> {
  const url = resourceType
    ? `${API_BASE}/api/resources?resource_type=${resourceType}`
    : `${API_BASE}/api/resources`;
  const response = await fetch(url, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    throw new Error("获取资源列表失败");
  }
  return parseJSON<ResourceResponse[]>(response);
}


export async function executeResourceCode(
  resourceId: number,
  codeIndex: number = 0
): Promise<CodeExecutionResponse> {
  const response = await fetch(`${API_BASE}/api/resources/${resourceId}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ code_index: codeIndex }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "运行代码失败"));
  }
  return parseJSON<CodeExecutionResponse>(response);
}

export async function setResourceFavorite(
  resourceId: number,
  isFavorite: boolean
): Promise<ResourceResponse> {
  const response = await fetch(`${API_BASE}/api/resources/${resourceId}/favorite`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ is_favorite: isFavorite }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "更新收藏状态失败"));
  }
  return parseJSON<ResourceResponse>(response);
}

export async function regenerateResource(resourceId: number): Promise<ResourceResponse> {
  const response = await fetch(`${API_BASE}/api/resources/${resourceId}/regenerate`, {
    method: "POST",
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "重生成资源失败"));
  }
  return parseJSON<ResourceResponse>(response);
}

export async function exportResourceMarkdown(resourceId: number): Promise<Blob> {
  return exportResource(resourceId, "markdown");
}

export async function exportResourcePptx(resourceId: number): Promise<Blob> {
  return exportResource(resourceId, "pptx");
}

export async function createResourceExportAsset(
  resourceId: number,
  format: "markdown" | "pptx"
): Promise<ResourceAssetResponse> {
  const response = await fetch(
    `${API_BASE}/api/resources/${resourceId}/assets/export?format=${format}`,
    {
      method: "POST",
      headers: { ...authHeaders() },
    }
  );
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "生成导出链接失败"));
  }
  return parseJSON<ResourceAssetResponse>(response);
}

export async function createAnimationExportAsset(
  resourceId: number
): Promise<ResourceAssetResponse> {
  const response = await fetch(`${API_BASE}/api/resources/${resourceId}/assets/animation`, {
    method: "POST",
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "生成动画导出包失败"));
  }
  return parseJSON<ResourceAssetResponse>(response);
}

export async function fetchAssetBlob(asset: ResourceAssetResponse): Promise<Blob> {
  const url = resolveAssetUrl(asset.url);
  const response = await fetch(url, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "获取资产失败"));
  }
  return response.blob();
}

async function exportResource(
  resourceId: number,
  format: "markdown" | "pptx"
): Promise<Blob> {
  const response = await fetch(
    `${API_BASE}/api/resources/${resourceId}/export?format=${format}`,
    {
      headers: { ...authHeaders() },
    }
  );
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "导出资源失败"));
  }
  return response.blob();
}

export function getChatStreamUrl(): string {
  return `${API_BASE}/api/chat/stream`;
}

function resolveAssetUrl(url: string): string {
  if (/^https?:\/\//i.test(url)) {
    return url;
  }
  return `${API_BASE}${url.startsWith("/") ? url : `/${url}`}`;
}

// ---- Wiki API ----

export async function fetchWikiCourses(): Promise<WikiCourse[]> {
  const response = await fetch(`${API_BASE}/api/wiki/courses`, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    throw new Error("获取课程列表失败");
  }
  return parseJSON<WikiCourse[]>(response);
}

export async function fetchWikiChapters(
  courseId?: string | null
): Promise<WikiChapter[]> {
  const url = courseId
    ? `${API_BASE}/api/wiki/chapters?course_id=${encodeURIComponent(courseId)}`
    : `${API_BASE}/api/wiki/chapters`;
  const response = await fetch(url, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    throw new Error("获取章节列表失败");
  }
  return parseJSON<WikiChapter[]>(response);
}

export async function fetchWikiTree(
  chapterId: string,
  courseId?: string | null
): Promise<{ concepts: WikiConceptNode[] }> {
  const url = courseId
    ? `${API_BASE}/api/wiki/tree/${chapterId}?course_id=${encodeURIComponent(courseId)}`
    : `${API_BASE}/api/wiki/tree/${chapterId}`;
  const response = await fetch(url, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    throw new Error("获取知识树失败");
  }
  return parseJSON<{ concepts: WikiConceptNode[] }>(response);
}

export async function searchWiki(
  query: string,
  topK: number = 5,
  courseId?: string | null
): Promise<{
  results: WikiSearchResult[];
}> {
  const response = await fetch(`${API_BASE}/api/wiki/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ query, top_k: topK, course_id: courseId || null }),
  });
  if (!response.ok) {
    throw new Error("搜索知识库失败");
  }
  return parseJSON<{ results: WikiSearchResult[] }>(response);
}

export async function uploadWikiDocument(
  file: File,
  courseId?: string | null
): Promise<WikiUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (courseId) {
    formData.append("course_id", courseId);
  }

  const response = await fetch(`${API_BASE}/api/wiki/upload`, {
    method: "POST",
    headers: { ...authHeaders() },
    body: formData,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "上传资料失败"));
  }
  return parseJSON<WikiUploadResponse>(response);
}

export async function fetchPrerequisites(
  topic: string
): Promise<{ topic: string; prerequisites: string[] }> {
  const response = await fetch(
    `${API_BASE}/api/wiki/prerequisites/${encodeURIComponent(topic)}`,
    { headers: { ...authHeaders() } }
  );
  if (!response.ok) {
    throw new Error("获取前置知识失败");
  }
  return parseJSON(response);
}

// ---- Learning Path API ----

export async function createLearningPath(
  goalTopic: string,
  title?: string,
  courseId?: string | null
): Promise<LearningPath> {
  const response = await fetch(`${API_BASE}/api/learning/paths`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      goal_topic: goalTopic,
      title: title || null,
      course_id: courseId || null,
    }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "创建学习路径失败"));
  }
  return parseJSON<LearningPath>(response);
}

export async function fetchLearningPaths(): Promise<LearningPathSummary[]> {
  const response = await fetch(`${API_BASE}/api/learning/paths`, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    throw new Error("获取学习路径列表失败");
  }
  return parseJSON<LearningPathSummary[]>(response);
}

export async function fetchLearningDashboard(): Promise<LearningDashboard> {
  const response = await fetch(`${API_BASE}/api/learning/dashboard`, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    throw new Error("获取学习评估数据失败");
  }
  return parseJSON<LearningDashboard>(response);
}

export async function fetchAgentObservability(
  limit: number = 60
): Promise<AgentObservability> {
  const response = await fetch(`${API_BASE}/api/learning/agent-observability?limit=${limit}`, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    throw new Error("获取 Agent 运行数据失败");
  }
  return parseJSON<AgentObservability>(response);
}

export async function fetchReviewQueue(limit: number = 20): Promise<ReviewItem[]> {
  const response = await fetch(`${API_BASE}/api/learning/review-queue?limit=${limit}`, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    throw new Error("获取复习队列失败");
  }
  return parseJSON<ReviewItem[]>(response);
}

export async function updateReviewItem(
  itemId: number,
  mastered: boolean
): Promise<ReviewItem> {
  const response = await fetch(`${API_BASE}/api/learning/review-items/${itemId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ mastered }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "更新复习状态失败"));
  }
  return parseJSON<ReviewItem>(response);
}

export async function fetchLearningPath(pathId: number): Promise<LearningPath> {
  const response = await fetch(`${API_BASE}/api/learning/paths/${pathId}`, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    throw new Error("获取学习路径详情失败");
  }
  return parseJSON<LearningPath>(response);
}

export async function updateNodeStatus(
  pathId: number,
  concept: string,
  status: string
): Promise<LearningPath> {
  const response = await fetch(`${API_BASE}/api/learning/paths/${pathId}/nodes`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ concept, status }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "更新知识点状态失败"));
  }
  return parseJSON<LearningPath>(response);
}

export async function fetchPathRecommendations(
  pathId: number
): Promise<PathRecommendation> {
  const response = await fetch(
    `${API_BASE}/api/learning/paths/${pathId}/recommendations`,
    { headers: { ...authHeaders() } }
  );
  if (!response.ok) {
    throw new Error("获取学习推荐失败");
  }
  return parseJSON<PathRecommendation>(response);
}

export async function recordLearningActivity(data: {
  path_id?: number | null;
  activity_type: string;
  knowledge_point?: string | null;
  resource_id?: number | null;
  result?: Record<string, unknown> | null;
  score?: number | null;
  duration_sec?: number | null;
  detail?: string | null;
}): Promise<LearningActivity> {
  const response = await fetch(`${API_BASE}/api/learning/activities`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const d = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(d.detail, "记录学习活动失败"));
  }
  return parseJSON<LearningActivity>(response);
}

export async function generatePptImages(
  topic: string
): Promise<Response> {
  const response = await fetch(
    `${API_BASE}/api/resources/ppt-images?topic=${encodeURIComponent(topic)}`,
    {
      method: "POST",
      headers: { ...authHeaders() },
    }
  );
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(data.detail, "生成 PPT 图片失败"));
  }
  return response;
}

export async function submitQuiz(data: {
  resource_id: number;
  answers: { question_id: number; user_answer: string }[];
  duration_sec?: number | null;
}): Promise<QuizSubmitResponse> {
  const response = await fetch(`${API_BASE}/api/learning/quiz-submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const d = await response.json().catch(() => ({}));
    throw new Error(formatErrorDetail(d.detail, "提交练习失败"));
  }
  return parseJSON<QuizSubmitResponse>(response);
}
