"""Client d'une passerelle compatible OpenAI (/v1/chat/completions), même interface que `OllamaClient`.

Choisi par `LLM_PROVIDER=openai` (.env) : toutes les tâches de texte du catalogue partent vers `OPENAI_MODEL`, quel que
soit le modèle Ollama qu'elles nomment. Les embeddings et les modèles de décision (tev1) restent sur l'Ollama local :
la passerelle n'a pas de route /v1/embeddings, et l'API /v1/systemone n'existe que chez Ollama.
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from gmix.llm.ollama import CONNECT_TIMEOUT_S, ChatResult, OllamaClient, OllamaError, Usage

# Options Ollama du catalogue -> paramètres OpenAI ; les autres (num_ctx…) n'ont pas d'équivalent et sont ignorées.
OPTIONS = {"num_predict": "max_tokens", "temperature": "temperature", "top_p": "top_p", "seed": "seed", "stop": "stop"}


class OpenAIClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        local: OllamaClient,
        serves: set[str],
        timeout_s: float = 300.0,
    ) -> None:
        """`serves` : tags du catalogue servis par la passerelle (modèles de chat) ; `local` : Ollama, pour le reste."""
        self.model = model
        self.local = local
        self._serves = serves
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_s, connect=CONNECT_TIMEOUT_S * 5),  # hôte distant : poignée TLS comprise
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def aclose(self) -> None:
        await self._http.aclose()
        await self.local.aclose()

    async def version(self) -> str:
        response = await self._http.get("/models")
        if response.status_code >= 400:
            raise OllamaError(f"/models -> HTTP {response.status_code}: {response.text[:500]}")
        return f"openai:{self.model}"

    async def installed_models(self) -> set[str]:
        """Modèles de chat du catalogue (servis par la passerelle) + ceux de l'Ollama local (embeddings, décision)."""
        try:
            local = await self.local.installed_models()
        except httpx.HTTPError:
            local = set()  # Ollama arrêté : le texte marche quand même
        return self._serves | local

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        options: dict[str, Any] | None = None,
        fmt: str | dict[str, Any] | None = None,
        think: bool | None = None,
        keep_alive: str | None = None,
    ) -> ChatResult:
        data = await self._post("/chat/completions", self._body(messages, options, fmt, stream=False))
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        return ChatResult(
            content=message.get("content") or "",
            thinking=message.get("reasoning_content"),
            usage=self._usage(data),
            done_reason=choice.get("finish_reason"),  # "length" comme chez Ollama : sortie tronquée
        )

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        options: dict[str, Any] | None = None,
        think: bool | None = None,
        keep_alive: str | None = None,
    ) -> AsyncIterator[str | Usage]:
        """Fragments de texte au fil de l'eau (SSE), puis un `Usage` final."""
        body = self._body(messages, options, None, stream=True)
        usage = Usage(model=self.model)
        async with self._http.stream("POST", "/chat/completions", json=body) as response:
            if response.status_code >= 400:
                raise OllamaError(
                    f"/chat/completions -> HTTP {response.status_code}: {(await response.aread())[:500]!r}"
                )
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                data = json.loads(payload)
                if data.get("error"):
                    raise OllamaError(str(data["error"]))
                if data.get("usage"):
                    usage = self._usage(data)
                for choice in data.get("choices") or []:
                    chunk = (choice.get("delta") or {}).get("content")
                    if chunk:
                        yield chunk
        yield usage

    async def embed(
        self, model: str, inputs: list[str], *, keep_alive: str | None = None
    ) -> tuple[list[list[float]], Usage]:
        return await self.local.embed(model, inputs, keep_alive=keep_alive)

    async def decide(
        self,
        model: str,
        state: str | dict[str, Any] | list[Any],
        questions: dict[str, dict[str, Any]],
        *,
        keep_alive: str | None = None,
    ) -> dict[str, Any]:
        return await self.local.decide(model, state, questions, keep_alive=keep_alive)

    def _body(
        self, messages: list[dict[str, str]], options: dict[str, Any] | None, fmt: Any, *, stream: bool
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"model": self.model, "messages": messages, "stream": stream}
        body |= {OPTIONS[k]: v for k, v in (options or {}).items() if k in OPTIONS and v is not None}
        if stream:
            body["stream_options"] = {"include_usage": True}
        if isinstance(fmt, dict):  # schéma JSON : sortie contrainte, comme `format` chez Ollama
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "sortie", "schema": fmt}}
        elif fmt == "json":
            body["response_format"] = {"type": "json_object"}
        return body

    def _usage(self, data: dict[str, Any]) -> Usage:
        u = data.get("usage") or {}
        return Usage(
            model=data.get("model") or self.model,
            prompt_tokens=u.get("prompt_tokens") or 0,
            completion_tokens=u.get("completion_tokens") or 0,
        )

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        response = await self._http.post(path, json=body)
        if response.status_code >= 400:
            raise OllamaError(f"{path} -> HTTP {response.status_code}: {response.text[:500]}")
        return response.json()
