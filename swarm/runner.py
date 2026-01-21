from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from swarm.config import SwarmConfig
from swarm.coordinator import Coordinator


@dataclass(slots=True)
class RunSpec:
    objective: str
    run_id: str | None = None
    output_dir: str | Path | None = None
    max_steps: int | None = None
    dry_run: bool = False
    verbose: bool = False
    config: SwarmConfig | None = None


@dataclass(slots=True)
class RunResult:
    run_id: str
    objective: str
    final: str
    output_dir: str
    events: list[dict[str, object]]


class SwarmRunner:
    def __init__(self, config: SwarmConfig, concurrency: int = 4) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be >= 1")
        self._config = config
        self._concurrency = concurrency
        self._task_group: asyncio.TaskGroup | None = None
        self._results: list[RunResult] = []
        self._results_lock: asyncio.Lock | None = None
        self._semaphore: asyncio.Semaphore | None = None

    def spawn(self, spec: RunSpec) -> "asyncio.Task[RunResult]":
        if self._task_group is None or self._semaphore is None:
            raise RuntimeError("spawn() called outside of SwarmRunner.run()")
        return self._task_group.create_task(self._run_spec(spec))

    async def run(self, specs: Iterable[RunSpec]) -> list[RunResult]:
        self._results = []
        self._results_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(self._concurrency)
        async with asyncio.TaskGroup() as task_group:
            self._task_group = task_group
            for spec in specs:
                task_group.create_task(self._run_spec(spec))
        self._task_group = None
        return list(self._results)

    async def _run_spec(self, spec: RunSpec) -> RunResult:
        if self._semaphore is None or self._results_lock is None:
            raise RuntimeError("SwarmRunner not initialized; call run() first")
        async with self._semaphore:
            coordinator = Coordinator(
                config=spec.config or self._config,
                spawner=self.spawn,
            )
            result = await coordinator.run(
                objective=spec.objective,
                run_id=spec.run_id,
                output_dir=spec.output_dir,
                max_steps=spec.max_steps,
                dry_run=spec.dry_run,
                verbose=spec.verbose,
            )
            run_result = RunResult(
                run_id=result["run_id"],
                objective=result["objective"],
                final=result["final"],
                output_dir=result["output_dir"],
                events=result["events"],
            )
            async with self._results_lock:
                self._results.append(run_result)
            return run_result
