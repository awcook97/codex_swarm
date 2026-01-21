from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass(slots=True)
class StorePaths:
    root: Path

    @property
    def data_file(self) -> Path:
        return self.root / "store.json"


class BatchStore:
    def __init__(self, paths: StorePaths) -> None:
        self._paths = paths
        self._lock = Lock()
        self._paths.root.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self._paths.data_file.exists():
            return {"batches": {}, "features": {}}
        return json.loads(self._paths.data_file.read_text(encoding="utf-8"))

    def save(self, data: dict[str, Any]) -> None:
        self._paths.data_file.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )

    def create_batch(self, batch: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self.load()
            batch_id = batch["batch_id"]
            if batch_id in data["batches"]:
                raise ValueError(f"Batch {batch_id} already exists")
            data["batches"][batch_id] = batch
            for feature in batch.get("features", []):
                data["features"][feature["feature_id"]] = feature
            self.save(data)
            return batch

    def update_batch(self, batch_id: str, update: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self.load()
            batch = data["batches"].get(batch_id)
            if not batch:
                raise KeyError(batch_id)
            batch.update(update)
            for feature in batch.get("features", []):
                data["features"][feature["feature_id"]] = feature
            self.save(data)
            return batch

    def list_batches(self) -> list[dict[str, Any]]:
        data = self.load()
        return list(data["batches"].values())

    def get_batch(self, batch_id: str) -> dict[str, Any] | None:
        data = self.load()
        return data["batches"].get(batch_id)

    def get_feature(self, feature_id: str) -> dict[str, Any] | None:
        data = self.load()
        return data["features"].get(feature_id)
