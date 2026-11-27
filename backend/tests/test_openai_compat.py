"""Passerelle compatible OpenAI : traduction des options et du format, réponse, flux SSE, repli local."""

import json
from typing import Any

import httpx

from gmix.llm.ollama import OllamaClient, Usage
from gmix.llm.openai_compat import OpenAIClient


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


async def test_installed_models_keeps_the_served_tags_when_ollama_is_down() -> None:
    client = _client(lambda request: httpx.Response(200, json={}))
    assert await client.installed_models() == {"qwen2.5:3b"}  # Ollama injoignable (port 1) : rien de local
    await client.aclose()
