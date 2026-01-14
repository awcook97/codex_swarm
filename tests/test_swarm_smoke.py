from __future__ import annotations

import asyncio
from pathlib import Path

from swarm.config import SwarmConfig
from swarm.coordinator import Coordinator


def test_swarm_smoke(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = SwarmConfig.from_repo_root(repo_root)
    config.db_path = tmp_path / "swarm.db"
    config.artifacts_dir = tmp_path / "artifacts"
    config.filesystem_allowlist = [repo_root, config.artifacts_dir]

    coordinator = Coordinator(config=config)
    result = asyncio.run(
        coordinator.run(
            objective="Summarize the swarm system",
            run_id="smoke",
            max_steps=3,
            dry_run=True,
            verbose=False,
        )
    )

    assert result["final"]
    assert len(result["events"]) > 0
