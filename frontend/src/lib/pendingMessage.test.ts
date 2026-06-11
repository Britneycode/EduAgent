import { beforeEach, describe, expect, it } from "vitest";
import { consumePendingMessage, setPendingMessage } from "@/lib/pendingMessage";

describe("pendingMessage", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    consumePendingMessage();
  });

  it("persists the pending message in sessionStorage", () => {
    setPendingMessage("帮我生成学习路径");

    expect(window.sessionStorage.getItem("eduagent.pendingMessage")).toBe(
      "帮我生成学习路径"
    );
    expect(consumePendingMessage()).toBe("帮我生成学习路径");
    expect(window.sessionStorage.getItem("eduagent.pendingMessage")).toBeNull();
  });

  it("can consume a message restored after module memory is gone", () => {
    window.sessionStorage.setItem("eduagent.pendingMessage", "刷新后继续发送");

    expect(consumePendingMessage()).toBe("刷新后继续发送");
    expect(consumePendingMessage()).toBeNull();
  });
});
