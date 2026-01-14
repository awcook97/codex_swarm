from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass


@dataclass(slots=True)
class ShellResult:
    stdout: str
    stderr: str
    return_code: int


class ShellTool:
    def __init__(self, allowlist: list[str]) -> None:
        self._allowlist = set(allowlist)

    def run(self, command: str) -> ShellResult:
        parts = shlex.split(command)
        if not parts:
            raise ValueError("Command is empty")
        if parts[0] not in self._allowlist:
            raise PermissionError(f"Command not allowed: {parts[0]}")
        completed = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            check=False,
        )
        return ShellResult(
            stdout=completed.stdout,
            stderr=completed.stderr,
            return_code=completed.returncode,
        )
