from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.agents.common import build_profile_lines, build_wiki_context_with_sources
from app.agents.resource_types import AgentResource
from app.core.code_sandbox import CodeSandboxError, extract_python_code, validate_python_code
from app.core.llm import BaseLLMClient, get_llm_client

if TYPE_CHECKING:
    from app.wiki.wiki_service import WikiService

logger = logging.getLogger(__name__)


class CodeAgent:
    """代码实践生成 Agent。"""

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        wiki_service: WikiService | None = None,
    ) -> None:
        self.llm_client = llm_client or get_llm_client()
        self.wiki_service = wiki_service

    async def generate_code(
        self,
        topic: str,
        profile: dict[str, Any] | None,
        document_content: str | None = None,
        quiz_content: str | None = None,
        course_id: str | None = None,
    ) -> AgentResource:
        normalized_topic = topic.strip() if topic else "当前学习主题"
        wiki_context, wiki_fallback, confidence, sources = (
            await self._build_wiki_context(normalized_topic, course_id=course_id)
        )
        prompt = self.build_prompt(
            normalized_topic,
            profile or {},
            wiki_context=wiki_context,
            document_content=document_content or "",
            quiz_content=quiz_content or "",
        )
        content = await self.llm_client.generate_text(prompt)
        return AgentResource(
            title=f"{normalized_topic}代码实践",
            resource_type="code",
            content=self._normalize_content(normalized_topic, content),
            knowledge_point=normalized_topic,
            agent_name="CodeAgent",
            wiki_fallback=wiki_fallback,
            wiki_context=wiki_context,
            confidence=confidence,
            sources=sources,
        )

    def build_prompt(
        self,
        topic: str,
        profile: dict[str, Any],
        *,
        wiki_context: str = "",
        document_content: str = "",
        quiz_content: str = "",
    ) -> str:
        profile_lines = self._build_profile_lines(profile)
        parts = [
            "你是 EduAgent 的代码实践助手。",
            "请围绕学习主题输出中文代码实践内容，默认提供 Python 示例。",
            f"主题：{topic}",
        ]

        if wiki_context:
            parts.extend(["", wiki_context])

        if document_content:
            parts.extend(["", "上游学习讲义：", document_content])

        if quiz_content:
            parts.extend(["", "上游练习题：", quiz_content])

        parts.extend(
            [
                "",
                "学生画像：",
                *profile_lines,
                "输出要求：",
                "1. 只输出中文内容。",
                "2. 固定包含以下小节：代码目标、实验步骤、Python 示例、预期输出、练习建议。",
                "3. 示例要紧扣主题，便于学生动手验证。",
                "4. 难度与学生画像匹配，默认适合课程复习。",
                "5. 第一个代码块必须是可直接运行的 ```python 代码块。",
                "6. Python 示例只能使用标准库，不依赖 numpy/pandas/sklearn 等第三方库。",
                "7. 代码运行后必须产生清晰 stdout，便于学生对照预期输出。",
                "8. 内容适合直接展示在学习资料卡片中，不要输出系统提示语。",
            ]
        )
        return "\n".join(parts)

    def _build_profile_lines(self, profile: dict[str, Any]) -> list[str]:
        return build_profile_lines(
            profile,
            ("learning_goal", "cognitive_style", "coding_level", "knowledge_base"),
        )

    async def _build_wiki_context(
        self, topic: str, course_id: str | None = None
    ) -> tuple[str, bool, float, list[dict[str, Any]]]:
        return await build_wiki_context_with_sources(
            self.wiki_service,
            query=topic,
            course_id=course_id,
            logger=logger,
        )

    def _normalize_content(self, topic: str, content: str) -> str:
        normalized = content.strip()
        if self._has_safe_first_python_block(normalized):
            return normalized

        logger.info("CodeAgent 输出缺少可运行安全代码块，使用标准库兜底示例")
        return self._build_fallback_content(topic)

    def _has_safe_first_python_block(self, content: str) -> bool:
        if not content.strip():
            return False
        try:
            code = extract_python_code(content, code_index=0)
            validate_python_code(code)
        except CodeSandboxError:
            return False
        return True

    def _build_fallback_content(self, topic: str) -> str:
        topic_literal = repr(topic)
        return f"""# {topic}代码实践

## 代码目标

用一个纯标准库 Python 小实验，把「{topic}」拆成若干学习检查点，并计算当前练习的平均掌握度。这个示例不依赖第三方库，可以直接在 EduAgent 的 Python 沙箱中运行。

## 实验步骤

1. 定义本次代码实践的主题。
2. 准备几个学习检查点和模拟得分。
3. 逐项打印检查点结果。
4. 计算平均掌握度，并给出下一步练习建议。

## Python 示例

```python
from statistics import mean

topic = {topic_literal}
checkpoints = [
    {{"name": "说出核心概念", "score": 4}},
    {{"name": "手动推演一个小例子", "score": 3}},
    {{"name": "解释关键步骤的原因", "score": 4}},
    {{"name": "完成一次代码复现", "score": 5}},
]

scores = [item["score"] for item in checkpoints]

print("代码实践主题:", topic)
print("学习检查点:")
for index, item in enumerate(checkpoints, start=1):
    print(f"{{index}}. {{item['name']}} - {{item['score']}}/5")

average_score = mean(scores)
print("平均掌握度:", round(average_score, 2), "/ 5")

if average_score >= 4:
    print("建议: 可以尝试改写示例，加入自己的测试数据。")
else:
    print("建议: 先补齐低分检查点，再重新运行本实验。")
```

## 预期输出

运行后会看到主题、4 个检查点、平均掌握度，以及一条下一步练习建议。

## 练习建议

把检查点替换成你对「{topic}」的真实学习任务，并调整分数；再次运行代码，观察建议如何变化。
"""
