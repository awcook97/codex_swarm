from __future__ import annotations

from dataclasses import dataclass
from urllib.request import Request, urlopen


@dataclass(slots=True)
class HttpResponse:
    url: str
    status: int
    text: str


class HttpTool:
    def __init__(self, user_agent: str = "SwarmHttpTool/1.0") -> None:
        self._user_agent = user_agent

    def get(self, url: str, timeout: float = 5.0) -> HttpResponse:
        req = Request(url, headers={"User-Agent": self._user_agent})
        with urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return HttpResponse(url=url, status=response.status, text=body)
