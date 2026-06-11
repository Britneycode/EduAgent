import { describe, expect, it } from "vitest";
import { buildLearningPathGraph } from "@/components/learning/LearningPathGraph";
import type { LearningPathNode } from "@/lib/types";

function node(
  concept: string,
  prerequisites: string[] = [],
  status: LearningPathNode["status"] = "pending"
): LearningPathNode {
  return {
    concept,
    chapter: "ch",
    section: "s",
    description: "",
    prerequisites,
    status,
  };
}

describe("buildLearningPathGraph", () => {
  it("builds prerequisite edges and layered positions", () => {
    const graph = buildLearningPathGraph([
      node("梯度下降"),
      node("多层感知机", ["梯度下降"]),
      node("反向传播", ["梯度下降", "多层感知机"], "completed"),
    ]);

    expect(graph.edges.map((edge) => edge.id)).toEqual([
      "梯度下降->多层感知机",
      "梯度下降->反向传播",
      "多层感知机->反向传播",
    ]);
    const levels = new Map(graph.nodes.map((item) => [item.id, item.level]));
    expect(levels.get("梯度下降")).toBe(0);
    expect(levels.get("多层感知机")).toBe(1);
    expect(levels.get("反向传播")).toBe(2);
  });

  it("falls back to sequential edges for historical paths without prerequisites", () => {
    const graph = buildLearningPathGraph([
      node("A"),
      { ...node("B"), prerequisites: undefined },
      { ...node("C"), prerequisites: undefined },
    ]);

    expect(graph.edges.map((edge) => edge.id)).toEqual(["A->B", "B->C"]);
  });
});
