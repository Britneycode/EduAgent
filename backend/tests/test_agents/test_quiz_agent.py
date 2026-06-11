from __future__ import annotations

import asyncio
import json

from app.agents.quiz_agent import QuizAgent
from app.core.llm import BaseLLMClient


class StubLLMClient(BaseLLMClient):
    async def generate_text(self, prompt: str) -> str:
        assert "反向传播" in prompt
        assert "图文结合" in prompt
        assert "复习" in prompt
        assert "上游学习讲义：" in prompt
        return "1. 基础理解题\n答案：用于检验概念理解。"


class StructuredQuizLLMClient(BaseLLMClient):
    async def generate_text(self, prompt: str) -> str:
        assert '"question_count": 10' in prompt
        return json.dumps(
            {
                "questions": [
                    {
                        "id": 1,
                        "type": "choice",
                        "question": "反向传播的核心用途是什么？",
                        "options": ["A. 计算梯度", "B. 生成图像"],
                        "answer": "A",
                        "explanation": "反向传播用于高效计算梯度。",
                    }
                ]
            },
            ensure_ascii=False,
        )


PROFILE = {
    "cognitive_style": "图文结合",
    "learning_goal": "复习",
    "learning_pace": "平稳",
    "coding_level": "一般",
}


def test_quiz_agent_generates_quiz_resource() -> None:
    agent = QuizAgent(llm_client=StubLLMClient())

    resource = asyncio.run(
        agent.generate_quiz(
            "反向传播",
            PROFILE,
            document_content="这是上游讲义正文。",
        )
    )

    assert resource.title == "反向传播练习题"
    assert resource.resource_type == "quiz"
    assert resource.knowledge_point == "反向传播"
    assert resource.agent_name == "QuizAgent"
    assert "基础理解题" in resource.content


def test_quiz_agent_builds_prompt_with_document_context() -> None:
    agent = QuizAgent(llm_client=StubLLMClient())

    prompt = agent.build_prompt(
        "反向传播",
        PROFILE,
        document_content="这是上游讲义正文。",
    )

    assert "请围绕学习主题输出中文练习题" in prompt
    assert "主题：反向传播" in prompt
    assert "上游学习讲义：" in prompt
    assert "图文结合" in prompt
    assert "复习" in prompt


def test_quiz_agent_adds_training_settings_to_structured_quiz() -> None:
    agent = QuizAgent(llm_client=StructuredQuizLLMClient())

    resource = asyncio.run(agent.generate_quiz("反向传播", PROFILE))
    payload = json.loads(resource.content)

    assert payload["settings"]["mode"] == "training"
    assert payload["settings"]["question_count"] == 1
    assert payload["settings"]["time_limit_sec"] == 600
    assert payload["questions"][0]["difficulty"] == "easy"
    assert payload["questions"][0]["knowledge_point"] == "反向传播"
