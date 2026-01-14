from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from swarm.agents.base import AgentContext, BaseAgent


class CoderAgent(BaseAgent):
    def __init__(self, instructions: str | None = None) -> None:
        super().__init__(
            name="coder",
            role="Coder",
            instructions=instructions or "Create artifacts or code changes based on tasks.",
        )

    async def run(self, task: str, context: AgentContext) -> dict[str, Any]:
        self.log(context, f"Coding task: {task}")
        artifact_dir = context.output_dir
        artifact_path = artifact_dir / "result.txt"
        content = (
            f"Objective: {context.objective}\n"
            f"Task: {task}\n"
            "Output: Drafted response artifact.\n"
        )
        if not context.dry_run:
            context.filesystem.write_text(artifact_path, content)
            created_at = datetime.now(timezone.utc).isoformat()
            context.persistent.put_artifact(
                context.run_id,
                name="result.txt",
                path=str(artifact_path),
                created_at=created_at,
            )
        else:
            content = f"[dry-run]\n{content}"
        context.short_term.put(context.run_id, self.name, "artifact", str(artifact_path))
        return {"artifact": str(artifact_path), "content": content}
