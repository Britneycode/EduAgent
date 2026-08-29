"use client";

import { useState, useEffect, useMemo } from "react";
import { fetchSessionDetail, fetchWikiCourses } from "@/lib/api";
import { setLastSessionId } from "@/lib/lastSession";
import type {
  ChatMessage,
  ResourceCard as ResourceCardType,
  ResourceResponse,
  SessionDetail,
  WikiCourse,
} from "@/lib/types";

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

export function buildHistoricalMessages(detail: SessionDetail): ChatMessage[] {
  const msgs: ChatMessage[] = detail.messages.map((message) => ({
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

export function useChatSession(sessionIdParam: string) {
  const parsedSessionId = parseInt(sessionIdParam, 10);
  const hasValidSessionId = !isNaN(parsedSessionId) && parsedSessionId > 0;
  const currentSessionId = hasValidSessionId ? parsedSessionId : null;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [courses, setCourses] = useState<WikiCourse[]>([]);
  const [sessionCourse, setSessionCourse] = useState<{
    sessionId: number | null;
    courseId: string | null;
  }>({
    sessionId: currentSessionId,
    courseId: null,
  });
  const [loading, setLoading] = useState(hasValidSessionId);

  const defaultCourseId = useMemo(() => getDefaultCourseId(courses), [courses]);
  const sessionCourseId =
    sessionCourse.sessionId === currentSessionId ? sessionCourse.courseId : null;
  const selectedCourseId = sessionCourseId || defaultCourseId;

  useEffect(() => {
    if (hasValidSessionId) {
      setLastSessionId(parsedSessionId);
    }
  }, [hasValidSessionId, parsedSessionId]);

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

    let cancelled = false;

    fetchSessionDetail(parsedSessionId)
      .then((detail) => {
        if (cancelled) return;
        setSessionCourse({
          sessionId: parsedSessionId,
          courseId: detail.course_id ?? null,
        });
        setMessages(buildHistoricalMessages(detail));
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [hasValidSessionId, parsedSessionId]);

  return {
    parsedSessionId,
    hasValidSessionId,
    currentSessionId,
    messages,
    setMessages,
    courses,
    selectedCourseId,
    loading: hasValidSessionId ? loading : false,
  };
}
