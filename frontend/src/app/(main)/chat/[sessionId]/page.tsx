"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { streamChat } from "@/lib/sse";
import { fetchSessionDetail, fetchWikiCourses } from "@/lib/api";
import { consumePendingMessage } from "@/lib/pendingMessage";
import { setLastSessionId } from "@/lib/lastSession";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { StreamingText } from "@/components/chat/StreamingText";
import { VoiceInput } from "@/components/chat/VoiceInput";
import { AgentFlow } from "@/components/chat/AgentFlow";
import { AgentStatus } from "@/components/chat/AgentStatus";
import { ResourceCard } from "@/components/chat/ResourceCard";
import {
  getStreamStateForSession,
  useChatStreamStore,
} from "@/store/chatStreamStore";
import type {
  ChatMessage as ChatMsg,
  ResourceCard as ResourceCardType,
  ResourceResponse,
  SessionDetail,
  WikiCourse,
} from "@/lib/types";

const STARTER_PROMPTS = [
  "帮我梳理《人工智能导论》的学习路径",
  "我现在是大二，想补机器学习基础",
  "给我出一组神经网络入门练习题",
];

type CourseSelection = {
  sessionId: number | null;
  courseId: string | null;
};

function toResourceCard(resource: ResourceResponse): ResourceCardType {
  return {
    id: resource.id,
    turn_id: resource.turn_id,
    course_id: resource.course_id,
    resource_type: resource.resource_type,
    title: resource.title,
    content: resource.content,
    knowledge_point: resource.knowledge_point,
    agent_name: resource.agent_name,
    is_favorite: resource.is_favorite,
    confidence: resource.confidence,
    sources: resource.sources,
  };
}

function getDefaultCourseId(courses: WikiCourse[]): string | null {
  const defaultCourse = courses.find((course) => course.is_default) || courses[0];
  return defaultCourse?.id ?? null;
}

function buildHistoricalMessages(detail: SessionDetail): ChatMsg[] {
  const msgs: ChatMsg[] = detail.messages.map((message) => ({
    id: `history-${message.id}`,
    role: message.role,
    content: message.content,
    turn_id: message.turn_id,
  }));

  const assistantIndexByTurnId = new Map<string, number>();
  let latestAssistantIndex = -1;

  msgs.forEach((message, index) => {
    if (message.role !== "assistant") return;
    latestAssistantIndex = index;
    if (message.turn_id) {
      assistantIndexByTurnId.set(message.turn_id, index);
    }
  });

  const unmatchedResources: ResourceCardType[] = [];

  for (const resource of detail.resources) {
    const card = toResourceCard(resource);
    const targetIndex = resource.turn_id
      ? assistantIndexByTurnId.get(resource.turn_id)
      : undefined;

    if (typeof targetIndex === "number") {
      msgs[targetIndex] = {
        ...msgs[targetIndex],
        resources: [...(msgs[targetIndex].resources ?? []), card],
      };
    } else {
      unmatchedResources.push(card);
    }
  }

  if (unmatchedResources.length > 0) {
    if (latestAssistantIndex >= 0) {
      msgs[latestAssistantIndex] = {
        ...msgs[latestAssistantIndex],
        resources: [
          ...(msgs[latestAssistantIndex].resources ?? []),
          ...unmatchedResources,
        ],
      };
    } else {
      msgs.push({
        id: `history-resources-${detail.id}`,
        role: "assistant",
        content: "以下是本会话关联的学习资源。",
        resources: unmatchedResources,
      });
    }
  }

  return msgs;
}

