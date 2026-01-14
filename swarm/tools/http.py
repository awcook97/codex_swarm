from __future__ import annotations

from dataclasses import dataclass
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json


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
        try:
            with urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                status = getattr(response, "status", None) or getattr(response, "getcode", lambda: 0)()
                return HttpResponse(url=url, status=int(status), text=body)
        except HTTPError as exc:
            # HTTPError contains status code and may contain a body
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = str(exc)
            return HttpResponse(url=url, status=getattr(exc, "code", 0), text=body)
        except URLError as exc:
            return HttpResponse(url=url, status=0, text=str(exc))

    def post(self, url: str, payload: dict, timeout: float = 10.0) -> HttpResponse:
        """POST JSON payload to `url` and return an HttpResponse.

        Errors are returned as HttpResponse objects with `status==0` for network errors
        or the HTTP status code for server responses.
        """
        data = json.dumps(payload).encode("utf-8")
        headers = {"User-Agent": self._user_agent, "Content-Type": "application/json"}
        req = Request(url, data=data, headers=headers)
        try:
            with urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                status = getattr(response, "status", None) or getattr(response, "getcode", lambda: 0)()
                return HttpResponse(url=url, status=int(status), text=body)
        except HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = str(exc)
            return HttpResponse(url=url, status=getattr(exc, "code", 0), text=body)
        except URLError as exc:
            return HttpResponse(url=url, status=0, text=str(exc))
