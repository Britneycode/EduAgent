import { describe, expect, it } from "vitest";
import { parseAnimationScript } from "@/components/ui/AnimationPlayer";

describe("parseAnimationScript", () => {
  it("extracts explicit Chinese storyboard scenes and fields", () => {
    const scenes = parseAnimationScript(`
## 镜头1：问题引入
- 时长：12 秒
- 旁白：先展示学生看到的原始问题。
- 画面元素：黑板、输入向量、问题气泡
- 关键公式：y = f(x)
- 学习目的：建立学习动机

## 第2个镜头：步骤拆解
旁白：把复杂任务拆成三个小步骤。
画面：流程线从左到右展开
目的：降低认知负担
`);

    expect(scenes).toHaveLength(2);
    expect(scenes[0]).toMatchObject({
      title: "问题引入",
      duration: "12 秒",
      narration: "先展示学生看到的原始问题。",
      visuals: "黑板、输入向量、问题气泡",
      formula: "y = f(x)",
      purpose: "建立学习动机",
    });
    expect(scenes[1]).toMatchObject({
      title: "步骤拆解",
      narration: "把复杂任务拆成三个小步骤。",
      visuals: "流程线从左到右展开",
      purpose: "降低认知负担",
    });
  });

  it("supports numbered scene headings", () => {
    const scenes = parseAnimationScript(`
1. 分镜：概念入口
旁白：从生活例子切入。

2、场景：公式出现
公式：loss = -log p(y|x)
`);

    expect(scenes).toHaveLength(2);
    expect(scenes[0].title).toBe("概念入口");
    expect(scenes[1].title).toBe("公式出现");
    expect(scenes[1].formula).toBe("loss = -log p(y|x)");
  });

  it("falls back to paragraph scenes when no storyboard heading exists", () => {
    const scenes = parseAnimationScript(`
# 动画讲解脚本

第一段用于说明问题背景。

第二段展示核心概念。

第三段总结学习目标。
`);

    expect(scenes).toHaveLength(3);
    expect(scenes[0].title).toBe("片段 1");
    expect(scenes[0].narration).toContain("第一段");
  });
});