export default function ChatPage() {
  const params = useParams();
  const router = useRouter();
  const sessionIdParam = params.sessionId as string;

  const parsedSessionId = parseInt(sessionIdParam, 10);
  const hasValidSessionId = !isNaN(parsedSessionId) && parsedSessionId > 0;
  const currentSessionId = hasValidSessionId ? parsedSessionId : null;

  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [studyMode, setStudyMode] = useState(true);
  const [courses, setCourses] = useState<WikiCourse[]>([]);
  const [manualCourseSelection, setManualCourseSelection] =
    useState<CourseSelection | null>(null);
  const [sessionCourse, setSessionCourse] = useState<CourseSelection>({
    sessionId: currentSessionId,
    courseId: null,
  });
  const [loading, setLoading] = useState(hasValidSessionId);
  const lastUserMessageRef = useRef<string>("");
  const lastStudyModeRef = useRef(true);
  const lastCourseIdRef = useRef<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const activeSessionIdRef = useRef<number | null>(currentSessionId);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const streamState = useChatStreamStore((state) =>
    hasValidSessionId
      ? getStreamStateForSession(state.streams, parsedSessionId)
      : getStreamStateForSession(state.streams, -1)
  );
  const startStream = useChatStreamStore((state) => state.startStream);
  const appendToken = useChatStreamStore((state) => state.appendToken);
  const setAgentStatus = useChatStreamStore((state) => state.setAgentStatus);
  const clearAgentStatus = useChatStreamStore((state) => state.clearAgentStatus);
  const setResources = useChatStreamStore((state) => state.setResources);
  const setWikiFallback = useChatStreamStore((state) => state.setWikiFallback);
  const setStreamError = useChatStreamStore((state) => state.setError);
  const finishStream = useChatStreamStore((state) => state.finishStream);
  const clearStream = useChatStreamStore((state) => state.clearStream);
  const setController = useChatStreamStore((state) => state.setController);
  const abortStream = useChatStreamStore((state) => state.abortStream);
  const defaultCourseId = useMemo(() => getDefaultCourseId(courses), [courses]);
  const sessionCourseId =
    sessionCourse.sessionId === currentSessionId ? sessionCourse.courseId : null;
  const selectedCourseId =
    manualCourseSelection?.sessionId === currentSessionId
      ? manualCourseSelection.courseId
      : sessionCourseId || defaultCourseId;

  useEffect(() => {
    activeSessionIdRef.current = currentSessionId;
    if (hasValidSessionId) {
      setLastSessionId(parsedSessionId);
    }
  }, [currentSessionId, hasValidSessionId, parsedSessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamState.streamingContent, scrollToBottom]);

  useEffect(() => {
    let cancelled = false;

    fetchWikiCourses()
      .then((items) => {
        if (cancelled) return;
        setCourses(items);
      })
      .catch(() => {
        if (cancelled) return;
        setCourses([]);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!hasValidSessionId) {
      return;
    }

    fetchSessionDetail(parsedSessionId)
      .then((detail) => {
        setSessionCourse({
          sessionId: parsedSessionId,
          courseId: detail.course_id ?? null,
        });
        setMessages(buildHistoricalMessages(detail));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [hasValidSessionId, parsedSessionId]);

  const handleSend = async (overrideMessage?: string) => {
    const trimmed = (overrideMessage ?? input).trim();
    if (!trimmed || streamState.isStreaming || !hasValidSessionId) return;

    lastUserMessageRef.current = trimmed;
    lastStudyModeRef.current = studyMode;
    lastCourseIdRef.current = selectedCourseId;

    const userMsg: ChatMsg = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    clearStream(parsedSessionId);
    startStream(parsedSessionId);

    const collectedResources: ResourceCardType[] = [];
    let collectedContent = "";

    abortStream(parsedSessionId);
    const controller = new AbortController();
    setController(parsedSessionId, controller);

    await streamChat(
      activeSessionIdRef.current,
      trimmed,
      {
        onSessionId: (newSessionId) => {
          if (activeSessionIdRef.current === newSessionId) {
            return;
          }
          activeSessionIdRef.current = newSessionId;
          router.replace(`/chat/${newSessionId}`);
        },
        onAgentStatus: (payload, sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          setAgentStatus(targetSessionId, payload.agent || "", payload.message);
        },
        onProfileUpdated: (sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          clearAgentStatus(targetSessionId);
        },
        onToken: (payload, sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          collectedContent += payload.token;
          appendToken(targetSessionId, payload.token);
        },
        onResourceCard: (resource, sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          collectedResources.push(resource);
          setResources(targetSessionId, [...collectedResources]);
        },
        onWikiFallback: (payload, sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          setWikiFallback(targetSessionId, payload.message);
        },
        onError: (payload, sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          setStreamError(targetSessionId, payload.message);
        },
        onDone: (sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          const assistantMsg: ChatMsg = {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: collectedContent,
            resources: [...collectedResources],
          };
          setMessages((prev) => [...prev, assistantMsg]);
          finishStream(targetSessionId);
        },
      },
      controller.signal,
      { studyMode, courseId: selectedCourseId }
    );
  };

  const pendingHandled = useRef(false);
  useEffect(() => {
    if (loading || pendingHandled.current) return;
    const pending = consumePendingMessage();
    if (pending) {
      pendingHandled.current = true;
      const timeoutId = window.setTimeout(() => {
        void handleSend(pending);
      }, 0);
      return () => window.clearTimeout(timeoutId);
    }
  });

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && streamState.isStreaming && hasValidSessionId) {
        abortStream(parsedSessionId);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [streamState.isStreaming, hasValidSessionId, parsedSessionId, abortStream]);

  const handleRegenerate = useCallback(() => {
    const lastMsg = lastUserMessageRef.current;
    if (!lastMsg || streamState.isStreaming || !hasValidSessionId) return;

    setMessages((prev) => {
      const lastAssistantIdx = prev.findLastIndex((m) => m.role === "assistant");
      if (lastAssistantIdx === -1) return prev;
      return prev.slice(0, lastAssistantIdx);
    });

    clearStream(parsedSessionId);
    startStream(parsedSessionId);

    const collectedResources: ResourceCardType[] = [];
    let collectedContent = "";

    abortStream(parsedSessionId);
    const controller = new AbortController();
    setController(parsedSessionId, controller);

    streamChat(
      activeSessionIdRef.current,
      lastMsg,
      {
        onSessionId: (newSessionId) => {
          if (activeSessionIdRef.current === newSessionId) return;
          activeSessionIdRef.current = newSessionId;
          router.replace(`/chat/${newSessionId}`);
        },
        onAgentStatus: (payload, sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          setAgentStatus(targetSessionId, payload.agent || "", payload.message);
        },
        onProfileUpdated: (sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          clearAgentStatus(targetSessionId);
        },
        onToken: (payload, sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          collectedContent += payload.token;
          appendToken(targetSessionId, payload.token);
        },
        onResourceCard: (resource, sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          collectedResources.push(resource);
          setResources(targetSessionId, [...collectedResources]);
        },
        onWikiFallback: (payload, sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          setWikiFallback(targetSessionId, payload.message);
        },
        onError: (payload, sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          setStreamError(targetSessionId, payload.message);
        },
        onDone: (sessionId) => {
          const targetSessionId = sessionId ?? activeSessionIdRef.current;
          if (targetSessionId === null) return;
          const assistantMsg: ChatMsg = {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: collectedContent,
            resources: [...collectedResources],
          };
          setMessages((prev) => [...prev, assistantMsg]);
          finishStream(targetSessionId);
        },
      },
      controller.signal,
      { studyMode: lastStudyModeRef.current, courseId: lastCourseIdRef.current }
    );
  }, [
    hasValidSessionId,
    parsedSessionId,
    streamState.isStreaming,
    router,
    clearStream,
    startStream,
    abortStream,
    setController,
    setAgentStatus,
    clearAgentStatus,
    appendToken,
    setResources,
    setWikiFallback,
    setStreamError,
    finishStream,
  ]);

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-57px)] items-center justify-center">
        <p className="text-sm text-[var(--color-warm-gray-400)]">
          正在加载会话...
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl bg-[var(--color-ivory)] ring-1 ring-[var(--color-warm-gray-200)]">
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-5 md:px-6 md:py-6">
        <div className="mx-auto flex min-h-full w-full max-w-5xl flex-col">
          {messages.length === 0 && !streamState.isStreaming && (
            <div className="flex flex-1 items-center justify-center py-10 md:py-16">
              <div className="grid w-full max-w-4xl gap-5 md:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)] md:items-center">
                <div className="text-center md:text-left">
                  <p className="mb-3 text-sm text-[var(--color-terracotta)]">
                    个性化学习助手
                  </p>
                  <h2 className="mb-4 text-3xl font-medium text-[var(--color-warm-gray-800)] md:text-4xl">
                    开始你的学习之旅
                  </h2>
                  <p className="max-w-xl text-sm leading-7 text-[var(--color-warm-gray-500)] md:text-base">
                    告诉我你的专业、年级、目标和薄弱点，我会结合学习画像为你组织知识、生成资料，并陪你一步步推进学习。
                  </p>
                </div>
                <div className="rounded-xl bg-[var(--color-parchment)] p-4 ring-1 ring-[var(--color-warm-gray-200)] md:p-5">
                  <div className="mb-3 text-xs tracking-[0.18em] text-[var(--color-warm-gray-400)] uppercase">
                    你可以这样开始
                  </div>
                  <div className="space-y-3">
                    {STARTER_PROMPTS.map((prompt) => (
                      <button
                        key={prompt}
                        type="button"
                        onClick={() => {
                          setInput(prompt);
                          inputRef.current?.focus();
                        }}
                        className="w-full rounded-xl bg-[var(--color-ivory)] px-4 py-3 text-left text-sm leading-6 text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:text-[var(--color-terracotta)]"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {messages.length > 0 && (
            <div className="mb-4 text-center">
              <p className="text-xs text-[var(--color-warm-gray-400)]">
                学习对话会持续更新你的画像与推荐内容。
              </p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <ChatMessage
              key={msg.id}
              role={msg.role}
              content={msg.content}
              isLast={idx === messages.length - 1}
              isStreaming={streamState.isStreaming}
              onRegenerate={msg.role === "assistant" ? handleRegenerate : undefined}
              onFollowUp={(q) => { setInput(q); inputRef.current?.focus(); }}
            >
              {msg.resources?.map((resource) => (
                <ResourceCard key={resource.id ?? resource.title} resource={resource} sessionId={currentSessionId} />
              ))}
            </ChatMessage>
          ))}

          {streamState.isStreaming && (
            <div className="mb-4">
              <AgentFlow
                timeline={streamState.agentTimeline}
                resources={streamState.resources}
                isStreaming={streamState.isStreaming}
              />
              {streamState.agentStatus && (
                <AgentStatus
                  agent={streamState.agentName}
                  message={streamState.agentStatus}
                />
              )}
              {streamState.wikiFallback && (
                <div className="mx-3 mb-3 rounded-xl bg-[var(--color-parchment)] px-3 py-2 text-xs text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)]">
                  {streamState.wikiFallback}
                </div>
              )}
              {streamState.streamingContent && (
                <div className="flex justify-start">
                  <div className="max-w-[88%] rounded-xl rounded-bl-sm bg-[var(--color-ivory)] px-5 py-4 ring-1 ring-[var(--color-warm-gray-200)] md:max-w-[78%]">
                    <StreamingText content={streamState.streamingContent} />
                    {streamState.resources.map((resource) => (
                      <ResourceCard key={resource.id ?? resource.title} resource={resource} sessionId={currentSessionId} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {streamState.error && (
            <div className="py-4 text-center">
              <p className="inline-block rounded-lg bg-[var(--color-parchment)] px-4 py-2 text-sm text-[var(--color-terracotta)] ring-1 ring-[var(--color-warm-gray-200)]">
                {streamState.error}
              </p>
              <div className="mt-2">
                <button
                  type="button"
                  onClick={handleRegenerate}
                  className="rounded-lg px-4 py-1.5 text-xs text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:text-[var(--color-terracotta)] hover:ring-[var(--color-terracotta)]"
                >
                  重试
                </button>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="border-t border-[var(--color-warm-gray-200)] bg-[var(--color-ivory)]/95 px-4 py-4 backdrop-blur-sm md:px-6">
        <div className="mx-auto w-full max-w-5xl rounded-xl bg-[var(--color-parchment)] p-4 ring-1 ring-[var(--color-warm-gray-200)]">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <p className="text-sm text-[var(--color-warm-gray-700)]">
                告诉我你的课程背景、目标和卡点
              </p>
              <p className="text-xs text-[var(--color-warm-gray-400)]">
                我会根据你的画像生成更贴合的讲解、题目和代码练习。
              </p>
            </div>
            <Link
              href={`/profile${hasValidSessionId ? `?session_id=${parsedSessionId}` : ""}`}
              className="shrink-0 text-xs text-[var(--color-terracotta)] hover:underline"
            >
              查看学习画像
            </Link>
          </div>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-lg bg-[var(--color-ivory)] p-1 ring-1 ring-[var(--color-warm-gray-200)]">
              <button
                type="button"
                onClick={() => setStudyMode(true)}
                className={`rounded-md px-3 py-1.5 text-xs transition-colors ${
                  studyMode
                    ? "bg-[var(--color-warm-gray-800)] text-white"
                    : "text-[var(--color-warm-gray-500)] hover:text-[var(--color-terracotta)]"
                }`}
              >
                辅导模式
              </button>
              <button
                type="button"
                onClick={() => setStudyMode(false)}
                className={`rounded-md px-3 py-1.5 text-xs transition-colors ${
                  !studyMode
                    ? "bg-[var(--color-warm-gray-800)] text-white"
                    : "text-[var(--color-warm-gray-500)] hover:text-[var(--color-terracotta)]"
                }`}
              >
                直接回答
              </button>
            </div>
            <label className="inline-flex items-center gap-2 rounded-lg bg-[var(--color-ivory)] px-2.5 py-1.5 text-xs text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)]">
              <span className="shrink-0">课程</span>
              <select
                value={selectedCourseId || ""}
                onChange={(event) => {
                  setManualCourseSelection({
                    sessionId: currentSessionId,
                    courseId: event.target.value || null,
                  });
                }}
                disabled={courses.length === 0 || streamState.isStreaming}
                className="max-w-[180px] bg-transparent text-[var(--color-warm-gray-700)] outline-none disabled:opacity-60"
                aria-label="选择课程知识库"
              >
                {courses.length === 0 ? (
                  <option value="">默认课程</option>
                ) : (
                  courses.map((course) => (
                    <option key={course.id} value={course.id}>
                      {course.title}
                    </option>
                  ))
                )}
              </select>
            </label>
          </div>
          <div className="flex gap-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="请输入你的学习需求..."
              aria-label="学习需求输入框"
              rows={1}
              className="flex-1 resize-none rounded-xl bg-[var(--color-ivory)] px-4 py-3 text-sm ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)]"
              disabled={streamState.isStreaming}
            />
            <VoiceInput
              onResult={(text) => { setInput((prev) => prev + text); inputRef.current?.focus(); }}
              disabled={streamState.isStreaming}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || streamState.isStreaming}
              className="rounded-xl bg-[var(--color-terracotta)] px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              发送
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
