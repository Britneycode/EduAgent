import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import ChatPage from "@/app/(main)/chat/[sessionId]/page";
import { useChatStreamStore } from "@/store/chatStreamStore";

const replaceMock = vi.fn();
const useParamsMock = vi.fn();
const fetchSessionDetailMock = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => useParamsMock(),
  useRouter: () => ({ replace: replaceMock }),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchSessionDetail: (...args: unknown[]) => fetchSessionDetailMock(...args),
  };
});

describe("ChatPage", () => {
  beforeEach(() => {
    replaceMock.mockReset();
    fetchSessionDetailMock.mockReset();
    fetchSessionDetailMock.mockResolvedValue({
      id: 1,
      title: "会话",
      created_at: "2026-04-19T00:00:00Z",
      updated_at: "2026-04-19T00:00:00Z",
      messages: [],
      resources: [],
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
});
