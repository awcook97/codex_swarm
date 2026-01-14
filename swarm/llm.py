from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LLMResponse:
    content: str


class LLM:
    async def complete(self, prompt: str) -> LLMResponse:  # pragma: no cover - interface
        raise NotImplementedError


class MockLLM(LLM):
    def __init__(self, seed: int = 42) -> None:
        self._seed = seed

    async def complete(self, prompt: str) -> LLMResponse:
        lowered = prompt.lower()
        if "role: planner" in lowered:
            plan = {
                "steps": [
                    {
                        "id": 1,
                        "agent": "researcher",
                        "task": "Gather relevant context for the objective.",
                        "depends_on": [],
                    },
                    {
                        "id": 2,
                        "agent": "coder",
                        "task": "Draft an output artifact based on the research.",
                        "depends_on": [1],
                    },
                    {
                        "id": 3,
                        "agent": "critic",
                        "task": "Review the drafted output for completeness and clarity.",
                        "depends_on": [2],
                    },
                ],
                "seed": self._seed,
            }
            return LLMResponse(content=json.dumps(plan, indent=2))
        if "role: researcher" in lowered:
            objective = _extract_line(prompt, "objective")
            if "animation" in objective or "movie" in objective:
                payload = {
                    "summary": "Animation work needs a renderable deliverable with a short arc.",
                    "deliverable": "gif",
                    "needs": ["gif encoder"],
                }
            else:
                payload = {
                    "summary": "Provide general guidance and assumptions based on the objective.",
                    "deliverable": "html",
                    "needs": [],
                }
            return LLMResponse(content=json.dumps(payload))
        if "role: coder" in lowered:
            objective = _extract_line(prompt, "objective")
            if "animation" in objective or "movie" in objective:
                payload = {
                    "deliverable": "gif",
                    "subject": objective,
                    "project_type": "animation",
                }
            else:
                payload = {
                    "deliverable": "html",
                    "subject": objective,
                    "project_type": "landing_page",
                }
            return LLMResponse(content=json.dumps(payload))
        if "role: critic" in lowered:
            payload = {"approved": True, "notes": "Looks good."}
            return LLMResponse(content=json.dumps(payload))
        return LLMResponse(content=json.dumps({"summary": "Unrecognized prompt."}))


class OllamaLLM(LLM):
    def __init__(self, model: str, base_url: str, endpoint: str, timeout: int, retries: int) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._endpoint = endpoint
        self._timeout = timeout
        self._retries = max(0, retries)

    async def complete(self, prompt: str) -> LLMResponse:
        payload = {"model": self._model, "prompt": prompt, "stream": False}
        response = await self._post_with_retries(payload)
        content = response.get("response")
        if content is None:
            message = response.get("message", {})
            content = message.get("content", "")
        return LLMResponse(content=content or "")

    async def _post_with_retries(self, payload: dict[str, Any]) -> dict[str, Any]:
        attempts = self._retries + 1
        last_exc: Exception | None = None
        for _ in range(attempts):
            try:
                return await asyncio.to_thread(self._post, self._endpoint, payload)
            except TimeoutError as exc:
                last_exc = exc
            except urllib.error.HTTPError as exc:
                if exc.code == 404 and self._endpoint != "/api/chat":
                    chat_payload = {
                        "model": self._model,
                        "messages": [{"role": "user", "content": payload["prompt"]}],
                        "stream": False,
                    }
                    return await asyncio.to_thread(self._post, "/api/chat", chat_payload)
                last_exc = exc
            except urllib.error.URLError as exc:
                last_exc = exc
        raise RuntimeError(f"Ollama request failed: {last_exc}") from last_exc

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        url = f"{self._base_url}{endpoint}"
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)


def _extract_line(prompt: str, prefix: str) -> str:
    prefix_lower = f"{prefix.lower()}:"
    for line in prompt.splitlines():
        if line.lower().startswith(prefix_lower):
            return line.split(":", 1)[-1].strip().lower()
    return ""
