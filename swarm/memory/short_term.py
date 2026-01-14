from __future__ import annotations

from collections import defaultdict
from typing import Any


class ShortTermMemory:
    def __init__(self) -> None:
        self._store: dict[tuple[str, str], dict[str, Any]] = defaultdict(dict)

    def put(self, run_id: str, agent: str, key: str, value: Any) -> None:
        self._store[(run_id, agent)][key] = value

    def get(self, run_id: str, agent: str, key: str) -> Any | None:
        return self._store.get((run_id, agent), {}).get(key)

    def list(self, run_id: str, agent: str) -> dict[str, Any]:
        return dict(self._store.get((run_id, agent), {}))
