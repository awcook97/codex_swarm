from __future__ import annotations

from typing import Any

from swarm.agents.base import AgentContext, BaseAgent


class ResearcherAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="researcher",
            role="Researcher",
            instructions="Gather context relevant to the objective.",
        )

    async def run(self, task: str, context: AgentContext) -> dict[str, Any]:
        self.log(context, f"Starting research task: {task}")
        if context.config.enable_http and not context.dry_run:
            try:
                response = context.http.get("https://example.com")
                result = response.text[:500]
            except Exception as exc:  # pragma: no cover - network path
                result = f"HTTP research failed: {exc}"
        else:
            result = (
                "Research stub: No HTTP calls made. Provide general guidance and assumptions "
                "based on the objective."
            )
        context.short_term.put(context.run_id, self.name, "research", result)
        return {"summary": result}
