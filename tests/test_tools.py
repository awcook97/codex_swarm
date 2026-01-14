from __future__ import annotations

import pytest
from pathlib import Path

from swarm.tools.filesystem import FilesystemTool
from swarm.tools.shell import ShellTool


def test_filesystem_tool_allowed_and_forbidden(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    file_path = allowed / "hello.txt"

    fs = FilesystemTool([allowed])
    fs.write_text(file_path, "hi")
    assert fs.read_text(file_path) == "hi"

    other = tmp_path / "other"
    other.mkdir()
    fs2 = FilesystemTool([allowed])
    with pytest.raises(PermissionError):
        fs2.read_text(other / "x.txt")
    with pytest.raises(PermissionError):
        fs2.write_text(other / "y.txt", "no")


def test_shell_tool_allowlist() -> None:
    shell = ShellTool(["echo"])
    res = shell.run("echo hello")
    assert "hello" in res.stdout
    assert res.return_code == 0

    sh = ShellTool(["true"])  # allow a harmless command
    with pytest.raises(PermissionError):
        sh.run("ls")
