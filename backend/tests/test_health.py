from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


def test_health_endpoint_returns_status_and_warning_field() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "llm_warning" in data
    assert "safety_warning" in data
    assert "tts_warning" in data
    assert data["cache"]["enabled"] is True
    assert data["cache"]["backend"] in {"memory", "redis", "disabled"}
    assert "vector_store" in data
    assert data["vector_store"]["backend"] in {"numpy", "chroma-http", None}


def test_health_endpoint_returns_warning_text_when_provider_reports_warning(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        main_module, "get_llm_configuration_warning", lambda: "缺少星火配置"
    )

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["llm_warning"] == "缺少星火配置"
