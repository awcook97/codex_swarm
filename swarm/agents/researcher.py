from __future__ import annotations

import json
import re
import urllib.parse
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

        http_notes = ""
        references: list[str] = []
        if context.config.enable_http and not context.dry_run:
            try:
                summary_text, refs = _fetch_wikipedia_summary(context.http, context.objective)
                references.extend(refs)
                if summary_text:
                    http_notes = f"\n\nHTTP notes:\n{summary_text}"
            except Exception as exc:  # pragma: no cover - network path
                http_notes = f"\n\nHTTP research failed: {exc}"

        if summary is None:
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
        if http_notes:
            summary = f"{summary}{http_notes}"

        context.short_term.put(context.run_id, self.name, "research", summary)
        if deliverable:
            context.short_term.put(context.run_id, self.name, "deliverable", deliverable)
        if needs:
            context.short_term.put(context.run_id, self.name, "needs", needs)
        if references:
            context.short_term.put(context.run_id, self.name, "references", references)
        research_path = context.output_dir / "research.md"
        handoff_path = context.output_dir / "handoff.json"
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
                        "References:",
                        *references,
                        "",
                    ]
                ),
            )
            context.filesystem.write_text(
                handoff_path,
                json.dumps(
                    {
                        "summary": summary,
                        "deliverable": deliverable,
                        "needs": needs,
                        "references": references,
                    },
                    indent=2,
                ),
            )
        return {
            "summary": summary,
            "deliverable": deliverable,
            "needs": needs,
            "files": [str(research_path), str(handoff_path)],
        }


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    if not lowered:
        return ""
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)
    return cleaned.strip("-")[:64]


def _fetch_wikipedia_summary(http: Any, objective: str) -> tuple[str, list[str]]:
    query = objective.strip()
    if not query:
        return "", []
    search_url = (
        "https://en.wikipedia.org/w/api.php?action=opensearch&search="
        + _url_escape(query)
        + "&limit=1&namespace=0&format=json"
    )
    response = http.get(search_url, timeout=6.0)
    try:
        payload = json.loads(response.text)
    except json.JSONDecodeError:
        return "", [response.url]
    if len(payload) < 2 or not payload[1]:
        return "", [response.url]
    title = str(payload[1][0]).replace(" ", "_")
    summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    summary_response = http.get(summary_url, timeout=6.0)
    try:
        summary_payload = json.loads(summary_response.text)
        extract = summary_payload.get("extract") or ""
    except json.JSONDecodeError:
        extract = summary_response.text[:500]
    return extract[:500], [response.url, summary_response.url]


def _url_escape(value: str) -> str:
    return urllib.parse.quote(value.strip())
