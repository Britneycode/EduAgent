import type {
  SSEEvent,
  AgentStatusPayload,
  TokenPayload,
  ResourceCard,
  ErrorPayload,
  WikiFallbackPayload,
  ProfileUpdateProposedPayload,
  ProgressPayload,
} from "./types";
import { getChatStreamUrl } from "./api";
import { getToken } from "./auth";

export function parseSSEChunk(chunk: string): SSEEvent[] {
  const events: SSEEvent[] = [];
  const blocks = chunk.split("\n\n");

  for (const block of blocks) {
    const trimmed = block.trim();
    if (!trimmed) continue;

    const dataLine = trimmed
      .split("\n")
      .find((line) => line.startsWith("data: "));
    if (!dataLine) continue;

    try {
      const json = JSON.parse(dataLine.slice(6));
      events.push(json as SSEEvent);
    } catch {
      // 跳过解析失败的块
    }
  }

  return events;
}

export interface StreamChatHandlers {
  onAgentStatus?: (payload: AgentStatusPayload, sessionId: number | null) => void;
  onProfileUpdateProposed?: (
    payload: ProfileUpdateProposedPayload,
    sessionId: number | null
  ) => void;
  onProgress?: (payload: ProgressPayload, sessionId: number | null) => void;
  onHeartbeat?: (sessionId: number | null) => void;
  onToken?: (payload: TokenPayload, sessionId: number | null) => void;
  onResourceCard?: (resource: ResourceCard, sessionId: number | null) => void;
  onWikiFallback?: (payload: WikiFallbackPayload, sessionId: number | null) => void;
  onError?: (payload: ErrorPayload, sessionId: number | null) => void;
  onDone?: (sessionId: number | null) => void;
  onSessionId?: (sessionId: number) => void;
}

export interface StreamChatOptions {
  studyMode?: boolean;
  courseId?: string | null;
}

export async function streamChat(
  sessionId: number | null,
  message: string,
  handlers: StreamChatHandlers,
  signal?: AbortSignal,
  options?: StreamChatOptions
): Promise<void> {
  const body: Record<string, unknown> = {
    message,
    study_mode: Boolean(options?.studyMode),
  };
  if (sessionId !== null) {
    body.session_id = sessionId;
  }
  if (options?.courseId) {
    body.course_id = options.courseId;
  }

  let response: Response;
  try {
    response = await fetch(getChatStreamUrl(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
    });
  } catch {
    if (signal?.aborted) {
      handlers.onDone?.(sessionId);
      return;
    }
    handlers.onError?.(
      { message: "连接服务器失败，请检查网络" },
      sessionId
    );
    return;
  }

  if (!response.ok) {
    handlers.onError?.(
      { message: "连接服务器失败，请检查网络" },
      sessionId
    );
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    handlers.onError?.(
      { message: "浏览器不支持流式响应" },
      sessionId
    );
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let errorReceived = false;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = parseSSEChunk(buffer);

      // 清空已处理的数据
      const lastDoubleNewline = buffer.lastIndexOf("\n\n");
      if (lastDoubleNewline !== -1) {
        buffer = buffer.slice(lastDoubleNewline + 2);
      }

      for (const event of events) {
        if (errorReceived) break;

        // 通知前端新的 session_id
        if (event.session_id && event.session_id > 0) {
          handlers.onSessionId?.(event.session_id);
        }

        switch (event.type) {
          case "agent_status": {
            const p = event.payload as AgentStatusPayload;
            handlers.onAgentStatus?.(p, event.session_id);
            break;
          }
          case "profile_update_proposed": {
            const p = event.payload as ProfileUpdateProposedPayload;
            handlers.onProfileUpdateProposed?.(p, event.session_id);
            break;
          }
          case "progress": {
            const p = event.payload as ProgressPayload;
            handlers.onProgress?.(p, event.session_id);
            break;
          }
          case "heartbeat":
            handlers.onHeartbeat?.(event.session_id);
            break;
          case "token": {
            const p = event.payload as TokenPayload;
            handlers.onToken?.(p, event.session_id);
            break;
          }
          case "resource_card": {
            const p = event.payload as ResourceCard;
            handlers.onResourceCard?.(p, event.session_id);
            break;
          }
          case "wiki_fallback": {
            const p = event.payload as WikiFallbackPayload;
            handlers.onWikiFallback?.(p, event.session_id);
            break;
          }
          case "error": {
            errorReceived = true;
            const p = event.payload as ErrorPayload;
            handlers.onError?.(p, event.session_id);
            break;
          }
          case "done":
            handlers.onDone?.(event.session_id);
            break;
        }
      }
    }
  } catch {
    if (signal?.aborted) {
      handlers.onDone?.(sessionId);
      return;
    }
    if (!errorReceived) {
      handlers.onError?.(
        { message: "连接已中断，请重试" },
        sessionId
      );
    }
  }
}
