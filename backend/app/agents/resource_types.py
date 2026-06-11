from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentResource:
    title: str
    resource_type: str
    content: str
    knowledge_point: str
    agent_name: str
    wiki_fallback: bool = False
    wiki_context: str = ""
    confidence: float = 0.0
    sources: list[dict[str, Any]] = field(default_factory=list)
