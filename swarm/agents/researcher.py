from __future__ import annotations

import json
from typing import Any

from swarm.agents.base import AgentContext, BaseAgent


class ResearcherAgent(BaseAgent):
    def __init__(self, instructions: str | None = None) -> None:
        super().__init__(
            name="researcher",
            role="Researcher",
            instructions=instructions or "Gather context relevant to the objective.",
        )

    async def run(self, task: str, context: AgentContext) -> dict[str, Any]:
        self.log(context, f"Starting research task: {task}")
        prompt = "\n".join(
            [
                "ROLE: Researcher",
                "Return JSON with fields: summary, deliverable, needs.",
                f"Objective: {context.objective}",
                f"Task: {task}",
            ]
        )
        response_text = await self.complete(context, prompt)
        summary = None
        deliverable = None
        needs: list[str] = []
        try:
            payload = json.loads(response_text)
            summary = payload.get("summary")
            deliverable = payload.get("deliverable")
            needs = payload.get("needs") or []
        except json.JSONDecodeError:
            summary = None

        if summary is None:
            if context.config.enable_http and not context.dry_run:
                try:
                    response = context.http.get("https://example.com")
                    summary = response.text[:500]
                except Exception as exc:  # pragma: no cover - network path
                    summary = f"HTTP research failed: {exc}"
            else:
                summary = (
                    "Research stub: No HTTP calls made. Provide general guidance and assumptions "
                    "based on the objective."
                )
            lowered = context.objective.lower()
            if "animation" in lowered or "movie" in lowered:
                summary = (
                    f"{summary}\n\nSuggested deliverable: animated GIF (or short video).\n"
                    "Needs: gif encoder or video render pipeline.\n"
                    "Deliverable: animated gif"
                )
                deliverable = "gif"
                needs = ["gif encoder"]

        context.short_term.put(context.run_id, self.name, "research", summary)
        if deliverable:
            context.short_term.put(context.run_id, self.name, "deliverable", deliverable)
        if needs:
            context.short_term.put(context.run_id, self.name, "needs", needs)
        research_path = context.output_dir / "research.md"
        if not context.dry_run:
            context.filesystem.write_text(
                research_path,
                "\n".join(
                    [
                        "# Research Notes",
                        "",
                        f"Objective: {context.objective}",
                        "",
                        summary,
                        "",
                    ]
                ),
            )
        return {
            "summary": summary,
            "deliverable": deliverable,
            "needs": needs,
            "files": [str(research_path)],
        }
