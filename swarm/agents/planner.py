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
                "Return JSON with fields: plan, deliverable, project_type, artifacts.",
                "plan must include steps with (id, agent, task, depends_on).",
                f"Objective: {task}",
            ]
        )
        response = await self.complete(context, prompt)
        try:
            payload = json.loads(response)
        except json.JSONDecodeError:
            payload = {}
        plan = payload.get("plan") if isinstance(payload, dict) else None
        if not isinstance(plan, dict) or "steps" not in plan:
            plan = {
                "steps": [
                    {"id": 1, "agent": "researcher", "task": "Gather context.", "depends_on": []},
                    {"id": 2, "agent": "coder", "task": "Draft a response.", "depends_on": [1]},
                    {"id": 3, "agent": "critic", "task": "Review the draft.", "depends_on": [2]},
                ]
            }
        deliverable = payload.get("deliverable") if isinstance(payload, dict) else None
        project_type = payload.get("project_type") if isinstance(payload, dict) else None
        artifacts = payload.get("artifacts") if isinstance(payload, dict) else None
        if not isinstance(artifacts, list):
            artifacts = []

        plan_payload = {
            "plan": plan,
            "deliverable": deliverable,
            "project_type": project_type,
            "artifacts": artifacts,
        }
        context.short_term.put(context.run_id, self.name, "plan", plan_payload)
        if deliverable:
            context.short_term.put(context.run_id, self.name, "deliverable", deliverable)
        if project_type:
            context.short_term.put(context.run_id, self.name, "project_type", project_type)
        if artifacts:
            context.short_term.put(context.run_id, self.name, "artifacts", artifacts)
        plan_path = context.output_dir / "plan.json"
        if not context.dry_run:
            context.filesystem.write_text(plan_path, json.dumps(plan_payload, indent=2))
        return {"plan": plan_payload, "files": [str(plan_path)]}
