from __future__ import annotations

from typing import Any

from swarm.agents.base import AgentContext, BaseAgent


class CriticAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="critic",
            role="Critic",
            instructions="Review outputs for clarity and completeness.",
        )

    async def run(self, task: str, context: AgentContext) -> dict[str, Any]:
        self.log(context, f"Reviewing output: {task}")
        approved = True
        notes = "Looks good."
        if len(task.strip()) < 10:
            approved = False
            notes = "Output is too short; expand with more detail."
        return {"approved": approved, "notes": notes}
