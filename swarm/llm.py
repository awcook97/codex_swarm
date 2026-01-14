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
    def __init__(self, model: str, url: str) -> None:
        self._model = model
        self._url = url

    async def complete(self, prompt: str) -> LLMResponse:
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }
        try:
            response = await asyncio.to_thread(self._post, payload)
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        content = response.get("response", "")
        return LLMResponse(content=content)

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self._url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)


def _extract_line(prompt: str, prefix: str) -> str:
    prefix_lower = f"{prefix.lower()}:"
    for line in prompt.splitlines():
        if line.lower().startswith(prefix_lower):
            return line.split(":", 1)[-1].strip().lower()
    return ""
