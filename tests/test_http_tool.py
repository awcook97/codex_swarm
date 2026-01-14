from __future__ import annotations

import io
from types import SimpleNamespace

from swarm.tools.http import HttpTool, HttpResponse


class DummyResp:
    def __init__(self, data: bytes, status: int = 200):
        self._data = io.BytesIO(data)
        self.status = status

    def read(self):
        return self._data.read()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_http_get_success(monkeypatch):
    tool = HttpTool()

    def fake_urlopen(req, timeout=None):
        return DummyResp(b"ok", status=200)

    monkeypatch.setattr("swarm.tools.http.urlopen", fake_urlopen)
    res = tool.get("http://example")
    assert isinstance(res, HttpResponse)
    assert res.status == 200
    assert res.text == "ok"


def test_http_get_404(monkeypatch):
    tool = HttpTool()

    class FakeHTTPError(Exception):
        pass

    def fake_urlopen(req, timeout=None):
        raise FakeHTTPError("Not Found")

    # Simulate URLError path
    monkeypatch.setattr("swarm.tools.http.urlopen", fake_urlopen)
    res = tool.get("http://example")
    assert isinstance(res, HttpResponse)
    assert res.status == 0
    assert "Not Found" in res.text
