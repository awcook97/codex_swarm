from __future__ import annotations

import asyncio
from pathlib import Path

from swarm.config import SwarmConfig
from swarm.coordinator import Coordinator
from swarm.agents.planner import PlannerAgent
from swarm.agents.base import AgentContext
from swarm.bus.event_log import EventLog
from swarm.memory.short_term import ShortTermMemory
from swarm.memory.persistent import PersistentMemory
from swarm.tools.filesystem import FilesystemTool
from swarm.tools.shell import ShellTool
from swarm.tools.http import HttpTool
from swarm.llm import LLMResponse


class BadLLM:
    async def complete(self, prompt: str) -> LLMResponse:  # type: ignore[misc]
        return LLMResponse(content="not-a-json")


def test_planner_falls_back_on_invalid_json(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = SwarmConfig.from_repo_root(repo_root)
    config.db_path = tmp_path / "swarm.db"
    config.artifacts_dir = tmp_path / "artifacts"
    config.output_root = tmp_path / "output"
    config.filesystem_allowlist = [repo_root, config.artifacts_dir, config.output_root]

    event_log = EventLog()
    short_term = ShortTermMemory()
    persistent = PersistentMemory(config.db_path)
    filesystem = FilesystemTool([config.artifacts_dir, config.output_root])
    shell = ShellTool(list(config.shell_allowlist))
    http = HttpTool()

    context = AgentContext(
        run_id="test",
        objective="obj",
        config=config,
        output_dir=config.output_root,
        event_log=event_log,
        short_term=short_term,
        persistent=persistent,
        filesystem=filesystem,
        shell=shell,
        http=http,
        llm=BadLLM(),
        dry_run=True,
        verbose=False,
    )

    planner = PlannerAgent()
    result = asyncio.run(planner.run("task", context))
    assert "plan" in result
    plan = result["plan"]
    assert isinstance(plan, dict)
    assert "steps" in plan
    assert any(s.get("agent") == "researcher" for s in plan.get("steps", []))

    persistent.close()


def test_coordinator_run_smoke_more_assertions(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = SwarmConfig.from_repo_root(repo_root)
    config.db_path = tmp_path / "swarm.db"
    config.artifacts_dir = tmp_path / "artifacts"
    config.output_root = tmp_path / "output"
    config.filesystem_allowlist = [repo_root, config.artifacts_dir, config.output_root]

    coordinator = Coordinator(config=config)
    result = asyncio.run(
        coordinator.run(
            objective="Summarize the swarm system for tests",
            run_id="smoke2",
            max_steps=3,
            dry_run=True,
            verbose=False,
        )
    )

    assert result["final"]
    assert len(result["events"]) > 0

    run = coordinator.persistent.get_run("smoke2")
    assert run and run["run_id"] == "smoke2"

    messages = list(coordinator.persistent.list_messages("smoke2"))
    assert len(messages) >= 1

    coordinator.persistent.close()
