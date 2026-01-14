from __future__ import annotations

import json
from typing import Any

from swarm.agents.base import AgentContext, BaseAgent


class CriticAgent(BaseAgent):
    def __init__(self, instructions: str | None = None) -> None:
        super().__init__(
            name="critic",
            role="Critic",
            instructions=instructions or "Review outputs for clarity and completeness.",
        )

    async def run(self, task: str, context: AgentContext) -> dict[str, Any]:
        self.log(context, f"Reviewing output: {task}")
        approved = True
        notes = "Looks good."
        step_id = "unknown"
        try:
            payload = json.loads(task)
            step_id = payload.get("step_id", "unknown")
            output = payload.get("output", {})
        except json.JSONDecodeError:
            output = {}

        files = output.get("files", [])
        deliverable = output.get("deliverable")
        prompt = "\n".join(
            [
                "ROLE: Critic",
                "Return JSON with fields: approved, notes.",
                f"Objective: {context.objective}",
                f"Files: {files}",
                f"Output summary: {output.get('content', '')}",
            ]
        )
        response_text = await self.complete(context, prompt)
        try:
            review = json.loads(response_text)
            approved = bool(review.get("approved", approved))
            notes = review.get("notes", notes)
        except json.JSONDecodeError:
            pass

        lower_files = [name.lower() for name in files]
        has_gif = any(name.endswith(".gif") for name in lower_files)
        has_video = any(name.endswith(".mp4") or name.endswith(".webm") for name in lower_files)
        has_html = any(name.endswith(".html") for name in lower_files)
        has_python = any(name.endswith(".py") for name in lower_files)
        if not files:
            approved = False
            notes = "No files were produced; generate a project with concrete outputs."
        elif not (has_gif or has_video or has_html or has_python):
            approved = False
            notes = "Missing primary deliverable; include a GIF/video or HTML entrypoint."
        elif deliverable == "python" and not has_python:
            approved = False
            notes = "Missing .py deliverable; include a runnable Python file."
        elif not (has_gif or has_video or has_python) and "index.html" not in lower_files:
            approved = False
            notes = "Missing index.html; include a primary entrypoint."
        else:
            required = _read_artifact_requirements(context)
            missing = [name for name in required if name.lower() not in lower_files]
            if missing:
                approved = False
                notes = f"Missing required files: {', '.join(missing)}"

        review_path = context.output_dir / f"critic_step_{step_id}.md"
        if not context.dry_run:
            context.filesystem.write_text(
                review_path,
                "\n".join(
                    [
                        "# Critic Review",
                        "",
                        f"Step: {step_id}",
                        f"Approved: {approved}",
                        "",
                        "Notes:",
                        notes,
                        "",
                    ]
                ),
            )
        return {"approved": approved, "notes": notes, "files": [str(review_path)]}


def _read_artifact_requirements(context: AgentContext) -> list[str]:
    plan_path = context.output_dir / "plan.json"
    try:
        payload = json.loads(context.filesystem.read_text(plan_path))
    except Exception:
        return []
    artifacts = payload.get("artifacts")
    if isinstance(artifacts, list):
        return [str(item) for item in artifacts]
    return []
