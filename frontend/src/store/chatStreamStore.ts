import { create } from "zustand";
import type { ProgressPayload, ResourceCard } from "@/lib/types";

export interface AgentTimelineItem {
  agent: string;
  status: string;
  message: string;
}

export interface ChatStreamState {
  isStreaming: boolean;
  streamingContent: string;
  agentName: string;
  agentStatus: string | null;
  agentTimeline: AgentTimelineItem[];
  resources: ResourceCard[];
  progress: ProgressPayload | null;
  wikiFallback: string | null;
  error: string | null;
}

interface ChatStreamStoreState {
  streams: Record<number, ChatStreamState>;
  controllers: Record<number, AbortController | null>;
  startStream: (sessionId: number) => void;
  appendToken: (sessionId: number, token: string) => void;
  setAgentStatus: (
    sessionId: number,
    agentName: string,
    agentStatus: string | null
  ) => void;
  clearAgentStatus: (sessionId: number) => void;
  setResources: (sessionId: number, resources: ResourceCard[]) => void;
  setProgress: (sessionId: number, progress: ProgressPayload | null) => void;
  setWikiFallback: (sessionId: number, wikiFallback: string | null) => void;
  setError: (sessionId: number, error: string | null) => void;
  finishStream: (sessionId: number) => void;
  clearStream: (sessionId: number) => void;
  setController: (sessionId: number, controller: AbortController | null) => void;
  abortStream: (sessionId: number) => void;
}

const EMPTY_STREAM_STATE: ChatStreamState = {
  isStreaming: false,
  streamingContent: "",
  agentName: "",
  agentStatus: null,
  agentTimeline: [],
  resources: [],
  progress: null,
  wikiFallback: null,
  error: null,
};

function createEmptyStreamState(): ChatStreamState {
  return {
    ...EMPTY_STREAM_STATE,
    agentTimeline: [],
    resources: [],
    progress: null,
  };
}

export function getStreamStateForSession(
  streams: Record<number, ChatStreamState>,
  sessionId: number
): ChatStreamState {
  return streams[sessionId] ?? EMPTY_STREAM_STATE;
}

function updateStream(
  streams: Record<number, ChatStreamState>,
  sessionId: number,
  updater: (stream: ChatStreamState) => ChatStreamState
) {
  return {
    ...streams,
    [sessionId]: updater(streams[sessionId] ?? createEmptyStreamState()),
  };
}

function updateAgentTimeline(
  timeline: AgentTimelineItem[],
  item: AgentTimelineItem
): AgentTimelineItem[] {
  const existingIndex = timeline.findIndex((step) => step.agent === item.agent);
  if (existingIndex === -1) {
    return [...timeline, item];
  }

  return timeline.map((step, index) =>
    index === existingIndex ? { ...step, ...item } : step
  );
}

export function createChatStreamStore() {
  return create<ChatStreamStoreState>()((set, get) => ({
    streams: {},
    controllers: {},
    startStream: (sessionId) =>
      set((state) => ({
        streams: {
          ...state.streams,
          [sessionId]: {
            ...createEmptyStreamState(),
            isStreaming: true,
          },
        },
      })),
    appendToken: (sessionId, token) =>
      set((state) => ({
        streams: updateStream(state.streams, sessionId, (stream) => ({
          ...stream,
          isStreaming: true,
          streamingContent: stream.streamingContent + token,
          agentName: stream.agentName ? "" : stream.agentName,
          agentStatus: stream.agentStatus ? null : stream.agentStatus,
        })),
      })),
    setAgentStatus: (sessionId, agentName, agentStatus) =>
      set((state) => ({
        streams: updateStream(state.streams, sessionId, (stream) => ({
          ...stream,
          isStreaming: true,
          agentName,
          agentStatus,
          agentTimeline: agentName
            ? updateAgentTimeline(stream.agentTimeline, {
                agent: agentName,
                status: agentStatus ? "working" : "idle",
                message: agentStatus ?? "",
              })
            : stream.agentTimeline,
        })),
      })),
    clearAgentStatus: (sessionId) =>
      set((state) => ({
        streams: updateStream(state.streams, sessionId, (stream) => ({
          ...stream,
          agentName: "",
          agentStatus: null,
        })),
      })),
    setResources: (sessionId, resources) =>
      set((state) => ({
        streams: updateStream(state.streams, sessionId, (stream) => ({
          ...stream,
          resources,
        })),
      })),
    setProgress: (sessionId, progress) =>
      set((state) => ({
        streams: updateStream(state.streams, sessionId, (stream) => ({
          ...stream,
          progress,
        })),
      })),
    setWikiFallback: (sessionId, wikiFallback) =>
      set((state) => ({
        streams: updateStream(state.streams, sessionId, (stream) => ({
          ...stream,
          wikiFallback,
        })),
      })),
    setError: (sessionId, error) =>
      set((state) => ({
        streams: updateStream(state.streams, sessionId, (stream) => ({
          ...stream,
          isStreaming: false,
          error,
        })),
      })),
    finishStream: (sessionId) =>
      set((state) => ({
        streams: updateStream(state.streams, sessionId, (stream) => ({
          ...stream,
          isStreaming: false,
        })),
        controllers: {
          ...state.controllers,
          [sessionId]: null,
        },
      })),
    clearStream: (sessionId) =>
      set((state) => ({
        streams: {
          ...state.streams,
          [sessionId]: createEmptyStreamState(),
        },
      })),
    setController: (sessionId, controller) =>
      set((state) => ({
        controllers: {
          ...state.controllers,
          [sessionId]: controller,
        },
      })),
    abortStream: (sessionId) => {
      get().controllers[sessionId]?.abort();
      set((state) => ({
        controllers: {
          ...state.controllers,
          [sessionId]: null,
        },
      }));
    },
  }));
}

export const useChatStreamStore = createChatStreamStore();
