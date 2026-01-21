from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from projects.feature_factory.api.store import BatchStore, StorePaths
from projects.feature_factory.pipeline.runner import BatchSpec, normalize_batch, run_batch


@dataclass(slots=True)
class ApiConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    concurrency: int = 4


class FeatureFactoryHandler(BaseHTTPRequestHandler):
    server_version = "FeatureFactory/0.1"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        return json.loads(raw.decode("utf-8"))

    def _store(self) -> BatchStore:
        return self.server.store  # type: ignore[attr-defined]

    def _repo_root(self) -> Path:
        return self.server.repo_root  # type: ignore[attr-defined]

    def _config(self) -> ApiConfig:
        return self.server.config  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/" or self.path == "/index.html":
            self._send_file(self.server.web_root / "index.html", "text/html; charset=utf-8")  # type: ignore[attr-defined]
            return
        if self.path == "/app.js":
            self._send_file(self.server.web_root / "app.js", "text/javascript; charset=utf-8")  # type: ignore[attr-defined]
            return
        if self.path == "/styles.css":
            self._send_file(self.server.web_root / "styles.css", "text/css; charset=utf-8")  # type: ignore[attr-defined]
            return
        if self.path == "/batches":
            self._send_json(HTTPStatus.OK, {"batches": self._store().list_batches()})
            return
        if self.path.startswith("/batches/"):
            batch_id = self.path.split("/", 2)[2]
            batch = self._store().get_batch(batch_id)
            if not batch:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "batch not found"})
                return
            self._send_json(HTTPStatus.OK, batch)
            return
        if self.path.startswith("/features/"):
            feature_id = self.path.split("/", 2)[2]
            feature = self._store().get_feature(feature_id)
            if not feature:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "feature not found"})
                return
            self._send_json(HTTPStatus.OK, feature)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/batches":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            payload = self._read_json()
            batch_spec = normalize_batch(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        now = datetime.now(timezone.utc).isoformat()
        batch = _batch_from_spec(batch_spec, now)
        try:
            self._store().create_batch(batch)
        except ValueError as exc:
            self._send_json(HTTPStatus.CONFLICT, {"error": str(exc)})
            return

        thread = threading.Thread(
            target=_run_and_update,
            args=(self._store(), self._repo_root(), batch_spec, self._config()),
            daemon=True,
        )
        thread.start()
        self._send_json(HTTPStatus.ACCEPTED, batch)


def _batch_from_spec(spec: BatchSpec, created_at: str) -> dict[str, Any]:
    return {
        "batch_id": spec.batch_id,
        "created_at": created_at,
        "status": "queued",
        "features": [
            {
                "feature_id": feature.feature_id,
                "objective": feature.objective,
                "status": "queued",
                "run_id": None,
                "output_dir": None,
                "final": None,
                "artifacts": [],
            }
            for feature in spec.features
        ],
    }


def _run_and_update(store: BatchStore, repo_root: Path, spec: BatchSpec, config: ApiConfig) -> None:
    store.update_batch(spec.batch_id, {"status": "running"})
    try:
        results = run_batch(spec, repo_root, concurrency=config.concurrency)
        features = []
        for result in results:
            features.append(
                {
                    "feature_id": result.run_id,
                    "objective": result.objective,
                    "status": "completed",
                    "run_id": result.run_id,
                    "output_dir": result.output_dir,
                    "final": result.final,
                    "artifacts": [],
                }
            )
        store.update_batch(
            spec.batch_id,
            {"status": "completed", "features": features, "results": [asdict(r) for r in results]},
        )
    except Exception as exc:
        store.update_batch(spec.batch_id, {"status": "failed", "error": str(exc)})


def start(config: ApiConfig | None = None) -> None:
    config = config or ApiConfig()
    repo_root = Path(__file__).resolve().parents[3]
    data_root = repo_root / "projects" / "feature_factory" / "data"
    web_root = repo_root / "projects" / "feature_factory" / "web"
    store = BatchStore(StorePaths(root=data_root))

    server = HTTPServer((config.host, config.port), FeatureFactoryHandler)
    server.store = store  # type: ignore[attr-defined]
    server.repo_root = repo_root  # type: ignore[attr-defined]
    server.web_root = web_root  # type: ignore[attr-defined]
    server.config = config  # type: ignore[attr-defined]
    print(f"Feature Factory API listening on http://{config.host}:{config.port}")
    server.serve_forever()


if __name__ == "__main__":
    start()
