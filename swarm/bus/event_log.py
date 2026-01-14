from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Event:
    timestamp: datetime
    event_type: str
    payload: dict[str, Any]


class EventLog:
    def __init__(self) -> None:
        self._events: list[Event] = []

    def log(self, event_type: str, payload: dict[str, Any]) -> None:
        self._events.append(
            Event(
                timestamp=datetime.now(timezone.utc),
                event_type=event_type,
                payload=payload,
            )
        )

    def list_events(self) -> list[Event]:
        return list(self._events)
