import { describe, expect, it } from "vitest";
import { buildWikiGraph } from "@/components/wiki/KnowledgeGraphView";
import type { WikiConceptNode } from "@/lib/types";

function concept(
  name: string,
  prerequisites: string[] = []
): WikiConceptNode {
  return {
    name,
    chapter: "ch01",
    section: "",
    prerequisites,
    description: "",
  };
}

describe("buildWikiGraph", () => {
  it("builds dependency edges and topological levels", () => {
    const graph = buildWikiGraph([
      concept("人工智能的定义与本质"),
      concept("AI发展史与三次浪潮", ["人工智能的定义与本质"]),
      concept("AI核心分支与研究领域", [
        "人工智能的定义与本质",
        "AI发展史与三次浪潮",
      ]),
    ]);

    expect(graph.edges.map((edge) => edge.id)).toEqual([
      "人工智能的定义与本质->AI发展史与三次浪潮",
      "人工智能的定义与本质->AI核心分支与研究领域",
      "AI发展史与三次浪潮->AI核心分支与研究领域",
    ]);

    const levels = new Map(graph.nodes.map((node) => [node.id, node.level]));
    expect(levels.get("人工智能的定义与本质")).toBe(0);
    expect(levels.get("AI发展史与三次浪潮")).toBe(1);
    expect(levels.get("AI核心分支与研究领域")).toBe(2);
  });

  it("falls back to sequential edges when a chapter has no local dependencies", () => {
    const graph = buildWikiGraph([
      concept("A", ["跨章节前置"]),
      concept("B", ["另一个跨章节前置"]),
      concept("C", []),
    ]);

    expect(graph.edges.map((edge) => edge.id)).toEqual(["A->B", "B->C"]);
  });
});
