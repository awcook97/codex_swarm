from __future__ import annotations

import json
from typing import Any

from swarm.agents.base import AgentContext, BaseAgent


class PlannerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="planner",
            role="Planner",
            instructions="Break objectives into structured steps.",
        )

    async def run(self, task: str, context: AgentContext) -> dict[str, Any]:
        self.log(context, f"Planning for objective: {task}")
        response = await context.llm.complete(task)
        try:
            plan = json.loads(response.content)
        except json.JSONDecodeError:
            plan = {
                "steps": [
                    {"id": 1, "agent": "researcher", "task": "Gather context.", "depends_on": []},
                    {"id": 2, "agent": "coder", "task": "Draft a response.", "depends_on": [1]},
                    {"id": 3, "agent": "critic", "task": "Review the draft.", "depends_on": [2]},
                ]
            }
        context.short_term.put(context.run_id, self.name, "plan", plan)
        return {"plan": plan}
