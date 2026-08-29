"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { BrainCircuit, Send, Sparkles, UserRoundCheck } from "lucide-react";
import { streamChat } from "@/lib/sse";
import { confirmAgentProfileUpdate } from "@/lib/api";
import { consumePendingMessage } from "@/lib/pendingMessage";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { StreamingText } from "@/components/chat/StreamingText";
import { VoiceInput } from "@/components/chat/VoiceInput";
import { AgentFlow } from "@/components/chat/AgentFlow";
import { AgentStatus } from "@/components/chat/AgentStatus";
import { ResourceCard } from "@/components/chat/ResourceCard";
import { ProfileUpdateBanner } from "@/components/chat/ProfileUpdateBanner";
import { useChatSession } from "@/hooks/useChatSession";
import {
  getStreamStateForSession,
  useChatStreamStore,
} from "@/store/chatStreamStore";
import type {
  ChatMessage as ChatMsg,
  ProfileUpdateProposedPayload,
  ResourceCard as ResourceCardType,
} from "@/lib/types";

const STARTER_PROMPTS = [
  "帮我梳理《人工智能导论》的学习路径",
  "我现在是大二，想补机器学习基础",
  "给我出一组神经网络入门练习题",
];

export default function ChatPage() {
  const params = useParams();
  const router = useRouter();
  const sessionIdParam = params.sessionId as string;

  const {
    parsedSessionId,
    hasValidSessionId,
    currentSessionId,
    messages,
    setMessages,
    selectedCourseId,
    loading,
  } = useChatSession(sessionIdParam);

  const [input, setInput] = useState("");
  const [studyMode, setStudyMode] = useState(true);
  const [profileProposal, setProfileProposal] =
    useState<ProfileUpdateProposedPayload | null>(null);
  const [profileConfirmState, setProfileConfirmState] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");
  const [profileConfirmMessage, setProfileConfirmMessage] = useState<string | null>(
    null
  );

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
  const setProgress = useChatStreamStore((state) => state.setProgress);
  const setWikiFallback = useChatStreamStore((state) => state.setWikiFallback);
  const setStreamError = useChatStreamStore((state) => state.setError);
  const finishStream = useChatStreamStore((state) => state.finishStream);
  const clearStream = useChatStreamStore((state) => state.clearStream);
  const setController = useChatStreamStore((state) => state.setController);
  const abortStream = useChatStreamStore((state) => state.abortStream);

  useEffect(() => {
    activeSessionIdRef.current = currentSessionId;
  }, [currentSessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamState.streamingContent, scrollToBottom]);

  const handleSend = useCallback(
    async (overrideMessage?: string) => {
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
      setProfileProposal(null);
      setProfileConfirmState("idle");
      setProfileConfirmMessage(null);
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
          onProfileUpdateProposed: (payload, sessionId) => {
            const targetSessionId = sessionId ?? activeSessionIdRef.current;
            if (targetSessionId === null) return;
            setProfileProposal(payload);
            setProfileConfirmState("idle");
            setProfileConfirmMessage(null);
            clearAgentStatus(targetSessionId);
          },
          onProgress: (payload, sessionId) => {
            const targetSessionId = sessionId ?? activeSessionIdRef.current;
            if (targetSessionId === null) return;
            setProgress(targetSessionId, payload);
          },
          onHeartbeat: () => {},
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
    },
    [
      input,
      hasValidSessionId,
      parsedSessionId,
      studyMode,
      selectedCourseId,
      streamState.isStreaming,
      router,
      setMessages,
      clearStream,
      startStream,
      abortStream,
      setController,
      setAgentStatus,
      clearAgentStatus,
      appendToken,
      setResources,
      setProgress,
      setWikiFallback,
      setStreamError,
      finishStream,
    ]
  );

  const handleRegenerate = useCallback(() => {
    if (!lastUserMessageRef.current || streamState.isStreaming) return;
    handleSend(lastUserMessageRef.current);
  }, [handleSend, streamState.isStreaming]);

  const handleConfirmProfileProposal = useCallback(async () => {
    if (!profileProposal || profileConfirmState === "saving") return;
    const targetSessionId = profileProposal.session_id ?? currentSessionId;
    setProfileConfirmState("saving");
    setProfileConfirmMessage(null);
    try {
      await confirmAgentProfileUpdate(targetSessionId, profileProposal.update);
      setProfileProposal(null);
      setProfileConfirmState("saved");
      setProfileConfirmMessage("学习画像已更新");
      window.setTimeout(() => {
        setProfileConfirmMessage(null);
        setProfileConfirmState("idle");
      }, 2400);
    } catch (error) {
      setProfileConfirmState("error");
      setProfileConfirmMessage(
        error instanceof Error ? error.message : "确认画像更新失败"
      );
    }
  }, [currentSessionId, profileConfirmState, profileProposal]);

  useEffect(() => {
    if (!hasValidSessionId) return;
    const pending = consumePendingMessage();
    if (pending) {
      const timer = setTimeout(() => {
        handleSend(pending);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [hasValidSessionId, handleSend]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

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

          {profileProposal && (
            <ProfileUpdateBanner
              proposal={profileProposal}
              confirmState={profileConfirmState}
              confirmMessage={profileConfirmMessage}
              onConfirm={handleConfirmProfileProposal}
              onDismiss={() => {
                setProfileProposal(null);
                setProfileConfirmState("idle");
                setProfileConfirmMessage(null);
              }}
            />
          )}

          {streamState.isStreaming && (
            <div className="mb-4">
              <AgentFlow
                timeline={streamState.agentTimeline}
                resources={streamState.resources}
                isStreaming={streamState.isStreaming}
                progress={streamState.progress}
              />
              {streamState.agentStatus && (
                <AgentStatus
                  agent={streamState.agentName}
                  message={streamState.agentStatus}
                  progress={streamState.progress}
                />
              )}
              {streamState.wikiFallback && (
                <div className="mx-3 mb-3 rounded-xl bg-[var(--color-parchment)] px-3 py-2 text-xs text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)]">
                  {streamState.wikiFallback}
                </div>
              )}
              {streamState.streamingContent && (
                <div className="flex justify-start">
                  <div className="relative w-full max-w-[840px] pl-5">
                    <span className="absolute left-0 top-2 h-[calc(100%-0.5rem)] w-px bg-[var(--color-warm-gray-200)]" />
                    <span className="absolute left-[-3px] top-2 h-2 w-2 rounded-full bg-[var(--color-terracotta)]" />
                    <div className="mb-2 rounded-xl bg-[var(--color-parchment)]/65 px-3 py-2 text-sm leading-6 text-[var(--color-warm-gray-700)] shadow-[var(--shadow-ring)]">
                      <StreamingText content={streamState.streamingContent} />
                    </div>
                    {streamState.resources.length > 0 && (
                      <div className="space-y-2">
                        {streamState.resources.map((resource) => (
                          <ResourceCard key={resource.id ?? resource.title} resource={resource} sessionId={currentSessionId} />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {!streamState.isStreaming && profileConfirmMessage && (
            <div className="py-2 text-center">
              <p
                className={`inline-block rounded-lg bg-[var(--color-parchment)] px-4 py-2 text-sm ${
                  profileConfirmState === "error"
                    ? "text-red-600"
                    : "text-[var(--color-terracotta)]"
                } ring-1 ring-[var(--color-warm-gray-200)]`}
              >
                {profileConfirmMessage}
              </p>
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
              className="inline-flex shrink-0 items-center gap-1.5 text-xs text-[var(--color-terracotta)] hover:underline"
            >
              <UserRoundCheck className="h-3.5 w-3.5" />
              查看学习画像
            </Link>
          </div>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-lg bg-[var(--color-ivory)] p-1 ring-1 ring-[var(--color-warm-gray-200)]">
              <button
                type="button"
                onClick={() => setStudyMode(true)}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs transition-colors ${
                  studyMode
                    ? "bg-[var(--color-warm-gray-800)] text-white"
                    : "text-[var(--color-warm-gray-500)] hover:text-[var(--color-terracotta)]"
                }`}
              >
                <BrainCircuit className="h-3.5 w-3.5" />
                辅导模式
              </button>
              <button
                type="button"
                onClick={() => setStudyMode(false)}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs transition-colors ${
                  !studyMode
                    ? "bg-[var(--color-warm-gray-800)] text-white"
                    : "text-[var(--color-warm-gray-500)] hover:text-[var(--color-terracotta)]"
                }`}
              >
                <Sparkles className="h-3.5 w-3.5" />
                直接回答
              </button>
            </div>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
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
            <div className="flex gap-3 sm:contents">
              <VoiceInput
                onResult={(text) => { setInput((prev) => prev + text); inputRef.current?.focus(); }}
                disabled={streamState.isStreaming}
              />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || streamState.isStreaming}
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-[var(--color-terracotta)] px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none"
              >
                发送
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
