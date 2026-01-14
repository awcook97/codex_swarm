from __future__ import annotations

import os
import subprocess
from pathlib import Path

from swarm.tools.git import GitTool


def test_git_tool_init_and_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    gt = GitTool(repo_root=repo)
    gt.init()

    # configure user for commits
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo)

    # create a file and commit via GitTool
    f = repo / "a.txt"
    f.write_text("hello")
    gt.add("a.txt")
    res = gt.commit("add a.txt")
    assert res.return_code == 0

    branch = gt.current_branch()
    assert branch is not None

    # create new branch
    gt.create_branch("feature/x")
    assert gt.current_branch() == "feature/x"
