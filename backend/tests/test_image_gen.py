from __future__ import annotations

from app.core.config import get_settings
from app.core.image_gen import ImageGenClient


def test_image_client_uses_independent_dashscope_key(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "dashscope-key")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "image-scope-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "wrong-provider-key")
    monkeypatch.setenv("SPARK_API_PASSWORD", "spark-password")
    get_settings.cache_clear()

    try:
        client = ImageGenClient()
    finally:
        get_settings.cache_clear()

    assert client.api_key == "image-scope-key"
