from __future__ import annotations

import asyncio
import json

from app.agents.media_agent import MediaAgent
from app.agents.resource_types import AgentResource
from app.core.llm import BaseLLMClient
from app.mcp_server import _resource_to_dict


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


class StubMindmapLLMClient(BaseLLMClient):
    """返回固定内容的 LLM 桩，用于 generate_mindmap 测试。"""

    def __init__(self, response: str) -> None:
        self.response = response

    async def generate_text(self, prompt: str) -> str:
        return self.response


MINDMAP_MERMAID = "mindmap\n  root((TCP))\n    三次握手\n    四次挥手"


def _patch_render(monkeypatch, result: str) -> list[str]:
    """注入思维导图渲染桩（禁止真实网络），返回记录调用入参的列表。"""
    calls: list[str] = []

    async def fake_render(mermaid_code: str) -> str:
        calls.append(mermaid_code)
        return result

    monkeypatch.setattr("app.agents.media_agent.render_mindmap_image", fake_render)
    return calls


def test_generate_mindmap_fills_image_url_from_render(monkeypatch) -> None:
    llm_response = f"# 思维导图\n\n```mermaid\n{MINDMAP_MERMAID}\n```\n\n补充说明"
    calls = _patch_render(monkeypatch, "data:image/png;base64,xxx")
    agent = MediaAgent(llm_client=StubMindmapLLMClient(llm_response))

    resource = asyncio.run(agent.generate_mindmap("TCP", profile={}))

    assert calls == [MINDMAP_MERMAID]
    assert resource.image_url == "data:image/png;base64,xxx"
    assert resource.content == llm_response.strip()


def test_generate_mindmap_skips_render_without_mermaid(monkeypatch) -> None:
    calls = _patch_render(monkeypatch, "data:image/png;base64,xxx")
    agent = MediaAgent(llm_client=StubMindmapLLMClient("纯文字回答，不含导图"))

    resource = asyncio.run(agent.generate_mindmap("TCP", profile={}))

    assert calls == []
    assert resource.image_url == ""
    assert resource.content == "纯文字回答，不含导图"


def test_generate_mindmap_keeps_content_when_render_fails(monkeypatch) -> None:
    llm_response = f"```mermaid\n{MINDMAP_MERMAID}\n```"
    _patch_render(monkeypatch, "")
    agent = MediaAgent(llm_client=StubMindmapLLMClient(llm_response))

    resource = asyncio.run(agent.generate_mindmap("TCP", profile={}))

    assert resource.image_url == ""
    assert resource.content == llm_response.strip()


def test_resource_to_dict_includes_image_url() -> None:
    resource = AgentResource(
        title="TCP思维导图",
        resource_type="mindmap",
        content="内容",
        knowledge_point="TCP",
        agent_name="MediaAgent",
        image_url="data:image/png;base64,xxx",
    )

    payload = _resource_to_dict(resource)

    assert payload["image_url"] == "data:image/png;base64,xxx"
