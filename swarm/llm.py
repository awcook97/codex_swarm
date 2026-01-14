from __future__ import annotations

import json
from dataclasses import dataclass


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
        content = json.dumps(plan, indent=2)
        return LLMResponse(content=content)
