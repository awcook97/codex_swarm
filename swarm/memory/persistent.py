from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable


class PersistentMemory:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path)
        self._initialize()

    def _initialize(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                objective TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                agent TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def put_run(self, run_id: str, objective: str, created_at: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, objective, created_at) VALUES (?, ?, ?)",
            (run_id, objective, created_at),
        )
        self._conn.commit()

    def put_message(self, run_id: str, agent: str, role: str, content: str, created_at: str) -> None:
        self._conn.execute(
            "INSERT INTO messages (run_id, agent, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (run_id, agent, role, content, created_at),
        )
        self._conn.commit()

    def put_artifact(self, run_id: str, name: str, path: str, created_at: str) -> None:
        self._conn.execute(
            "INSERT INTO artifacts (run_id, name, path, created_at) VALUES (?, ?, ?, ?)",
            (run_id, name, path, created_at),
        )
        self._conn.commit()

    def list_messages(self, run_id: str) -> Iterable[tuple[str, str, str]]:
        rows = self._conn.execute(
            "SELECT agent, role, content FROM messages WHERE run_id = ? ORDER BY id",
            (run_id,),
        )
        return list(rows)

    def list_artifacts(self, run_id: str) -> Iterable[tuple[str, str]]:
        rows = self._conn.execute(
            "SELECT name, path FROM artifacts WHERE run_id = ? ORDER BY id",
            (run_id,),
        )
        return list(rows)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT run_id, objective, created_at FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return {"run_id": row[0], "objective": row[1], "created_at": row[2]}

    def close(self) -> None:
        self._conn.close()
