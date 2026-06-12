import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import ChatPage from "@/app/(main)/chat/[sessionId]/page";
import { useChatStreamStore } from "@/store/chatStreamStore";

const replaceMock = vi.fn();
const useParamsMock = vi.fn();
const fetchSessionDetailMock = vi.fn();
const fetchWikiCoursesMock = vi.fn();
const confirmAgentProfileUpdateMock = vi.fn();
const streamChatMock = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => useParamsMock(),
  useRouter: () => ({ replace: replaceMock }),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    confirmAgentProfileUpdate: (...args: unknown[]) =>
      confirmAgentProfileUpdateMock(...args),
    fetchSessionDetail: (...args: unknown[]) => fetchSessionDetailMock(...args),
    fetchWikiCourses: (...args: unknown[]) => fetchWikiCoursesMock(...args),
  };
});

vi.mock("@/lib/sse", () => ({
  streamChat: (...args: unknown[]) => streamChatMock(...args),
}));

describe("ChatPage", () => {
  beforeEach(() => {
    replaceMock.mockReset();
    fetchSessionDetailMock.mockReset();
    fetchWikiCoursesMock.mockReset();
    confirmAgentProfileUpdateMock.mockReset();
    streamChatMock.mockReset();
    fetchSessionDetailMock.mockResolvedValue({
      id: 1,
      title: "会话",
      course_id: null,
      created_at: "2026-04-19T00:00:00Z",
      updated_at: "2026-04-19T00:00:00Z",
      messages: [],
      resources: [],
    });
    fetchWikiCoursesMock.mockResolvedValue([
      {
        id: "ai_intro",
        title: "人工智能导论",
        description: "",
        metadata_course_id: "AI101",
        chapter_count: 12,
        concept_count: 80,
        estimated_hours: 32,
        is_default: true,
      },
    ]);
    streamChatMock.mockResolvedValue(undefined);
    confirmAgentProfileUpdateMock.mockResolvedValue({
      user_id: 1,
      session_id: 1,
      major: null,
      grade: null,
      knowledge_base: {},
      cognitive_style: null,
      learning_goal: "复习反向传播",
      weak_points: [],
      learning_pace: null,
      interest_areas: [],
      coding_level: null,
      weekly_hours: null,
    });
    useChatStreamStore.setState({
      streams: {},
      controllers: {},
    });
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  it("重新进入同一会话页面时继续展示该会话的流式内容", async () => {
    useParamsMock.mockReturnValue({ sessionId: "1" });

    useChatStreamStore.getState().startStream(1);
    useChatStreamStore.getState().appendToken(1, "这是持续生成中的回答");

    const firstRender = render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText("这是持续生成中的回答")).toBeInTheDocument();
    });

    firstRender.unmount();

    const secondRender = render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText("这是持续生成中的回答")).toBeInTheDocument();
    });

    secondRender.unmount();
  });

  it("隐藏聊天页课程选择器但保留输入控制", async () => {
    useParamsMock.mockReturnValue({ sessionId: "1" });

    render(<ChatPage />);

    await screen.findByLabelText("学习需求输入框");

    expect(screen.queryByLabelText("选择课程知识库")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "辅导模式" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "直接回答" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "发送" })).toBeInTheDocument();
  });

  it("发送消息时继续使用已有会话的隐藏课程上下文", async () => {
    useParamsMock.mockReturnValue({ sessionId: "1" });
    fetchSessionDetailMock.mockResolvedValueOnce({
      id: 1,
      title: "会话",
      course_id: "computer_networks",
      created_at: "2026-04-19T00:00:00Z",
      updated_at: "2026-04-19T00:00:00Z",
      messages: [],
      resources: [],
    });

    render(<ChatPage />);

    const input = await screen.findByLabelText("学习需求输入框");
    fireEvent.change(input, { target: { value: "讲讲 TCP 拥塞控制" } });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    await waitFor(() => {
      expect(streamChatMock).toHaveBeenCalled();
    });

    expect(streamChatMock.mock.calls[0][4]).toMatchObject({
      studyMode: true,
      courseId: "computer_networks",
    });
  });

  it("shows and confirms proposed profile updates from the stream", async () => {
    useParamsMock.mockReturnValue({ sessionId: "1" });
    streamChatMock.mockImplementation(
      async (
        _sessionId: unknown,
        _message: unknown,
        handlers: {
          onProfileUpdateProposed: (payload: unknown, sessionId: number) => void;
          onDone: (sessionId: number) => void;
        }
      ) => {
        handlers.onProfileUpdateProposed(
          {
            session_id: 1,
            update: { learning_goal: "复习反向传播" },
            changed_fields: ["learning_goal"],
          },
          1
        );
        handlers.onDone(1);
      }
    );

    render(<ChatPage />);

    const input = await screen.findByLabelText("学习需求输入框");
    fireEvent.change(input, { target: { value: "我想复习反向传播" } });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    await screen.findByText("Agent 建议更新学习画像");
    fireEvent.click(screen.getByRole("button", { name: "确认" }));

    await waitFor(() => {
      expect(confirmAgentProfileUpdateMock).toHaveBeenCalledWith(1, {
        learning_goal: "复习反向传播",
      });
    });
    expect(await screen.findByText("学习画像已更新")).toBeInTheDocument();
  });
});
