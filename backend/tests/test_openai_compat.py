"""Passerelle compatible OpenAI : traduction des options et du format, réponse, flux SSE, repli local."""

import json
from typing import Any

import httpx
import pytest

from gmix.llm.catalog import load_catalog
from gmix.llm.ollama import OllamaClient, OllamaError, Usage
from gmix.llm.openai_compat import OpenAIClient
from gmix.llm.service import BudgetExceeded, LLMService
from gmix.settings import get_settings


def _client(handler: Any) -> OpenAIClient:
    local = OllamaClient("http://127.0.0.1:1")
    client = OpenAIClient("https://passerelle.test/v1/", "cle", "deepseek-x", local=local, serves={"qwen2.5:3b"})
    client._http = httpx.AsyncClient(base_url="https://passerelle.test/v1", transport=httpx.MockTransport(handler))
    return client


async def test_chat_sends_the_gateway_model_options_and_schema() -> None:
    sent: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content), path=request.url.path)
        return httpx.Response(200, json={
            "model": "deepseek-x", "usage": {"prompt_tokens": 12, "completion_tokens": 5},
            "choices": [{"message": {"content": '{"a": 1}'}, "finish_reason": "length"}],
        })  # fmt: skip

    client = _client(handler)
    schema = {"type": "object", "properties": {"a": {"type": "integer"}}}
    result = await client.chat(
        "qwen2.5:3b", [{"role": "user", "content": "x"}], options={"num_predict": 50, "num_ctx": 4096}, fmt=schema
    )
    assert sent["path"] == "/v1/chat/completions" and sent["model"] == "deepseek-x"
    assert sent["max_tokens"] == 50 and "num_ctx" not in sent
    assert sent["response_format"]["json_schema"]["schema"] == schema
    assert result.content == '{"a": 1}' and result.done_reason == "length"
    assert (result.usage.prompt_tokens, result.usage.completion_tokens) == (12, 5)
    await client.aclose()


async def test_stream_yields_chunks_then_usage() -> None:
    lines = [
        {"choices": [{"delta": {"content": "Bon"}}]},
        {"choices": [{"delta": {"content": "jour"}}]},
        {"choices": [], "usage": {"prompt_tokens": 3, "completion_tokens": 2}},
    ]
    sse = "".join(f"data: {json.dumps(line)}\n\n" for line in lines) + "data: [DONE]\n\n"
    client = _client(lambda request: httpx.Response(200, text=sse))
    items = [item async for item in client.chat_stream("qwen2.5:3b", [{"role": "user", "content": "x"}])]
    assert items[:2] == ["Bon", "jour"]
    assert isinstance(items[2], Usage) and items[2].completion_tokens == 2
    await client.aclose()


@pytest.mark.parametrize("var", ["OPENAI_BASE_URL", "OPENAI_MODEL"])
def test_openai_provider_requires_base_url_and_model(monkeypatch: pytest.MonkeyPatch, var: str) -> None:
    values = {"openai_base_url": "https://passerelle.test/v1", "openai_model": "deepseek-x"}
    values[var.lower()] = " "
    settings = get_settings().model_copy(update={"llm_provider": "openai", **values})
    monkeypatch.setattr("gmix.llm.service.get_settings", lambda: settings)
    with pytest.raises(ValueError, match=f"LLM_PROVIDER=openai : {var} est vide"):
        LLMService.from_settings(with_cache=False)


async def test_installed_models_keeps_the_served_tags_when_ollama_is_down() -> None:
    client = _client(lambda request: httpx.Response(200, json={}))
    assert await client.installed_models() == {"qwen2.5:3b"}  # Ollama injoignable (port 1) : rien de local
    await client.aclose()


MSG = [{"role": "user", "content": "x"}]
OK = {"choices": [{"message": {"content": "ok"}}]}


def _flaky(statuses: list[int], calls: list[int]) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        status = statuses[min(len(calls), len(statuses)) - 1]
        return httpx.Response(status, json=OK if status == 200 else {"error": "x"})

    return handler


@pytest.fixture(autouse=True)
def _no_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("gmix.llm.openai_compat.RETRY_DELAY_S", 0)


async def test_503_then_success_is_retried() -> None:
    calls: list[int] = []
    client = _client(_flaky([503, 200], calls))
    assert (await client.chat("qwen2.5:3b", MSG)).content == "ok" and len(calls) == 2
    await client.aclose()


async def test_three_503_give_a_clear_error_after_three_attempts() -> None:
    calls: list[int] = []
    client = _client(_flaky([503], calls))
    with pytest.raises(OllamaError, match="Passerelle OpenAI indisponible après 3 essais"):
        await client.chat("qwen2.5:3b", MSG)
    assert len(calls) == 3
    await client.aclose()


async def test_400_is_not_retried() -> None:
    calls: list[int] = []
    client = _client(_flaky([400], calls))
    with pytest.raises(OllamaError, match="refusé"):
        await client.chat("qwen2.5:3b", MSG)
    assert len(calls) == 1
    await client.aclose()


async def test_too_long_context_is_refused_before_any_http_call() -> None:
    calls: list[int] = []
    client = _client(_flaky([200], calls))
    catalog = load_catalog()
    client._serves = {catalog.models[catalog.task("system.ping").model].tag}
    service = LLMService(catalog, client)
    with pytest.raises(BudgetExceeded):
        await service.text("system.ping", [{"role": "user", "content": "mot " * 2000}])
    assert calls == []
    await client.aclose()
