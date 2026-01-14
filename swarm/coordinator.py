from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from swarm.agents import (
    AgentContext,
    BaseAgent,
    CoderAgent,
    CriticAgent,
    PlannerAgent,
    ResearcherAgent,
)
from swarm.agents.instructions import load_agent_instructions
from swarm.bus import EventLog
from swarm.config import SwarmConfig
from swarm.llm import LLM, MockLLM
from swarm.memory import PersistentMemory, ShortTermMemory
from swarm.tools import FilesystemTool, HttpTool, ShellTool


@dataclass(slots=True)
class StepResult:
    step_id: int
    agent: str
    task: str
    output: dict[str, Any]
    critic: dict[str, Any] | None = None


class Coordinator:
    def __init__(self, config: SwarmConfig, llm: LLM | None = None) -> None:
        self.config = config
        self.event_log = EventLog()
        self.short_term = ShortTermMemory()
        self.persistent = PersistentMemory(config.db_path)
        self.filesystem = FilesystemTool(list(config.filesystem_allowlist))
        self.shell = ShellTool(list(config.shell_allowlist))
        self.http = HttpTool()
        self.llm = llm or MockLLM(seed=config.seed)
        self.agents: dict[str, BaseAgent] = {
            "researcher": ResearcherAgent(
                instructions=load_agent_instructions(self.config.repo_root, "researcher")
            ),
            "planner": PlannerAgent(
                instructions=load_agent_instructions(self.config.repo_root, "planner")
            ),
            "coder": CoderAgent(
                instructions=load_agent_instructions(self.config.repo_root, "coder")
            ),
            "critic": CriticAgent(
                instructions=load_agent_instructions(self.config.repo_root, "critic")
            ),
        }

    def _context(
        self, run_id: str, objective: str, output_dir: Path, dry_run: bool, verbose: bool
    ) -> AgentContext:
        return AgentContext(
            run_id=run_id,
            objective=objective,
            config=self.config,
            output_dir=output_dir,
            event_log=self.event_log,
            short_term=self.short_term,
            persistent=self.persistent,
            filesystem=self.filesystem,
            shell=self.shell,
            http=self.http,
            llm=self.llm,
            dry_run=dry_run,
            verbose=verbose,
        )

    async def run(
        self,
        objective: str,
        run_id: str | None = None,
        output_dir: str | Path | None = None,
        max_steps: int | None = None,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> dict[str, Any]:
        run_id = run_id or uuid.uuid4().hex
        resolved_output = self._resolve_output_dir(objective, run_id, output_dir)
        created_at = datetime.now(timezone.utc).isoformat()
        self.persistent.put_run(run_id, objective, created_at)
        self.event_log.log("run_started", {"run_id": run_id, "objective": objective})

        context = self._context(run_id, objective, resolved_output, dry_run, verbose)
        planner = self.agents["planner"]
        plan_output = await planner.run(objective, context)
        plan = plan_output.get("plan", {})
        self.event_log.log("plan_created", {"run_id": run_id, "plan": plan})
        self.persistent.put_message(run_id, planner.name, planner.role, json.dumps(plan), created_at)

        steps = plan.get("steps", [])
        limit = max_steps or self.config.max_steps
        steps = steps[:limit]
        pending = {step["id"]: step for step in steps}
        completed: dict[int, StepResult] = {}

        while pending:
            ready = [
                step
                for step in pending.values()
                if all(dep in completed for dep in step.get("depends_on", []))
            ]
            if not ready:
                break
            tasks = [self._run_step(step, context) for step in ready]
            results = await asyncio.gather(*tasks)
            for result in results:
                completed[result.step_id] = result
                pending.pop(result.step_id, None)

        final_text = self._compose_final_output(completed)
        self.event_log.log("run_completed", {"run_id": run_id, "final": final_text})
        return {
            "run_id": run_id,
            "objective": objective,
            "final": final_text,
            "output_dir": str(resolved_output),
            "events": self.event_log.list_events(),
        }

    def _resolve_output_dir(
        self, objective: str, run_id: str, output_dir: str | Path | None
    ) -> Path:
        if output_dir is None:
            slug = _slugify(objective) or run_id
            return self.config.output_root / slug
        candidate = Path(output_dir)
        if not candidate.is_absolute():
            candidate = self.config.repo_root / candidate
        if self.config.repo_root not in candidate.resolve().parents and candidate.resolve() != self.config.repo_root:
            raise ValueError("output_dir must be inside the repo_root")
        return candidate


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    if not lowered:
        return ""
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)
    return cleaned.strip("-")[:64]

    async def _run_step(self, step: dict[str, Any], context: AgentContext) -> StepResult:
        agent_name = step.get("agent", "")
        task = step.get("task", "")
        agent = self.agents.get(agent_name)
        if agent is None:
            raise ValueError(f"Unknown agent: {agent_name}")
        self.event_log.log("step_started", {"step_id": step.get("id"), "agent": agent_name})
        output = await agent.run(task, context)
        created_at = datetime.now(timezone.utc).isoformat()
        self.persistent.put_message(context.run_id, agent.name, agent.role, json.dumps(output), created_at)
        self.event_log.log("step_completed", {"step_id": step.get("id"), "agent": agent_name})

        critic_result = None
        if agent_name != "critic":
            critic = self.agents["critic"]
            critic_result = await critic.run(json.dumps(output), context)
            self.event_log.log(
                "critic_review",
                {"step_id": step.get("id"), "approved": critic_result.get("approved")},
            )
        return StepResult(step_id=step.get("id", 0), agent=agent_name, task=task, output=output, critic=critic_result)

    def _compose_final_output(self, results: dict[int, StepResult]) -> str:
        ordered = [results[key] for key in sorted(results.keys())]
        sections: list[str] = []
        for item in ordered:
            if item.agent == "coder" and "content" in item.output:
                sections.append(str(item.output["content"]))
            else:
                sections.append(f"{item.agent}: {item.output}")
            if item.critic and not item.critic.get("approved", True):
                sections.append(f"Critic note: {item.critic.get('notes')}")
        return "\n".join(sections).strip()
