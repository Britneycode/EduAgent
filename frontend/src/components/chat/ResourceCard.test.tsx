import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";

import { ResourceCard } from "@/components/chat/ResourceCard";

describe("ResourceCard video resources", () => {
  it("renders video label, structured bilibili link and primary action", () => {
    render(
      <ResourceCard
        resource={{
          id: 1,
          resource_type: "video",
          title: "反向传播相关视频",
          content:
            "# 反向传播相关视频\n\n1. [反向传播从零讲解](https://www.bilibili.com/video/BV123)\n   - 平台：B站\n   - 推荐理由：适合作为补充讲解视频。\n   - 摘要：链式法则和梯度计算入门。",
          knowledge_point: "反向传播",
          agent_name: "VideoAgent",
        }}
      />
    );

    expect(screen.getByText("相关视频")).toBeInTheDocument();
    expect(screen.getByText("推荐理由")).toBeInTheDocument();
    expect(screen.getByText("链式法则和梯度计算入门。")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /反向传播从零讲解/ });
    expect(link).toHaveAttribute("href", "https://www.bilibili.com/video/BV123");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    const cta = screen.getByRole("link", { name: "打开 B站" });
    expect(cta).toHaveAttribute("href", "https://www.bilibili.com/video/BV123");
    expect(cta).toHaveAttribute("target", "_blank");
    expect(screen.queryByRole("button", { name: "MD" })).not.toBeInTheDocument();
  });

  it("renders unavailable video search as a light warning", () => {
    render(
      <ResourceCard
        resource={{
          id: 2,
          resource_type: "video",
          title: "计算机网络相关视频",
          content:
            "# 计算机网络相关视频\n\n视频搜索暂不可用，暂时无法联网检索 B站学习视频。\n\n- 原因：TAVILY_API_KEY 未配置",
          knowledge_point: "计算机网络",
          agent_name: "VideoAgent",
        }}
      />
    );

    expect(screen.getByText(/视频搜索暂不可用/)).toBeInTheDocument();
    expect(screen.getByText(/TAVILY_API_KEY 未配置/)).toBeInTheDocument();
  });
});
