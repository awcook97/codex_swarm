from __future__ import annotations

import asyncio
from pathlib import Path

from swarm.config import SwarmConfig
from swarm.runner import RunResult, RunSpec, SwarmRunner


def _config_for(tmp_path: Path) -> SwarmConfig:
    repo_root = Path(__file__).resolve().parents[1]
    config = SwarmConfig.from_repo_root(repo_root)
    config.db_path = tmp_path / "swarm.db"
    config.artifacts_dir = tmp_path / "artifacts"
    config.output_root = tmp_path / "output"
    config.filesystem_allowlist = [repo_root, config.artifacts_dir, config.output_root]
    return config


def test_swarm_runner_runs_multiple(tmp_path: Path) -> None:
    config = _config_for(tmp_path)
    runner = SwarmRunner(config=config, concurrency=2)
    specs = [
        RunSpec(objective="alpha", dry_run=True),
        RunSpec(objective="beta", dry_run=True),
    ]

    results = asyncio.run(runner.run(specs))

    assert len(results) == 2
    assert {result.objective for result in results} == {"alpha", "beta"}


def test_swarm_runner_can_spawn_additional_runs(tmp_path: Path) -> None:
    config = _config_for(tmp_path)
    runner = SwarmRunner(config=config, concurrency=2)

    async def run_with_spawn() -> list[RunResult]:
        results_holder: dict[str, list[RunResult]] = {}
        started = asyncio.Event()

        async def trigger_spawn() -> None:
            await started.wait()
            runner.spawn(RunSpec(objective="child", dry_run=True))

        async def run_root() -> None:
            started.set()
            results_holder["results"] = await runner.run(
                [RunSpec(objective="parent", dry_run=True)]
            )

        async with asyncio.TaskGroup() as group:
            group.create_task(trigger_spawn())
            group.create_task(run_root())

        return results_holder["results"]

    results = asyncio.run(run_with_spawn())
    objectives = {result.objective for result in results}
    assert objectives == {"parent", "child"}
