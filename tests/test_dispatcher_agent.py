from __future__ import annotations

import asyncio
from pathlib import Path

from swarm.config import SwarmConfig
from swarm.agents.dispatcher import DispatcherAgent
from swarm.memory.persistent import PersistentMemory
from swarm.memory.short_term import ShortTermMemory
from swarm.bus.event_log import EventLog
from swarm.tools.filesystem import FilesystemTool
from swarm.tools.shell import ShellTool
from swarm.tools.http import HttpTool
from swarm.agents.base import AgentContext


def test_dispatcher_writes_artifacts(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = SwarmConfig.from_repo_root(repo_root)
    config.db_path = tmp_path / "swarm.db"
    config.artifacts_dir = tmp_path / "artifacts"
    config.output_root = tmp_path / "output"
    config.filesystem_allowlist = [repo_root, config.artifacts_dir, config.output_root]

    # create a handoff.json in the output dir
    out_dir = config.output_root / "test-run"
    out_dir.mkdir(parents=True, exist_ok=True)
    handoff = out_dir / "handoff.json"
    handoff.write_text('{"summary":"ok"}', encoding="utf-8")

    event_log = EventLog()
    short_term = ShortTermMemory()
    persistent = PersistentMemory(config.db_path)
    filesystem = FilesystemTool([config.artifacts_dir, config.output_root, repo_root])
    shell = ShellTool(list(config.shell_allowlist))
    http = HttpTool()

    context = AgentContext(
        run_id="test-run",
        objective="obj",
        config=config,
        output_dir=out_dir,
        event_log=event_log,
        short_term=short_term,
        persistent=persistent,
        filesystem=filesystem,
        shell=shell,
        http=http,
        llm=None,  # type: ignore[arg-type]
        dry_run=True,
        verbose=False,
    )

    agent = DispatcherAgent()
    result = asyncio.run(agent.run("dispatch", context))
    assert result.get("dispatched") is True
    # artifacts should exist
    for i in range(1, 4):
        p = config.artifacts_dir / "test-run" / f"subagent-{i}.json"
        assert p.exists()

    persistent.close()
