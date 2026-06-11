export type ChatRole = "user" | "assistant";

export type ResourceType =
  | "document"
  | "quiz"
  | "code"
  | "mindmap"
  | "ppt"
  | "ppt_images"
  | "animation"
  | "reading";

export interface Profile {
  user_id: number;
  session_id: number | null;
  major: string | null;
  grade: string | null;
  knowledge_base: Record<string, string>;
  cognitive_style: string | null;
  learning_goal: string | null;
  weak_points: string[];
  learning_pace: string | null;
  interest_areas: string[];
  coding_level: string | null;
  weekly_hours: number | null;
}

export type ProfileUpdate = Partial<Pick<
  Profile,
  | "major"
  | "grade"
  | "knowledge_base"
  | "cognitive_style"
  | "learning_goal"
  | "weak_points"
  | "learning_pace"
  | "interest_areas"
  | "coding_level"
  | "weekly_hours"
>>;

export interface ProfileHistoryItem {
  id: number;
  user_id: number;
  session_id: number | null;
  source: "agent" | "manual" | string;
  changed_fields: string[];
  profile_data: Profile;
  created_at: string;
}

export interface SSEEvent {
  type:
    | "agent_status"
    | "profile_updated"
    | "token"
    | "resource_card"
    | "wiki_fallback"
    | "done"
    | "error";
  session_id: number | null;
  payload: AgentStatusPayload | TokenPayload | ResourceCard | WikiFallbackPayload | ErrorPayload | Record<string, unknown>;
}

export interface AgentStatusPayload {
  agent: string;
  status: string;
  message: string;
}

export interface TokenPayload {
  token: string;
}

export interface ResourceCard {
  id: number | null;
  turn_id?: string | null;
  course_id?: string | null;
  resource_type: ResourceType;
  title: string;
  content: string;
  knowledge_point?: string;
  agent_name?: string;
  is_favorite?: boolean;
  confidence?: number | null;
  sources?: ResourceSource[];
}

export interface ResourceSource {
  chapter?: string;
  section?: string;
  title?: string;
  score?: number;
  chunk_id?: string;
  snippet?: string;
  source_name?: string;
}

export interface ErrorPayload {
  message: string;
}

export interface WikiFallbackPayload {
  message: string;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  turn_id?: string | null;
  resources?: ResourceCard[];
  agentStatus?: string;
}

export interface ChatSession {
  id: number;
  title: string;
  course_id?: string | null;
  created_at: string;
  updated_at: string;
  is_pinned: boolean;
  pinned_at?: string | null;
}

export interface MessageResponse {
  id: number;
  turn_id?: string | null;
  role: ChatRole;
  content: string;
  message_type: string;
  created_at: string;
}

export interface ResourceResponse {
  id: number;
  turn_id?: string | null;
  course_id?: string | null;
  resource_type: ResourceType;
  title: string;
  content: string;
  knowledge_point?: string;
  agent_name?: string;
  is_favorite: boolean;
  created_at: string;
  confidence?: number | null;
  sources?: ResourceSource[];
}

export interface ResourceAssetResponse {
  url: string;
  filename: string;
  media_type: string;
  size_bytes: number;
}

export type CodeExecutionStatus = "success" | "error" | "timeout" | "blocked";

export interface CodeExecutionResponse {
  status: CodeExecutionStatus;
  stdout: string;
  stderr: string;
  exit_code: number | null;
  duration_ms: number;
}

export interface SessionDetail {
  id: number;
  title: string;
  course_id?: string | null;
  created_at: string;
  updated_at: string;
  messages: MessageResponse[];
  resources: ResourceResponse[];
}

// ---- Learning Path ----

export interface LearningPathNode {
  concept: string;
  chapter: string;
  section: string;
  description: string;
  prerequisites?: string[];
  status: "pending" | "in_progress" | "completed" | "skipped";
}

export interface LearningPath {
  id: number;
  user_id: number;
  title: string;
  goal_topic: string;
  course_id?: string | null;
  nodes: LearningPathNode[];
  status: string;
  created_at: string;
  updated_at: string;
  progress: number;
}

export interface LearningPathSummary {
  id: number;
  title: string;
  goal_topic: string;
  course_id?: string | null;
  status: string;
  node_count: number;
  progress: number;
  created_at: string;
  updated_at: string;
}

export interface PathRecommendation {
  next_concepts: string[];
  completed_count: number;
  total_count: number;
  message: string;
}

export interface LearningActivity {
  id: number;
  user_id: number;
  path_id: number | null;
  activity_type: string;
  knowledge_point: string | null;
  resource_id: number | null;
  result: Record<string, unknown> | null;
  score: number | null;
  duration_sec: number | null;
  detail: string | null;
  created_at: string;
}

