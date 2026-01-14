from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(slots=True)
class GitResult:
    stdout: str
    stderr: str
    return_code: int


class GitTool:
    """Lightweight git helper restricted to a repository root.

    Designed for automation by agents in this repo. Commands are executed
    with `cwd` set to the provided `repo_root`. By default remote-affecting
    commands (push/fetch) are disabled unless `allow_remote=True`.
    """

    def __init__(self, repo_root: Path, allow_remote: bool = False) -> None:
        self.repo_root = repo_root.resolve()
        self.allow_remote = allow_remote

    def _run(self, args: Iterable[str], check: bool = False) -> GitResult:
        parts = ["git"] + list(args)
        completed = subprocess.run(
            parts,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if check and completed.returncode != 0:
            raise subprocess.CalledProcessError(
                completed.returncode, parts, output=completed.stdout, stderr=completed.stderr
            )
        return GitResult(stdout=completed.stdout, stderr=completed.stderr, return_code=completed.returncode)

    def init(self) -> GitResult:
        return self._run(["init"], check=True)

    def status(self) -> GitResult:
        return self._run(["status", "--porcelain"])

    def current_branch(self) -> Optional[str]:
        res = self._run(["rev-parse", "--abbrev-ref", "HEAD"])
        if res.return_code != 0:
            return None
        return res.stdout.strip()

    def create_branch(self, name: str) -> GitResult:
        return self._run(["checkout", "-b", name], check=True)

    def checkout(self, name: str) -> GitResult:
        return self._run(["checkout", name], check=True)

    def add(self, pathspec: str = "--all") -> GitResult:
        return self._run(["add", pathspec], check=True)

    def commit(self, message: str) -> GitResult:
        return self._run(["commit", "-m", message], check=True)

    def apply_patch(self, patch_text: str) -> GitResult:
        proc = subprocess.run(
            ["git", "apply", "-"],
            cwd=str(self.repo_root),
            input=patch_text,
            capture_output=True,
            text=True,
            check=False,
        )
        return GitResult(stdout=proc.stdout, stderr=proc.stderr, return_code=proc.returncode)

    def diff(self, cached: bool = False) -> GitResult:
        args = ["diff", "--no-color"]
        if cached:
            args = ["diff", "--staged", "--no-color"]
        return self._run(args)

    def push(self, remote: str = "origin", branch: Optional[str] = None) -> GitResult:
        if not self.allow_remote:
            raise PermissionError("Remote operations are disabled for GitTool")
        args = ["push", remote]
        if branch:
            args.append(branch)
        return self._run(args)
