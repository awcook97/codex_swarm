from __future__ import annotations

import json
from typing import Any

from swarm.agents.base import AgentContext, BaseAgent


class PlannerAgent(BaseAgent):
    def __init__(self, instructions: str | None = None) -> None:
        super().__init__(
            name="planner",
            role="Planner",
            instructions=instructions or "Break objectives into structured steps.",
        )

    async def run(self, task: str, context: AgentContext) -> dict[str, Any]:
        self.log(context, f"Planning for objective: {task}")
        prompt = "\n".join(
            [
                "ROLE: Planner",
                "Return JSON with a plan of steps (id, agent, task, depends_on).",
                f"Objective: {task}",
            ]
        )
        response = await self.complete(context, prompt)
        try:
            plan = json.loads(response)
        except json.JSONDecodeError:
            plan = {
                "steps": [
                    {"id": 1, "agent": "researcher", "task": "Gather context.", "depends_on": []},
                    {"id": 2, "agent": "coder", "task": "Draft a response.", "depends_on": [1]},
                    {"id": 3, "agent": "critic", "task": "Review the draft.", "depends_on": [2]},
                ]
            }
        context.short_term.put(context.run_id, self.name, "plan", plan)
        plan_path = context.output_dir / "plan.json"
        if not context.dry_run:
            context.filesystem.write_text(plan_path, json.dumps(plan, indent=2))
        return {"plan": plan, "files": [str(plan_path)]}