export interface QuizQuestionResult {
  question_id: number;
  correct: boolean;
  user_answer: string;
  correct_answer: string;
  question_type: string;
  knowledge_point: string | null;
  difficulty: string | null;
}

export interface QuizSubmitResponse {
  score: number;
  total: number;
  correct_count: number;
  results: QuizQuestionResult[];
  knowledge_point: string | null;
  activity_id: number;
  duration_sec: number | null;
  weak_points: string[];
  accuracy_by_type: Record<string, number>;
}

export interface DashboardSummary {
  total_activities: number;
  total_duration_sec: number;
  quiz_count: number;
  average_quiz_score: number;
  completed_nodes: number;
  total_nodes: number;
  active_paths: number;
  pending_review_count: number;
}

export interface ActivityTrendPoint {
  date: string;
  activity_count: number;
  duration_sec: number;
  quiz_count: number;
  average_score: number;
}

export interface KnowledgeMasteryItem {
  knowledge_point: string;
  attempts: number;
  average_score: number;
  level: "mastered" | "in_progress" | "weak" | "unknown";
}

export interface PathProgressItem {
  path_id: number;
  title: string;
  goal_topic: string;
  progress: number;
  completed_count: number;
  total_count: number;
  status: string;
}

export interface ActivityTypeCount {
  activity_type: string;
  count: number;
}

export interface LearningDashboard {
  summary: DashboardSummary;
  activity_trend: ActivityTrendPoint[];
  knowledge_mastery: KnowledgeMasteryItem[];
  path_progress: PathProgressItem[];
  activity_types: ActivityTypeCount[];
  recent_activities: LearningActivity[];
  recommendations: string[];
}

export interface AgentObservability {
  summary: {
    total_runs: number;
    total_events: number;
    success_events: number;
    error_events: number;
    average_duration_ms: number;
  };
  agent_stats: {
    agent_name: string;
    call_count: number;
    success_count: number;
    error_count: number;
    total_duration_ms: number;
    average_duration_ms: number;
    latest_status: string;
    resource_types: string[];
  }[];
  recent_runs: {
    run_id: string;
    session_id: number;
    started_at: string;
    ended_at: string;
    event_count: number;
    duration_ms: number;
    status: string;
    agents: string[];
  }[];
  recent_events: {
    id: number;
    run_id: string;
    session_id: number;
    agent_name: string;
    node_name: string;
    resource_type: string | null;
    status: string;
    duration_ms: number;
    llm_provider: string | null;
    llm_used: boolean;
    input_chars: number;
    output_chars: number;
    token_estimate: number;
    error: string | null;
    event_metadata: Record<string, unknown>;
    created_at: string;
  }[];
}

export interface TeacherDashboard {
  summary: {
    student_count: number;
    active_path_count: number;
    quiz_count: number;
    average_quiz_score: number;
    pending_review_count: number;
  };
  weak_points: {
    knowledge_point: string;
    affected_students: number;
    review_count: number;
    average_score: number;
  }[];
  quiz_performance: {
    knowledge_point: string;
    attempts: number;
    average_score: number;
  }[];
  students: {
    user_id: number;
    username: string;
    display_name: string | null;
    major: string | null;
    grade: string | null;
    active_paths: number;
    completed_nodes: number;
    total_nodes: number;
    average_quiz_score: number;
    pending_reviews: number;
    weak_points: string[];
  }[];
  recommendations: string[];
}

export interface ReviewItem {
  id: number;
  user_id: number;
  resource_id: number | null;
  activity_id: number | null;
  knowledge_point: string | null;
  question_id: number;
  question_type: string;
  question_text: string;
  user_answer: string;
  correct_answer: string;
  explanation: string | null;
  status: "pending" | "reviewing" | "mastered" | string;
  review_count: number;
  next_review_at: string | null;
  last_reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

// ---- Wiki ----

export interface WikiChapter {
  id: string;
  title: string;
  course_id?: string;
}

export interface WikiConceptNode {
  name: string;
  course_id?: string;
  chapter: string;
  section: string;
  prerequisites: string[];
  description: string;
}

export interface WikiSearchResult {
  chunk_id: string;
  title: string;
  content: string;
  course_id: string;
  chapter: string;
  section: string;
  score: number;
}

export interface WikiUploadResponse {
  success: boolean;
  filename: string;
  title: string;
  course_id: string;
  content_type: string;
  chunk_count: number;
  chunk_ids: string[];
  char_count: number;
  chapter: string;
  section: string;
}

export interface WikiCourse {
  id: string;
  title: string;
  description: string;
  metadata_course_id: string;
  chapter_count: number;
  concept_count: number;
  estimated_hours: number;
  is_default: boolean;
}
