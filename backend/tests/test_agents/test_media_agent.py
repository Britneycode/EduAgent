from __future__ import annotations

import asyncio
import json

from app.agents.media_agent import MediaAgent
from app.core.llm import BaseLLMClient


class StubLLMClient(BaseLLMClient):
    async def generate_text(self, prompt: str) -> str:
        return json.dumps(
            {
                "slides": [
                    {
                        "title": "反向传播概述",
                        "key_points": ["链式法则", "梯度计算", "参数更新"],
                        "summary": "理解误差如何沿网络反向传播",
                    },
                    {
                        "title": "反向传播要点",
                        "key_points": ["前向计算", "损失函数", "反向求导"],
                        "summary": "把复杂求导拆成局部梯度相乘",
                    },
                ]
            },
            ensure_ascii=False,
        )


class StubImageGenClient:
    async def generate_images(self, prompts: list[str]) -> list[dict[str, str]]:
        return [
            {"url": f"https://example.com/slide-{index}.png"}
            for index, _prompt in enumerate(prompts, start=1)
        ]


def test_generate_ppt_images_uses_ppt_resource_type(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agents.media_agent.ImageGenClient",
        lambda: StubImageGenClient(),
    )
    agent = MediaAgent(llm_client=StubLLMClient())

    resource = asyncio.run(
        agent.generate_ppt_images("反向传播", profile={}, document_content="讲义")
    )

    payload = json.loads(resource.content)
    assert resource.resource_type == "ppt"
    assert payload["type"] == "ppt_images"
    assert [slide["image_url"] for slide in payload["slides"]] == [
        "https://example.com/slide-1.png",
        "https://example.com/slide-2.png",
    ]
