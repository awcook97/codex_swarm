from __future__ import annotations

from pathlib import Path


class FilesystemTool:
    def __init__(self, allowlist: list[Path]) -> None:
        self._allowlist = [path.resolve() for path in allowlist]

    def _is_allowed(self, path: Path) -> bool:
        resolved = path.resolve()
        return any(resolved == root or root in resolved.parents for root in self._allowlist)

    def read_text(self, path: Path) -> str:
        if not self._is_allowed(path):
            raise PermissionError(f"Path not allowed: {path}")
        return path.read_text(encoding="utf-8")

    def write_text(self, path: Path, content: str) -> None:
        if not self._is_allowed(path):
            raise PermissionError(f"Path not allowed: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
