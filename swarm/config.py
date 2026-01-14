from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


@dataclass(slots=True)
class SwarmConfig:
    repo_root: Path
    artifacts_dir: Path
    output_root: Path
    db_path: Path
    seed: int = 42
    max_steps: int = 10
    enable_http: bool = False
    shell_allowlist: Sequence[str] = field(default_factory=lambda: ["ls", "rg", "cat"])
    filesystem_allowlist: Sequence[Path] = field(default_factory=list)

    @classmethod
    def from_repo_root(cls, repo_root: Path) -> "SwarmConfig":
        artifacts_dir = repo_root / "artifacts"
        output_root = repo_root / "output"
        db_path = repo_root / "swarm.db"
        return cls(
            repo_root=repo_root,
            artifacts_dir=artifacts_dir,
            output_root=output_root,
            db_path=db_path,
            filesystem_allowlist=[repo_root, artifacts_dir, output_root],
        )
