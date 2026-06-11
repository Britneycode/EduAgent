from __future__ import annotations

import asyncio

from app.agents.tutor_agent import TutorAgent
from app.core.llm import BaseLLMClient


class RecordingLLMClient(BaseLLMClient):
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate_text(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "先判断你的目标，再一步步提示。"


def test_tutor_agent_study_mode_prompt_uses_coaching_structure() -> None:
    client = RecordingLLMClient()
    agent = TutorAgent(llm_client=client)

    answer = asyncio.run(
        agent.answer(
            "反向传播到底怎么算？",
            {"learning_goal": "备考", "cognitive_style": "图文结合"},
            study_mode=True,
        )
    )

    prompt = client.prompts[0]
    assert answer == "先判断你的目标，再一步步提示。"
    assert "当前启用 Study Mode" in prompt
    assert "诊断目标 → 分步提示 → 理解检查 → 小结" in prompt
    assert "避免一开始直接给最终答案" in prompt
