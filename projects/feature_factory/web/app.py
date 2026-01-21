from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path


def start(host: str = "127.0.0.1", port: int = 8081) -> None:
    """Serve the static dashboard files."""
    web_root = Path(__file__).parent
    handler = partial(SimpleHTTPRequestHandler, directory=str(web_root))
    server = HTTPServer((host, port), handler)
    print(f"Feature Factory web UI on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    start()
