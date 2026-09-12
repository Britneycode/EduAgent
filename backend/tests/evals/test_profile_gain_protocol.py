"""评测数据契约测试：不访问外部模型。"""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "profile_gain", Path(__file__).with_name("eval_profile_gain.py")
)
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def payload():
    return {label: {dim: {"score": 3, "evidence": "原文", "reason": "理由"}
                    for dim in evaluation.DIMS} for label in ("A", "B")}


def test_accepts_wrapped_complete_scores():
    value = payload()
    assert evaluation.validate_judgment('```json\n' + json.dumps(value) + '\n```') == value


@pytest.mark.parametrize("score", [0, 6, True, "5"])
def test_rejects_invalid_scores(score):
    value = payload()
    value["A"][evaluation.DIMS[0]]["score"] = score
    with pytest.raises(ValueError):
        evaluation.validate_judgment(json.dumps(value))


def test_rejects_missing_evidence():
    value = payload()
    value["B"][evaluation.DIMS[0]]["evidence"] = ""
    with pytest.raises(ValueError):
        evaluation.validate_judgment(json.dumps(value))

@pytest.mark.asyncio
async def test_judge_retries_truncation_and_keeps_raw(monkeypatch):
    import httpx
    from app.core.llm import OpenAICompatibleLLMClient
    responses = iter([
        {"choices": [{"finish_reason": "length", "message": {"content": "{"}}]},
        {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(payload())}}]},
    ])
    def handler(request):
        body = json.loads(request.content)
        assert body["response_format"] == {"type": "json_object"}
        return httpx.Response(200, json=next(responses))
    original = httpx.AsyncClient
    monkeypatch.setattr(evaluation.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler)))
    async def no_wait(_):
        pass
    monkeypatch.setattr(evaluation.asyncio, "sleep", no_wait)
    record = {}
    judge = OpenAICompatibleLLMClient(api_key="test-only", api_base_url="https://example.test/v1")
    await evaluation.judge_response(judge, "评分", record, lambda: None)
    assert len(record["attempts"]) == 2
    assert record["attempts"][0]["finish_reason"] == "length"
    assert record["parsed"] == payload()


@pytest.mark.asyncio
async def test_judge_stops_on_invalid_credentials(monkeypatch):
    import httpx
    from app.core.llm import OpenAICompatibleLLMClient
    original = httpx.AsyncClient
    monkeypatch.setattr(evaluation.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(lambda request: httpx.Response(401))))
    record = {}
    judge = OpenAICompatibleLLMClient(api_key="test-only", api_base_url="https://example.test/v1")
    with pytest.raises(httpx.HTTPStatusError):
        await evaluation.judge_response(judge, "评分", record, lambda: None)
    assert len(record["attempts"]) == 1
    assert record["attempts"][0]["http_status"] == 401
